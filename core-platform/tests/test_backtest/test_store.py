from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from atlas.backtest.report import BacktestSummary
from atlas.backtest.runner import TradeRecord
from atlas.backtest.store import save_run
from atlas.db.models import BacktestTrade, Base

_TS = datetime(2025, 3, 1, 0, 0, 1, tzinfo=timezone.utc)


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _summary(records: list[TradeRecord]) -> BacktestSummary:
    return BacktestSummary(
        start=datetime(2025, 3, 1, tzinfo=timezone.utc),
        end=datetime(2025, 3, 2, tzinfo=timezone.utc),
        initial_balance=Decimal("1000"),
        final_balance=Decimal("1001.5"),
        records=records,
    )


def _record(arb_id: str = "arb-1", pnl: str | None = "1.5") -> TradeRecord:
    return TradeRecord(
        timestamp=_TS,
        arb_id=arb_id,
        leg1_pair="BTC/USDT",
        leg2_pair="ETH/BTC",
        leg3_pair="ETH/USDT",
        expected_profit=Decimal("0.5"),
        actual_profit=Decimal(pnl) if pnl is not None else None,
        status="COMPLETE",
    )


async def test_save_run_returns_run_id(session_factory):
    run_id = await save_run(
        session_factory,
        _summary([_record()]),
        order_qty=Decimal("0.001"),
        min_profit=Decimal("0.002"),
        slippage=Decimal("0.0005"),
    )
    assert isinstance(run_id, int)


async def test_save_run_persists_trades(session_factory):
    run_id = await save_run(
        session_factory,
        _summary([_record("arb-1"), _record("arb-2", pnl=None)]),
        order_qty=Decimal("0.001"),
        min_profit=Decimal("0.002"),
        slippage=Decimal("0.0005"),
    )
    async with session_factory() as s:
        count = (
            await s.execute(
                select(func.count())
                .select_from(BacktestTrade)
                .where(BacktestTrade.run_id == run_id)
            )
        ).scalar_one()
    assert count == 2


async def test_save_run_with_no_trades(session_factory):
    run_id = await save_run(
        session_factory,
        _summary([]),
        order_qty=Decimal("0.001"),
        min_profit=Decimal("0.002"),
        slippage=Decimal("0.0005"),
    )
    assert run_id >= 1
