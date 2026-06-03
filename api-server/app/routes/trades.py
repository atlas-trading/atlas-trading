from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import ArbAttempt

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("")
async def list_trades(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        (await db.execute(select(ArbAttempt).order_by(desc(ArbAttempt.created_at)).limit(limit)))
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "strategy": r.strategy,
            "status": r.status,
            "expected_profit": str(r.expected_profit) if r.expected_profit else None,
            "actual_profit": str(r.actual_profit) if r.actual_profit else None,
            "created_at": r.created_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in rows
    ]
