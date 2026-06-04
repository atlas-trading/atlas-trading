import asyncio
from decimal import Decimal
from typing import Any

from atlas.core.exchange import Exchange
from atlas.core.parsers import parse_trading_pair
from atlas.market.tick import Tick


class MarketDataFeed:
    """
    Converts raw ccxt ticker payloads into Tick records and enqueues them on
    the shared tick queue for downstream consumers (e.g. persistence workers).

    Note: M-5 removed the EventBus duplicate-publish path. The LiveRunner is
    now the single owner of the runner → strategy direct invocation, while
    persistence consumers tail the tick_queue.
    """

    def __init__(self, exchange: Exchange, tick_queue: asyncio.Queue) -> None:
        self._exchange = exchange
        self._tick_queue = tick_queue

    async def on_tickers(self, tickers: dict[str, Any]) -> None:
        for symbol, raw in tickers.items():
            ts = raw.get("timestamp")
            if not ts:
                # M-8: drop ticks with missing/zero timestamp — they can't be
                # ordered or de-duplicated downstream.
                continue
            tick = self._to_tick(symbol, raw, ts)
            self._produce_tick(tick)

    def _produce_tick(self, tick: Tick) -> None:
        self._tick_queue.put_nowait(tick)

    def _to_tick(self, symbol: str, raw: dict[str, Any], timestamp: int) -> Tick:
        return Tick(
            exchange=self._exchange,
            trading_pair=parse_trading_pair(symbol),
            timestamp=timestamp,
            bid=Decimal(str(raw.get("bid") or 0)),
            ask=Decimal(str(raw.get("ask") or 0)),
            last=Decimal(str(raw.get("last") or 0)),
            volume=Decimal(str(raw.get("baseVolume") or 0)),
        )
