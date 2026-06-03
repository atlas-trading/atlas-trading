import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from atlas.core.exchange import Exchange
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.db.logger import DBLoggerWorker, _to_raw_tick
from atlas.db.models import Base, RawTick
from atlas.market.tick import Tick

_PAIR = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)


def _make_tick(ts: int = 1_000_000) -> Tick:
    return Tick(
        exchange=Exchange.BINANCE,
        trading_pair=_PAIR,
        timestamp=ts,
        bid=Decimal("50000"),
        ask=Decimal("50001"),
        last=Decimal("50000.5"),
        volume=Decimal("100"),
    )


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def test_to_raw_tick_mapping():
    tick = _make_tick(ts=1_000_000)
    raw = _to_raw_tick(tick)
    assert raw.exchange == "binance"
    assert raw.symbol == "BTC/USDT"
    assert raw.bid == Decimal("50000")
    assert raw.timestamp.tzinfo is not None
    assert raw.timestamp.timestamp() == pytest.approx(1_000.0)


async def test_flush_inserts_batch(session_factory):
    queue: asyncio.Queue = asyncio.Queue()
    worker = DBLoggerWorker(tick_queue=queue, session_factory=session_factory)

    ticks = [_make_tick(ts=i * 1000) for i in range(1, 4)]
    for t in ticks:
        queue.put_nowait(t)

    batch = worker._drain()
    assert len(batch) == 3
    assert queue.empty()

    await worker._flush(batch)

    async with session_factory() as session:
        rows = (await session.execute(select(RawTick))).scalars().all()
    assert len(rows) == 3


async def test_flush_empty_batch_is_noop(session_factory):
    queue: asyncio.Queue = asyncio.Queue()
    worker = DBLoggerWorker(tick_queue=queue, session_factory=session_factory)

    await worker._flush([])

    async with session_factory() as session:
        rows = (await session.execute(select(RawTick))).scalars().all()
    assert len(rows) == 0


async def test_drain_empty_queue():
    queue: asyncio.Queue = asyncio.Queue()
    worker = DBLoggerWorker(tick_queue=queue, session_factory=None)
    assert worker._drain() == []
