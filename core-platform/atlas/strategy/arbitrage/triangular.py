import time
from decimal import Decimal
from typing import Any

from atlas.core.exchange import Exchange
from atlas.core.parsers import parse_trading_pair
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.execution.arb_signal import ArbSignal
from atlas.execution.side import Side
from atlas.strategy.arbitrage.graph import ArbOpportunity, detect_arbitrage

_USDT = Quote.USDT
_BTC_Q = Quote.BTC
_ETH_Q = Quote.ETH

# Drop prices older than this many seconds during arb search.
_PRICE_TTL_SECONDS = 5.0


def _p(ticker: Ticker, quote: Quote) -> TradingPair:
    return TradingPair(ticker=ticker, quote=quote)


# 5 actively traded triangles on Binance
_TRIANGLES: list[frozenset[TradingPair]] = [
    frozenset({_p(Ticker.BTC, _USDT), _p(Ticker.ETH, _BTC_Q), _p(Ticker.ETH, _USDT)}),
    frozenset({_p(Ticker.BTC, _USDT), _p(Ticker.BNB, _BTC_Q), _p(Ticker.BNB, _USDT)}),
    frozenset({_p(Ticker.ETH, _USDT), _p(Ticker.BNB, _ETH_Q), _p(Ticker.BNB, _USDT)}),
    frozenset({_p(Ticker.BTC, _USDT), _p(Ticker.XRP, _BTC_Q), _p(Ticker.XRP, _USDT)}),
    frozenset({_p(Ticker.ETH, _USDT), _p(Ticker.XRP, _ETH_Q), _p(Ticker.XRP, _USDT)}),
]


class TriangularArbitrageStrategy:
    def __init__(
        self,
        exchange: Exchange,
        order_quantity: Decimal,
        min_profit: Decimal = Decimal("0.002"),
        taker_fee: Decimal = Decimal("0.001"),
    ) -> None:
        self._exchange = exchange
        self._order_quantity = order_quantity
        self._min_profit = min_profit
        self._taker_fee = taker_fee
        # Cached prices keyed by pair: (bid, ask, monotonic_timestamp)
        self._prices: dict[TradingPair, tuple[Decimal, Decimal, float]] = {}

    def all_pairs(self) -> list[TradingPair]:
        seen: set[TradingPair] = set()
        pairs: list[TradingPair] = []
        for triangle in _TRIANGLES:
            for pair in sorted(triangle, key=str):
                if pair not in seen:
                    seen.add(pair)
                    pairs.append(pair)
        return pairs

    def on_tickers(self, tickers: dict[str, Any]) -> list[ArbSignal]:
        self._update_prices(tickers)
        now = time.monotonic()
        signals: list[ArbSignal] = []
        for triangle in _TRIANGLES:
            fresh = {
                p: (bid, ask)
                for p in triangle
                if p in self._prices and now - self._prices[p][2] <= _PRICE_TTL_SECONDS
                for bid, ask, _ts in (self._prices[p],)
            }
            if len(fresh) < len(triangle):
                continue
            opp = detect_arbitrage(fresh, taker_fee=self._taker_fee)
            if opp is not None and opp.rate - 1 >= self._min_profit:
                signals.append(self._to_signal(opp))
        return signals

    def _update_prices(self, tickers: dict[str, Any]) -> None:
        now = time.monotonic()
        for symbol, data in tickers.items():
            try:
                pair = parse_trading_pair(symbol)
            except (ValueError, KeyError):
                continue
            last = data.get("last") or 0
            bid = data.get("bid") or last
            ask = data.get("ask") or last
            if not (bid and ask):
                continue
            bid_d, ask_d = Decimal(str(bid)), Decimal(str(ask))
            if bid_d <= 0 or ask_d <= 0 or bid_d > ask_d:
                continue
            self._prices[pair] = (bid_d, ask_d, now)

    def _to_signal(self, opp: ArbOpportunity) -> ArbSignal:
        legs = opp.legs
        if len(legs) != 3:
            raise ValueError(f"Expected 3-leg opportunity, got {len(legs)}")
        q1, q2, q3 = self._compute_quantities(legs, self._order_quantity)
        return ArbSignal(
            exchange=self._exchange,
            leg1_pair=legs[0][0],
            leg1_side=legs[0][1],
            leg1_quantity=q1,
            leg2_pair=legs[1][0],
            leg2_side=legs[1][1],
            leg2_quantity=q2,
            leg3_pair=legs[2][0],
            leg3_side=legs[2][1],
            leg3_quantity=q3,
            expected_profit=q1 * (opp.rate - 1),
        )

    def _compute_quantities(
        self,
        legs: tuple[tuple[TradingPair, Side], ...],
        base_qty: Decimal,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Propagate the realised output of each leg into the input quantity of the next.

        For ccxt-style spot pairs, `quantity` is always in base-asset units.
        - BUY at ask: spend (qty * ask) of quote, receive qty*(1-fee) of base.
        - SELL at bid: spend qty of base, receive qty*bid*(1-fee) of quote.

        The graph cycle is constructed so the output currency of leg i equals the
        input currency of leg i+1. The output amount of leg i — denominated in that
        shared currency — drives the *input* of leg i+1. We then convert that input
        amount back into the next leg's base-asset units before placing the order.
        """
        q1 = base_qty
        prev_pair, prev_side = legs[0]
        prev_bid, prev_ask, _ = self._prices[prev_pair]
        output_amount = self._leg_output_amount(prev_side, q1, prev_bid, prev_ask, self._taker_fee)

        cur_pair, cur_side = legs[1]
        cur_bid, cur_ask, _ = self._prices[cur_pair]
        q2 = self._input_to_base_qty(cur_side, output_amount, cur_bid, cur_ask)
        output_amount = self._leg_output_amount(cur_side, q2, cur_bid, cur_ask, self._taker_fee)

        cur_pair, cur_side = legs[2]
        cur_bid, cur_ask, _ = self._prices[cur_pair]
        q3 = self._input_to_base_qty(cur_side, output_amount, cur_bid, cur_ask)

        return q1, q2, q3

    @staticmethod
    def _leg_output_amount(
        side: Side,
        base_qty: Decimal,
        bid: Decimal,
        ask: Decimal,
        taker_fee: Decimal,
    ) -> Decimal:
        # BUY pays quote, receives base*(1-fee) → output = base_qty*(1-fee)
        # SELL pays base, receives quote*(1-fee) → output = base_qty*bid*(1-fee)
        if side == Side.BUY:
            return base_qty * (1 - taker_fee)
        return base_qty * bid * (1 - taker_fee)

    @staticmethod
    def _input_to_base_qty(
        side: Side, input_amount: Decimal, bid: Decimal, ask: Decimal
    ) -> Decimal:
        # BUY's input is denominated in quote: base qty = input_amount / ask
        # SELL's input is denominated in base: order qty = input_amount
        if side == Side.BUY:
            return input_amount / ask
        return input_amount
