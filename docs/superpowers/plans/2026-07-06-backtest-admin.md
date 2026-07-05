# Backtest Admin Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 백테스트 결과를 DB에 저장하고, api-server REST 엔드포인트와 web-dashboard 탭으로 실행 이력·요약·거래 내역을 조회한다.

**Architecture:** `run_backtest.py`가 완료 후 `backtest_runs`/`backtest_trades` 테이블에 저장(service 함수 `save_run`). api-server가 `GET /backtests`, `GET /backtests/{run_id}/trades`를 제공. web-dashboard는 `useState` 탭 전환으로 `BacktestPanel`을 노출.

**Tech Stack:** SQLAlchemy async + Alembic, FastAPI(수동 dict 직렬화), React 19 + Tailwind 4 (라이브러리 추가 없음)

**Spec:** `docs/superpowers/specs/2026-07-06-backtest-admin-design.md`

## Global Constraints

- 모든 dataclass는 `frozen=True, kw_only=True`. dataclass에 메서드 금지 — 로직은 service 함수로.
- 주석은 비자명한 WHY만. 파생 지표(승률·PnL)는 저장하지 않고 API에서 계산.
- python 실행은 각 패키지의 `.venv/bin/python`. api-server 테스트는 `api-server/.venv/bin/python -m pytest`.
- 커밋은 논리 단위로 자주.

---

## Task 1: DB 모델 + Alembic 마이그레이션

**Files:**
- Modify: `core-platform/atlas/db/models.py` (파일 끝에 클래스 2개 추가)
- Create: `core-platform/alembic/versions/0003_add_backtest_tables.py`
- Modify: `core-platform/tests/test_db/test_models.py` (테이블명 테스트 추가)

**Interfaces:**
- Produces: `atlas.db.models.BacktestRun` (컬럼: id, start_date, end_date, initial_balance, final_balance, order_qty, min_profit, slippage, created_at), `atlas.db.models.BacktestTrade` (컬럼: id, run_id, timestamp, arb_id, leg1_pair, leg2_pair, leg3_pair, expected_profit, actual_profit, status)

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_db/test_models.py` 끝에 추가

```python
def test_backtest_run_tablename():
    from atlas.db.models import BacktestRun

    assert BacktestRun.__tablename__ == "backtest_runs"


def test_backtest_trade_tablename():
    from atlas.db.models import BacktestTrade

    assert BacktestTrade.__tablename__ == "backtest_trades"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd core-platform && .venv/bin/python -m pytest tests/test_db/test_models.py -v`
Expected: ImportError (BacktestRun 없음)

- [ ] **Step 3: 모델 추가** — `atlas/db/models.py`

import 라인을 다음으로 교체:

```python
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
```

파일 끝에 추가:

```python
class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    final_balance: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    order_qty: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    min_profit: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    slippage: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("backtest_runs.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    arb_id: Mapped[str] = mapped_column(String(100))
    leg1_pair: Mapped[str] = mapped_column(String(20))
    leg2_pair: Mapped[str] = mapped_column(String(20))
    leg3_pair: Mapped[str] = mapped_column(String(20))
    expected_profit: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    actual_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
```

- [ ] **Step 4: 마이그레이션 작성** — `alembic/versions/0003_add_backtest_tables.py`

```python
"""add backtest result tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("initial_balance", sa.Numeric(20, 8), nullable=False),
        sa.Column("final_balance", sa.Numeric(20, 8), nullable=False),
        sa.Column("order_qty", sa.Numeric(20, 8), nullable=False),
        sa.Column("min_profit", sa.Numeric(20, 8), nullable=False),
        sa.Column("slippage", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "backtest_trades",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "run_id", sa.Integer, sa.ForeignKey("backtest_runs.id"), nullable=False
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arb_id", sa.String(100), nullable=False),
        sa.Column("leg1_pair", sa.String(20), nullable=False),
        sa.Column("leg2_pair", sa.String(20), nullable=False),
        sa.Column("leg3_pair", sa.String(20), nullable=False),
        sa.Column("expected_profit", sa.Numeric(20, 8), nullable=False),
        sa.Column("actual_profit", sa.Numeric(20, 8), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
    )
    op.create_index("ix_backtest_trades_run_id", "backtest_trades", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_backtest_trades_run_id", table_name="backtest_trades")
    op.drop_table("backtest_trades")
    op.drop_table("backtest_runs")
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `.venv/bin/python -m pytest tests/test_db/ -v`
Expected: PASS

- [ ] **Step 6: 로컬 DB에 마이그레이션 적용**

Run: `DATABASE_URL="postgresql+asyncpg://atlas:atlas-local@127.0.0.1:5432/atlas" .venv/bin/alembic upgrade head`
Expected: `Running upgrade 0002 -> 0003` (env.py가 DATABASE_URL을 다른 이름으로 읽으면 `alembic/env.py` 상단을 확인해 맞춰서 실행)

확인: `docker exec infrastructure-timescaledb-1 psql -U atlas -d atlas -c "\dt"` 에 backtest_runs, backtest_trades 표시

- [ ] **Step 7: 커밋**

```bash
git add core-platform/atlas/db/models.py core-platform/alembic/versions/0003_add_backtest_tables.py core-platform/tests/test_db/test_models.py
git commit -m "feat(db): backtest_runs and backtest_trades tables"
```

---

## Task 2: save_run service 함수

**Files:**
- Create: `core-platform/atlas/backtest/store.py`
- Create: `core-platform/tests/test_backtest/test_store.py`

**Interfaces:**
- Consumes: Task 1의 `BacktestRun`, `BacktestTrade` 모델. 기존 `atlas.backtest.report.BacktestSummary`(필드: start, end, initial_balance, final_balance, records), `atlas.backtest.runner.TradeRecord`
- Produces: `atlas.backtest.store.save_run(session_factory, summary, *, order_qty: Decimal, min_profit: Decimal, slippage: Decimal) -> int` (반환값: 생성된 run_id)

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_backtest/test_store.py`

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_backtest/test_store.py -v`
Expected: ImportError (store 모듈 없음)

- [ ] **Step 3: `atlas/backtest/store.py` 구현**

```python
from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker

from atlas.db.models import BacktestRun, BacktestTrade

from .report import BacktestSummary


async def save_run(
    session_factory: async_sessionmaker,
    summary: BacktestSummary,
    *,
    order_qty: Decimal,
    min_profit: Decimal,
    slippage: Decimal,
) -> int:
    async with session_factory() as session:
        run = BacktestRun(
            start_date=summary.start,
            end_date=summary.end,
            initial_balance=summary.initial_balance,
            final_balance=summary.final_balance,
            order_qty=order_qty,
            min_profit=min_profit,
            slippage=slippage,
        )
        session.add(run)
        await session.flush()
        session.add_all(
            BacktestTrade(
                run_id=run.id,
                timestamp=r.timestamp,
                arb_id=r.arb_id,
                leg1_pair=r.leg1_pair,
                leg2_pair=r.leg2_pair,
                leg3_pair=r.leg3_pair,
                expected_profit=r.expected_profit,
                actual_profit=r.actual_profit,
                status=r.status,
            )
            for r in summary.records
        )
        await session.commit()
        return run.id
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/python -m pytest tests/test_backtest/test_store.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
git add core-platform/atlas/backtest/store.py core-platform/tests/test_backtest/test_store.py
git commit -m "feat(backtest): save_run persists run and trades to DB"
```

---

## Task 3: run_backtest.py 저장 연동

**Files:**
- Modify: `core-platform/run_backtest.py`

**Interfaces:**
- Consumes: Task 2의 `save_run`

- [ ] **Step 1: import 추가**

```python
from atlas.backtest.store import save_run
```

- [ ] **Step 2: slippage를 변수로 추출** — `main()`에서 `exchange = BacktestExchange(` 앞에 추가하고 생성자에 전달:

```python
    slippage = Decimal("0.0005")
    exchange = BacktestExchange(
        initial_balance={
            "USDT": initial_usdt,
            "BTC": Decimal("0"),
            "ETH": Decimal("0"),
            "BNB": Decimal("0"),
            "XRP": Decimal("0"),
        },
        slippage=slippage,
    )
```

- [ ] **Step 3: 저장 호출 추가** — `print_summary(summary)` 다음, `if args.output:` 앞에:

```python
    try:
        run_id = await save_run(
            session_factory,
            summary,
            order_qty=Decimal(args.qty),
            min_profit=Decimal(args.min_profit),
            slippage=slippage,
        )
        print(f"결과 DB 저장됨: run_id={run_id}")
    except Exception:
        # 결과는 이미 터미널/CSV로 출력됐으므로 저장 실패로 프로세스를 죽이지 않는다
        logging.exception("백테스트 결과 DB 저장 실패")
```

- [ ] **Step 4: 수동 검증** — 로컬 DB(데이터 이미 적재됨)로 실행

Run: `DATABASE_URL="postgresql+asyncpg://atlas:atlas-local@127.0.0.1:5432/atlas" .venv/bin/python run_backtest.py --start 2025-03-01 --end 2025-03-02`
Expected: 요약 출력 후 `결과 DB 저장됨: run_id=1`

확인: `docker exec infrastructure-timescaledb-1 psql -U atlas -d atlas -c "select id, initial_balance, final_balance from backtest_runs;"` 에 1행

- [ ] **Step 5: 전체 테스트 + 커밋**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: 전체 통과

```bash
git add core-platform/run_backtest.py
git commit -m "feat(backtest): persist results to DB after run"
```

---

## Task 4: API — GET /backtests, GET /backtests/{run_id}/trades

**Files:**
- Create: `api-server/app/routes/backtests.py`
- Modify: `api-server/app/models.py` (재export 추가)
- Modify: `api-server/app/main.py` (라우터 등록)
- Create: `api-server/tests/test_backtests.py`

**Interfaces:**
- Consumes: Task 1의 `BacktestRun`, `BacktestTrade`
- Produces: `GET /backtests?limit=50` → `[{id:int, start_date, end_date, initial_balance, final_balance, order_qty, min_profit, slippage, created_at, trade_count:int, win_rate:float, total_pnl:str}]` / `GET /backtests/{run_id}/trades` → `[{id:int, timestamp, arb_id, leg1_pair, leg2_pair, leg3_pair, expected_profit, actual_profit, status}]` (404 if run 없음)

- [ ] **Step 1: aiosqlite dev 의존성 확인** — `api-server/pyproject.toml`의 dev deps에 `aiosqlite`가 없으면 추가

Run: `cd api-server && grep aiosqlite pyproject.toml || uv add --dev aiosqlite`

- [ ] **Step 2: 실패 테스트 작성** — `api-server/tests/test_backtests.py`

```python
"""
/backtests 라우트 테스트. aiosqlite 인메모리 DB로 get_db를 오버라이드하고,
TestClient 요청과 같은 이벤트 루프에서 테이블 생성·시드가 일어나도록
의존성 안에서 lazy 초기화한다.
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from atlas.db.models import BacktestRun, BacktestTrade, Base

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
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd api-server && .venv/bin/python -m pytest tests/test_backtests.py -v`
Expected: ImportError 또는 404 (라우터 없음)

- [ ] **Step 4: `app/models.py` 재export 추가**

```python
from atlas.db.models import ArbAttempt, BacktestRun, BacktestTrade, OrderRecord

__all__ = ["ArbAttempt", "BacktestRun", "BacktestTrade", "OrderRecord"]
```

- [ ] **Step 5: `app/routes/backtests.py` 구현**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import BacktestRun, BacktestTrade

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.get("")
async def list_backtests(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    runs = (
        (
            await db.execute(
                select(BacktestRun).order_by(desc(BacktestRun.created_at)).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    counts = {
        run_id: (total, complete)
        for run_id, total, complete in (
            await db.execute(
                select(
                    BacktestTrade.run_id,
                    func.count(),
                    func.count().filter(BacktestTrade.status == "COMPLETE"),
                ).group_by(BacktestTrade.run_id)
            )
        ).all()
    }
    out = []
    for r in runs:
        total, complete = counts.get(r.id, (0, 0))
        out.append(
            {
                "id": r.id,
                "start_date": r.start_date.isoformat(),
                "end_date": r.end_date.isoformat(),
                "initial_balance": str(r.initial_balance),
                "final_balance": str(r.final_balance),
                "order_qty": str(r.order_qty),
                "min_profit": str(r.min_profit),
                "slippage": str(r.slippage),
                "created_at": r.created_at.isoformat(),
                "trade_count": total,
                "win_rate": complete / total if total else 0.0,
                "total_pnl": str(r.final_balance - r.initial_balance),
            }
        )
    return out


@router.get("/{run_id}/trades")
async def list_backtest_trades(run_id: int, db: AsyncSession = Depends(get_db)) -> list[dict]:
    run = (
        await db.execute(select(BacktestRun).where(BacktestRun.id == run_id))
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="backtest run not found")
    trades = (
        (
            await db.execute(
                select(BacktestTrade)
                .where(BacktestTrade.run_id == run_id)
                .order_by(BacktestTrade.timestamp)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": t.id,
            "timestamp": t.timestamp.isoformat(),
            "arb_id": t.arb_id,
            "leg1_pair": t.leg1_pair,
            "leg2_pair": t.leg2_pair,
            "leg3_pair": t.leg3_pair,
            "expected_profit": str(t.expected_profit),
            "actual_profit": str(t.actual_profit) if t.actual_profit is not None else None,
            "status": t.status,
        }
        for t in trades
    ]
```

- [ ] **Step 6: `app/main.py` 라우터 등록**

import 라인 교체:

```python
from app.routes import backtests, internal, positions, trades, ws_alerts
```

`app.include_router(trades.router)` 아래에 추가:

```python
app.include_router(backtests.router)
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: 신규 3개 포함 전체 통과

- [ ] **Step 8: 커밋**

```bash
git add api-server/app/routes/backtests.py api-server/app/models.py api-server/app/main.py api-server/tests/test_backtests.py api-server/pyproject.toml api-server/uv.lock
git commit -m "feat(api): /backtests endpoints for run list and trades"
```

---

## Task 5: 대시보드 — 탭 + BacktestPanel

**Files:**
- Modify: `web-dashboard/vite.config.ts` (proxy 추가)
- Create: `web-dashboard/src/api/backtests.ts`
- Create: `web-dashboard/src/components/BacktestPanel.tsx`
- Modify: `web-dashboard/src/App.tsx` (탭 전환)

**Interfaces:**
- Consumes: Task 4의 두 엔드포인트 응답 형식

- [ ] **Step 1: vite proxy 추가** — `vite.config.ts` proxy 객체에:

```typescript
      "/backtests": "http://localhost:8000",
```

- [ ] **Step 2: `src/api/backtests.ts` 작성**

```typescript
export interface BacktestRun {
  id: number;
  start_date: string;
  end_date: string;
  initial_balance: string;
  final_balance: string;
  order_qty: string;
  min_profit: string;
  slippage: string;
  created_at: string;
  trade_count: number;
  win_rate: number;
  total_pnl: string;
}

export interface BacktestTrade {
  id: number;
  timestamp: string;
  arb_id: string;
  leg1_pair: string;
  leg2_pair: string;
  leg3_pair: string;
  expected_profit: string;
  actual_profit: string | null;
  status: string;
}

export async function fetchBacktestRuns(limit = 50): Promise<BacktestRun[]> {
  const res = await fetch(`/backtests?limit=${limit}`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} fetching /backtests`);
  }
  return res.json();
}

export async function fetchBacktestTrades(runId: number): Promise<BacktestTrade[]> {
  const res = await fetch(`/backtests/${runId}/trades`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} fetching /backtests/${runId}/trades`);
  }
  return res.json();
}
```

- [ ] **Step 3: `src/components/BacktestPanel.tsx` 작성**

```tsx
import { useEffect, useState } from "react";
import {
  BacktestRun,
  BacktestTrade,
  fetchBacktestRuns,
  fetchBacktestTrades,
} from "../api/backtests";

const STATUS_COLOR: Record<string, string> = {
  COMPLETE: "text-green-600 font-semibold",
  UNWIND_COMPLETE: "text-yellow-600 font-semibold",
  TIMEOUT: "text-gray-400",
  FAILED: "text-red-500",
};

function pnlColor(value: string): string {
  return parseFloat(value) >= 0 ? "text-green-600" : "text-red-600";
}

function SummaryCard({ label, value, className = "" }: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-lg font-semibold ${className}`}>{value}</p>
    </div>
  );
}

export function BacktestPanel() {
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [selected, setSelected] = useState<BacktestRun | null>(null);
  const [trades, setTrades] = useState<BacktestTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchBacktestRuns()
      .then((rs) => {
        setRuns(rs);
        if (rs.length > 0) setSelected(rs[0]);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    fetchBacktestTrades(selected.id)
      .then(setTrades)
      .catch((err) => setError(String(err)));
  }, [selected]);

  if (loading) return <p className="text-gray-400 text-sm">불러오는 중...</p>;
  if (error) return <p className="text-red-500 text-sm">오류: {error}</p>;
  if (runs.length === 0)
    return <p className="text-gray-400 text-sm">백테스트 실행 이력 없음</p>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-1">
        <ul className="divide-y">
          {runs.map((run) => (
            <li key={run.id}>
              <button
                onClick={() => setSelected(run)}
                className={`w-full text-left px-3 py-2 rounded hover:bg-gray-50 ${
                  selected?.id === run.id ? "bg-blue-50" : ""
                }`}
              >
                <span className="font-mono text-xs text-gray-500">
                  #{run.id}
                </span>{" "}
                <span className="text-sm">
                  {run.start_date.slice(0, 10)} ~ {run.end_date.slice(0, 10)}
                </span>
                <span className={`ml-2 text-sm ${pnlColor(run.total_pnl)}`}>
                  {parseFloat(run.total_pnl).toFixed(4)} USDT
                </span>
                <span className="ml-2 text-xs text-gray-400">
                  {run.trade_count}건
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="lg:col-span-2">
        {selected && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <SummaryCard
                label="총 PnL"
                value={`${parseFloat(selected.total_pnl).toFixed(4)} USDT`}
                className={pnlColor(selected.total_pnl)}
              />
              <SummaryCard
                label="승률"
                value={`${(selected.win_rate * 100).toFixed(1)}%`}
              />
              <SummaryCard label="거래 수" value={String(selected.trade_count)} />
              <SummaryCard
                label="초기 → 최종"
                value={`${parseFloat(selected.initial_balance).toFixed(0)} → ${parseFloat(selected.final_balance).toFixed(2)}`}
              />
            </div>

            {trades.length === 0 ? (
              <p className="text-gray-400 text-sm">거래 없음</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-gray-100 text-gray-600 uppercase text-xs">
                    <tr>
                      <th className="px-4 py-2">시간</th>
                      <th className="px-4 py-2">경로</th>
                      <th className="px-4 py-2">상태</th>
                      <th className="px-4 py-2">예상 수익</th>
                      <th className="px-4 py-2">실제 수익</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t) => (
                      <tr key={t.id} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-2 font-mono text-xs">
                          {new Date(t.timestamp).toLocaleString()}
                        </td>
                        <td className="px-4 py-2 text-xs">
                          {t.leg1_pair} → {t.leg2_pair} → {t.leg3_pair}
                        </td>
                        <td className={`px-4 py-2 ${STATUS_COLOR[t.status] ?? ""}`}>
                          {t.status}
                        </td>
                        <td className="px-4 py-2">{t.expected_profit}</td>
                        <td
                          className={`px-4 py-2 ${
                            t.actual_profit !== null
                              ? pnlColor(t.actual_profit)
                              : ""
                          }`}
                        >
                          {t.actual_profit ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: `App.tsx` 탭 전환으로 교체**

```tsx
import { useState } from "react";
import { AlertFeed } from "./components/AlertFeed";
import { BacktestPanel } from "./components/BacktestPanel";
import { TradeTable } from "./components/TradeTable";

const TABS = [
  { key: "live", label: "실시간" },
  { key: "backtest", label: "백테스트" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function App() {
  const [tab, setTab] = useState<TabKey>("live");

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">
        Atlas Trading — 어드민
      </h1>

      <nav className="flex gap-2 mb-6">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              tab === t.key
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-600 hover:bg-gray-100"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "live" ? (
        <div className="grid grid-cols-1 gap-6">
          <section className="bg-white rounded-xl shadow p-4">
            <h2 className="text-lg font-semibold text-gray-700 mb-3">
              실시간 알림
            </h2>
            <AlertFeed />
          </section>

          <section className="bg-white rounded-xl shadow p-4">
            <h2 className="text-lg font-semibold text-gray-700 mb-3">
              거래 내역
            </h2>
            <TradeTable />
          </section>
        </div>
      ) : (
        <section className="bg-white rounded-xl shadow p-4">
          <h2 className="text-lg font-semibold text-gray-700 mb-3">
            백테스트 결과
          </h2>
          <BacktestPanel />
        </section>
      )}
    </div>
  );
}
```

- [ ] **Step 5: 빌드 검증**

Run: `cd web-dashboard && npm run build`
Expected: tsc + vite build 성공

- [ ] **Step 6: 수동 확인** — api-server 기동 후 dev 서버로 탭 동작 확인

```bash
# 터미널 1
cd api-server && DATABASE_URL="postgresql+asyncpg://atlas:atlas-local@127.0.0.1:5432/atlas" .venv/bin/uvicorn app.main:app --port 8000
# 터미널 2
cd web-dashboard && npm run dev
```

브라우저 `http://localhost:5173` → 백테스트 탭 → Task 3에서 저장한 run이 목록에 표시되는지 확인

- [ ] **Step 7: 커밋**

```bash
git add web-dashboard/vite.config.ts web-dashboard/src/api/backtests.ts web-dashboard/src/components/BacktestPanel.tsx web-dashboard/src/App.tsx
git commit -m "feat(dashboard): backtest tab with run list, summary, trades"
```

---

## 완료 기준

- [ ] `core-platform`: `pytest tests/ -q` 전체 통과
- [ ] `api-server`: `pytest tests/ -v` 전체 통과 (신규 3개 포함)
- [ ] 로컬 DB에 alembic 0003 적용, `run_backtest.py` 실행 시 `run_id` 출력
- [ ] 대시보드 백테스트 탭에서 실행 목록·요약 카드·거래 테이블 표시
