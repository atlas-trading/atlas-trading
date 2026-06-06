from datetime import datetime, timezone
from typing import Any, AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from atlas.db.models import RawTick


class HistoricalFeed:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def stream(
        self, start: datetime, end: datetime
    ) -> AsyncIterator[tuple[datetime, dict[str, Any]]]:
        async with self._session_factory() as session:
            result = await session.stream(
                select(RawTick)
                .where(
                    RawTick.exchange == "binance",
                    RawTick.timestamp >= start,
                    RawTick.timestamp < end,
                )
                .order_by(RawTick.timestamp, RawTick.symbol)
            )
            current_ts: datetime | None = None
            current_group: dict[str, Any] = {}

            async for tick in result.scalars():
                if tick.timestamp.tzinfo is None:
                    ts = tick.timestamp.replace(tzinfo=timezone.utc)
                else:
                    ts = tick.timestamp.astimezone(timezone.utc)
                if current_ts is None:
                    current_ts = ts
                if ts != current_ts:
                    yield current_ts, current_group
                    current_group = {}
                    current_ts = ts
                current_group[tick.symbol] = {
                    "bid": float(tick.bid),
                    "ask": float(tick.ask),
                    "last": float(tick.last),
                }

            if current_group and current_ts is not None:
                yield current_ts, current_group
