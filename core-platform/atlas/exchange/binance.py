import asyncio
import logging
from decimal import Decimal
from typing import Any

import ccxt.pro as ccxtpro
from ccxt.base.errors import (
    AuthenticationError,
    ExchangeNotAvailable,
    NetworkError,
    RequestTimeout,
)

from atlas.core.parsers import to_ccxt_symbol
from atlas.core.trading_pair import TradingPair
from atlas.exchange.exchange_interface import ExchangeInterface, TickerCallback
from atlas.exchange.order_result import OrderResult
from atlas.execution.balance import Balance
from atlas.execution.order import Order
from atlas.execution.order_status import OrderStatus

_log = logging.getLogger(__name__)

_CCXT_STATUS_MAP: dict[str, OrderStatus] = {
    "open": OrderStatus.PENDING,
    "closed": OrderStatus.FILLED,
    "canceled": OrderStatus.CANCELLED,
    "expired": OrderStatus.CANCELLED,
    "rejected": OrderStatus.REJECTED,
}

_RECONNECT_BACKOFF_SECONDS = 1.0


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


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
        self._subscribe_task: asyncio.Task | None = None

    async def subscribe_ticker(
        self, trading_pairs: list[TradingPair], callback: TickerCallback
    ) -> None:
        symbols: list[str] = [to_ccxt_symbol(pair) for pair in trading_pairs]
        self._running = True

        while self._running:
            try:
                tickers = await self._exchange.watch_tickers(symbols)
                await self._on_ticker(tickers, callback)
            except asyncio.CancelledError:
                # Cooperative cancellation must propagate; never swallow.
                raise
            except AuthenticationError:
                # Bad credentials are non-recoverable.
                _log.exception("binance auth failure; aborting subscribe loop")
                raise
            except (NetworkError, RequestTimeout, ExchangeNotAvailable):
                _log.warning("binance transient error; reconnecting", exc_info=True)
                await asyncio.sleep(_RECONNECT_BACKOFF_SECONDS)
            except Exception:
                _log.exception("binance unexpected error in subscribe loop")
                raise

    async def _on_ticker(self, tickers: dict[str, Any], callback: TickerCallback) -> None:
        await callback(tickers)

    async def place_order(self, order: Order) -> OrderResult:
        symbol: str = to_ccxt_symbol(order.trading_pair)
        amount_str = self._exchange.amount_to_precision(symbol, float(order.quantity))
        price_str = (
            self._exchange.price_to_precision(symbol, float(order.price)) if order.price else None
        )
        params: dict[str, Any] = {"newClientOrderId": order.id}
        raw = await self._exchange.create_order(
            symbol=symbol,
            type=order.order_type.value,
            side=order.side.value,
            amount=amount_str,
            price=price_str,
            params=params,
        )

        return OrderResult(
            id=raw["id"],
            status=_CCXT_STATUS_MAP.get(raw.get("status", ""), OrderStatus.PENDING),
            symbol=raw.get("symbol"),
            type=raw.get("type"),
            side=raw.get("side"),
            timestamp=raw.get("timestamp"),
            datetime=raw.get("datetime"),
            price=_to_decimal(raw.get("price")),
            average=_to_decimal(raw.get("average")),
            amount=_to_decimal(raw.get("amount")),
            filled=_to_decimal(raw.get("filled")),
            remaining=_to_decimal(raw.get("remaining")),
            cost=_to_decimal(raw.get("cost")),
            client_order_id=raw.get("clientOrderId"),
            time_in_force=raw.get("timeInForce"),
            post_only=raw.get("postOnly"),
            reduce_only=raw.get("reduceOnly"),
        )

    async def cancel_order(self, order_id: str, symbol: str) -> None:
        await self._exchange.cancel_order(order_id, symbol)

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

        if self._subscribe_task is not None and not self._subscribe_task.done():
            self._subscribe_task.cancel()
            try:
                await self._subscribe_task
            except asyncio.CancelledError:
                pass

        await self._exchange.close()
