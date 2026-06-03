import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.db.models import RawTick
from atlas.market.tick import Tick

_BATCH_INTERVAL = 0.1  # 100ms


class DBLoggerWorker:
    def __init__(
        self, tick_queue: asyncio.Queue, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._tick_queue = tick_queue
        self._session_factory = session_factory
        self._running = False

    async def run(self) -> None:
        self._running = True
        while self._running:
            await asyncio.sleep(_BATCH_INTERVAL)
            batch = self._drain()
            if batch:
                await self._flush(batch)

    def stop(self) -> None:
        self._running = False

    def _drain(self) -> list[Tick]:
        batch: list[Tick] = []
        while True:
            try:
                batch.append(self._tick_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return batch

    async def _flush(self, batch: list[Tick]) -> None:
        async with self._session_factory() as session:
            session.add_all([_to_raw_tick(t) for t in batch])
            await session.commit()


def _to_raw_tick(tick: Tick) -> RawTick:
    return RawTick(
        exchange=str(tick.exchange),
        symbol=f"{tick.trading_pair.ticker}/{tick.trading_pair.quote}",
        timestamp=datetime.fromtimestamp(tick.timestamp / 1000, tz=timezone.utc),
        bid=tick.bid,
        ask=tick.ask,
        last=tick.last,
        volume=tick.volume,
    )
