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
