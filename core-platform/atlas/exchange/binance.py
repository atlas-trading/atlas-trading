import asyncio
import dataclasses
from decimal import Decimal

import ccxt.pro as ccxtpro

from atlas.core.parsers import to_ccxt_symbol
from atlas.core.trading_pair import TradingPair
from atlas.exchange.exchange_interface import ExchangeInterface, TickerCallback
from atlas.exchange.order_result import OrderResult
from atlas.execution.balance import Balance
from atlas.execution.order import Order
from atlas.execution.order_status import OrderStatus

_CCXT_STATUS_MAP: dict[str, OrderStatus] = {
    "open": OrderStatus.PENDING,
    "closed": OrderStatus.FILLED,
    "canceled": OrderStatus.CANCELLED,
    "expired": OrderStatus.CANCELLED,
    "rejected": OrderStatus.REJECTED,
}


class BinanceAdapter(ExchangeInterface):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False) -> None:
        self._exchange = ccxtpro.binance(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "options": {"defaultType": "spot"},
            }
        )
        if testnet:
            self._exchange.set_sandbox_mode(True)
        self._running = False

    async def subscribe_ticker(
        self, trading_pairs: list[TradingPair], callback: TickerCallback
    ) -> None:
        symbols: list[str] = [to_ccxt_symbol(pair) for pair in trading_pairs]
        self._running = True
        while self._running:
            try:
                tickers = await self._exchange.watch_tickers(symbols)
                await self._on_ticker(tickers, callback)
            except Exception:
                await asyncio.sleep(1)

    async def _on_ticker(self, tickers: dict, callback: TickerCallback) -> None:
        await callback(tickers)

    async def place_order(self, order: Order) -> Order:
        symbol: str = to_ccxt_symbol(order.trading_pair)
        raw = await self._exchange.create_order(
            symbol=symbol,
            type=order.order_type.value,
            side=order.side.value,
            amount=float(order.quantity),
            price=float(order.price) if order.price else None,
        )
        order_result = OrderResult(
            id=raw["id"],
            status=raw.get("status"),
            symbol=raw.get("symbol"),
            type=raw.get("type"),
            side=raw.get("side"),
            timestamp=raw.get("timestamp"),
            datetime=raw.get("datetime"),
            price=raw.get("price"),
            average=raw.get("average"),
            amount=raw.get("amount"),
            filled=raw.get("filled"),
            remaining=raw.get("remaining"),
            cost=raw.get("cost"),
            client_order_id=raw.get("clientOrderId"),
            time_in_force=raw.get("timeInForce"),
            post_only=raw.get("postOnly"),
            reduce_only=raw.get("reduceOnly"),
        )
        new_status = _CCXT_STATUS_MAP.get(order_result.status or "", OrderStatus.PENDING)
        return dataclasses.replace(order, status=new_status)

    async def cancel_order(self, order: Order) -> None:
        await self._exchange.cancel_order(order.id, to_ccxt_symbol(order.trading_pair))

    async def get_balance(self) -> Balance:
        raw = await self._exchange.fetch_balance()
        return Balance(
            usdt=Decimal(str(raw.get("USDT", {}).get("free", 0))),
            btc=Decimal(str(raw.get("BTC", {}).get("free", 0))),
            eth=Decimal(str(raw.get("ETH", {}).get("free", 0))),
        )

    async def health_check(self) -> bool:
        try:
            await self._exchange.fetch_balance()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        self._running = False
        await self._exchange.close()
