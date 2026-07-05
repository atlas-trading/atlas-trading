"""
/backtests 라우트 테스트. aiosqlite 인메모리 DB로 get_db를 오버라이드하고,
TestClient 요청과 같은 이벤트 루프에서 테이블 생성·시드가 일어나도록
의존성 안에서 lazy 초기화한다.
"""

from datetime import datetime, timezone
from decimal import Decimal

from atlas.db.models import BacktestRun, BacktestTrade, Base
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app

_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_factory = async_sessionmaker(_engine, expire_on_commit=False)
_initialized = False


async def _seed() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _factory() as s:
        run = BacktestRun(
            start_date=datetime(2025, 3, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 3, 2, tzinfo=timezone.utc),
            initial_balance=Decimal("1000"),
            final_balance=Decimal("1001.5"),
            order_qty=Decimal("0.001"),
            min_profit=Decimal("0.002"),
            slippage=Decimal("0.0005"),
        )
        s.add(run)
        await s.flush()
        s.add_all(
            [
                BacktestTrade(
                    run_id=run.id,
                    timestamp=datetime(2025, 3, 1, 0, 0, 1, tzinfo=timezone.utc),
                    arb_id="arb-1",
                    leg1_pair="BTC/USDT",
                    leg2_pair="ETH/BTC",
                    leg3_pair="ETH/USDT",
                    expected_profit=Decimal("0.5"),
                    actual_profit=Decimal("1.5"),
                    status="COMPLETE",
                ),
                BacktestTrade(
                    run_id=run.id,
                    timestamp=datetime(2025, 3, 1, 0, 0, 2, tzinfo=timezone.utc),
                    arb_id="arb-2",
                    leg1_pair="BTC/USDT",
                    leg2_pair="ETH/BTC",
                    leg3_pair="ETH/USDT",
                    expected_profit=Decimal("0.3"),
                    actual_profit=None,
                    status="TIMEOUT",
                ),
            ]
        )
        await s.commit()


async def _get_test_db():
    global _initialized
    if not _initialized:
        await _seed()
        _initialized = True
    async with _factory() as session:
        yield session


app.dependency_overrides[get_db] = _get_test_db
client = TestClient(app)


def test_list_backtests_returns_runs_with_summary():
    resp = client.get("/backtests")
    assert resp.status_code == 200
    [run] = resp.json()
    assert run["id"] == 1
    assert run["trade_count"] == 2
    assert run["win_rate"] == 0.5
    assert run["total_pnl"] == "1.50000000"


def test_list_backtest_trades_returns_trades_in_order():
    resp = client.get("/backtests/1/trades")
    assert resp.status_code == 200
    trades = resp.json()
    assert len(trades) == 2
    assert trades[0]["arb_id"] == "arb-1"
    assert trades[1]["actual_profit"] is None


def test_unknown_run_id_returns_404():
    resp = client.get("/backtests/999/trades")
    assert resp.status_code == 404
