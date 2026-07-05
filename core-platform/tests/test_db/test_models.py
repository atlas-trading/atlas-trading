import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from atlas.db.models import ArbAttempt, Base, OHLCVRecord, OrderRecord, RawTick, TradeResult


@pytest.mark.asyncio
async def test_all_tables_created():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.begin() as conn:
        table_names = await conn.run_sync(lambda c: c.dialect.get_table_names(c))

    assert "raw_ticks" in table_names
    assert "ohlcv" in table_names
    assert "orders" in table_names
    assert "arb_attempts" in table_names
    assert "trade_results" in table_names

    await engine.dispose()


def test_model_table_names():
    assert RawTick.__tablename__ == "raw_ticks"
    assert OHLCVRecord.__tablename__ == "ohlcv"
    assert OrderRecord.__tablename__ == "orders"
    assert ArbAttempt.__tablename__ == "arb_attempts"
    assert TradeResult.__tablename__ == "trade_results"


def test_backtest_run_tablename():
    from atlas.db.models import BacktestRun

    assert BacktestRun.__tablename__ == "backtest_runs"


def test_backtest_trade_tablename():
    from atlas.db.models import BacktestTrade

    assert BacktestTrade.__tablename__ == "backtest_trades"
