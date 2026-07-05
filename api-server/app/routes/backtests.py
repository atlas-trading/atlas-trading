from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import BacktestRun, BacktestTrade

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.get("")
async def list_backtests(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    runs = (
        (await db.execute(select(BacktestRun).order_by(desc(BacktestRun.created_at)).limit(limit)))
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
