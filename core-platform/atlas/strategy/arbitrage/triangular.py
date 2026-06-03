from decimal import Decimal
from typing import Any

from atlas.core.exchange import Exchange
from atlas.core.parsers import parse_trading_pair
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.execution.arb_signal import ArbSignal
from atlas.strategy.arbitrage.graph import ArbOpportunity, detect_arbitrage

_USDT = Quote.USDT
_BTC_Q = Quote.BTC
_ETH_Q = Quote.ETH


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
        min_profit: Decimal = Decimal("0.005"),
    ) -> None:
        self._exchange = exchange
        self._order_quantity = order_quantity
        self._min_profit = min_profit
        self._prices: dict[TradingPair, tuple[Decimal, Decimal]] = {}

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
        signals: list[ArbSignal] = []
        for triangle in _TRIANGLES:
            prices = {p: self._prices[p] for p in triangle if p in self._prices}
            if len(prices) < len(triangle):
                continue
            opp = detect_arbitrage(prices)
            if opp is not None and opp.rate - 1 >= self._min_profit:
                signals.append(self._to_signal(opp))
        return signals

    def _update_prices(self, tickers: dict[str, Any]) -> None:
        for symbol, data in tickers.items():
            try:
                pair = parse_trading_pair(symbol)
            except (ValueError, KeyError):
                continue
            bid = data.get("bid") or 0
            ask = data.get("ask") or 0
            if bid and ask:
                self._prices[pair] = (Decimal(str(bid)), Decimal(str(ask)))

    def _to_signal(self, opp: ArbOpportunity) -> ArbSignal:
        legs = opp.legs
        if len(legs) != 3:
            raise ValueError(f"Expected 3-leg opportunity, got {len(legs)}")
        qty = self._order_quantity
        return ArbSignal(
            exchange=self._exchange,
            leg1_pair=legs[0][0],
            leg1_side=legs[0][1],
            leg1_quantity=qty,
            leg2_pair=legs[1][0],
            leg2_side=legs[1][1],
            leg2_quantity=qty,
            leg3_pair=legs[2][0],
            leg3_side=legs[2][1],
            leg3_quantity=qty,
            expected_profit=qty * (opp.rate - 1),
        )
