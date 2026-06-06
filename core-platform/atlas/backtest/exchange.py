from decimal import Decimal
from typing import Any

from atlas.core.parsers import parse_trading_pair, to_ccxt_symbol
from atlas.core.trading_pair import TradingPair
from atlas.exchange.exchange_interface import ExchangeInterface, TickerCallback
from atlas.exchange.order_result import OrderResult
from atlas.execution.balance import Balance
from atlas.execution.order import Order
from atlas.execution.order_status import OrderStatus
from atlas.execution.side import Side


class BacktestExchange(ExchangeInterface):
    def __init__(
        self,
        initial_balance: dict[str, Decimal],
        slippage: Decimal = Decimal("0.0005"),
    ) -> None:
        self._balance: dict[str, Decimal] = dict(initial_balance)
        self._slippage = slippage
        self._prices: dict[TradingPair, tuple[Decimal, Decimal]] = {}

    def update_prices(self, tickers: dict[str, Any]) -> None:
        for symbol, data in tickers.items():
            try:
                pair = parse_trading_pair(symbol)
            except (ValueError, KeyError):
                continue
            bid = Decimal(str(data.get("bid") or 0))
            ask = Decimal(str(data.get("ask") or 0))
            if bid > 0 and ask > 0:
                self._prices[pair] = (bid, ask)

    def get_balance_for(self, currency: str) -> Decimal:
        return self._balance.get(currency, Decimal(0))

    def get_usdt_balance(self) -> Decimal:
        return self._balance.get("USDT", Decimal(0))

    async def place_order(self, order: Order) -> OrderResult:
        pair = order.trading_pair
        prices = self._prices.get(pair)
        if prices is None:
            raise RuntimeError(f"No price for {to_ccxt_symbol(pair)}")
        bid, ask = prices

        if order.side == Side.BUY:
            fill_price = ask * (1 + self._slippage)
            cost = order.quantity * fill_price
            quote = str(pair.quote)
            if self._balance.get(quote, Decimal(0)) < cost:
                raise RuntimeError(f"Insufficient {quote} balance")
            self._balance[quote] = self._balance.get(quote, Decimal(0)) - cost
            base = str(pair.ticker)
            self._balance[base] = self._balance.get(base, Decimal(0)) + order.quantity
            return OrderResult(
                id=order.id,
                status=OrderStatus.FILLED,
                filled=order.quantity,
                average=fill_price,
                cost=cost,
            )
        else:
            fill_price = bid * (1 - self._slippage)
            proceeds = order.quantity * fill_price
            base = str(pair.ticker)
            if self._balance.get(base, Decimal(0)) < order.quantity:
                raise RuntimeError(f"Insufficient {base} balance")
            self._balance[base] = self._balance.get(base, Decimal(0)) - order.quantity
            quote = str(pair.quote)
            self._balance[quote] = self._balance.get(quote, Decimal(0)) + proceeds
            return OrderResult(
                id=order.id,
                status=OrderStatus.FILLED,
                filled=order.quantity,
                average=fill_price,
                cost=proceeds,
            )

    async def get_balance(self) -> Balance:
        return Balance(
            usdt=self._balance.get("USDT", Decimal(0)),
            btc=self._balance.get("BTC", Decimal(0)),
            eth=self._balance.get("ETH", Decimal(0)),
        )

    async def health_check(self) -> bool:
        return True

    async def subscribe_ticker(self, trading_pairs: list, callback: TickerCallback) -> None:
        pass

    async def cancel_order(self, order_id: str, symbol: str) -> None:
        pass

    async def close(self) -> None:
        pass
