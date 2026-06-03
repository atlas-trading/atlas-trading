from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import ArbAttempt

router = APIRouter(prefix="/positions", tags=["positions"])

_OPEN_STATUSES = {"PENDING", "LEG1_FILLED", "LEG2_FILLED"}


@router.get("")
async def list_positions(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        (await db.execute(select(ArbAttempt).where(ArbAttempt.status.in_(_OPEN_STATUSES))))
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "strategy": r.strategy,
            "status": r.status,
            "expected_profit": str(r.expected_profit) if r.expected_profit else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
