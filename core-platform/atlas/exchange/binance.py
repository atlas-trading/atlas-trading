import asyncio
import dataclasses
from decimal import Decimal

import ccxt.pro as ccxtpro

from atlas.core.parsers import to_ccxt_symbol
from atlas.core.trading_pair import TradingPair
from atlas.exchange.exchange_interface import ExchangeInterface, TickerCallback
from atlas.execution.balance import Balance
from atlas.execution.order import Order
from atlas.execution.order_status import OrderStatus


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
        symbols = [to_ccxt_symbol(pair) for pair in trading_pairs]
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
        order_result = await self._exchange.create_order(
            symbol=symbol,
            type=order.order_type.value,
            side=order.side.value,
            amount=float(order.quantity),
            price=float(order.price) if order.price else None,
        )
        new_status = (
            OrderStatus.FILLED if order_result["status"] == "closed" else OrderStatus.PENDING
        )
        return dataclasses.replace(order, status=new_status)

    async def cancel_order(self, order_id: str) -> None:
        await self._exchange.cancel_order(order_id)

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
