from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from atlas.backtest.feed import HistoricalFeed
from atlas.db.models import Base, RawTick


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _tick(symbol: str, ts: datetime, bid: str, ask: str) -> RawTick:
    return RawTick(
        exchange="binance",
        symbol=symbol,
        timestamp=ts,
        bid=Decimal(bid),
        ask=Decimal(ask),
        last=Decimal(0),
        volume=Decimal(0),
    )


_T1 = datetime(2025, 3, 1, 0, 0, 1, tzinfo=timezone.utc)
_T2 = datetime(2025, 3, 1, 0, 0, 2, tzinfo=timezone.utc)


async def test_stream_yields_tickers_grouped_by_timestamp(session_factory):
    async with session_factory() as s:
        s.add_all(
            [
                _tick("BTC/USDT", _T1, "50000", "50001"),
                _tick("ETH/BTC", _T1, "0.06", "0.061"),
                _tick("BTC/USDT", _T2, "50100", "50101"),
            ]
        )
        await s.commit()

    feed = HistoricalFeed(session_factory)
    results = []
    async for ts, tickers in feed.stream(
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 2, tzinfo=timezone.utc),
    ):
        results.append((ts, tickers))

    assert len(results) == 2
    ts1, t1 = results[0]
    assert ts1 == _T1
    assert "BTC/USDT" in t1 and "ETH/BTC" in t1
    assert t1["BTC/USDT"]["bid"] == 50000.0

    ts2, t2 = results[1]
    assert ts2 == _T2
    assert list(t2.keys()) == ["BTC/USDT"]


async def test_stream_respects_date_range(session_factory):
    outside = datetime(2025, 2, 28, 23, 59, 59, tzinfo=timezone.utc)
    async with session_factory() as s:
        s.add_all(
            [
                _tick("BTC/USDT", outside, "49000", "49001"),
                _tick("BTC/USDT", _T1, "50000", "50001"),
            ]
        )
        await s.commit()

    feed = HistoricalFeed(session_factory)
    results = [
        r
        async for r in feed.stream(
            datetime(2025, 3, 1, tzinfo=timezone.utc),
            datetime(2025, 3, 2, tzinfo=timezone.utc),
        )
    ]
    assert len(results) == 1
    assert results[0][0] == _T1


async def test_stream_empty_range_yields_nothing(session_factory):
    feed = HistoricalFeed(session_factory)
    results = [
        r
        async for r in feed.stream(
            datetime(2025, 3, 1, tzinfo=timezone.utc),
            datetime(2025, 3, 1, tzinfo=timezone.utc),
        )
    ]
    assert results == []
