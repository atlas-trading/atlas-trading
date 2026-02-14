"""Backtest API Endpoints"""
import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

# Add core-platform to sys.path using absolute path
CORE_PLATFORM_PATH = Path("/Users/jang-yeonghwan/atlas-trading/atlas-trading/core-platform")
if str(CORE_PLATFORM_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PLATFORM_PATH))

from app.models.backtest import BacktestRun, BacktestTrade, BacktestEquity
from app.core.database import get_db
from app.schemas.backtest import (
    BacktestRunSummaryResponse,
    BacktestRunDetailResponse,
    BacktestRunFullResponse,
    TradeResponse,
    EquityPointResponse,
    StatsResponse,
)

router = APIRouter()


def _orm_to_summary(obj: BacktestRun) -> BacktestRunSummaryResponse:
    """ORM 객체를 Summary dataclass로 변환"""
    return BacktestRunSummaryResponse(
        id=obj.id,
        strategy_name=obj.strategy_name,
        symbol=obj.symbol,
        timeframe=obj.timeframe,
        start_date=obj.start_date,
        end_date=obj.end_date,
        initial_capital=obj.initial_capital,
        commission=obj.commission,
        final_capital=obj.final_capital,
        total_return=obj.total_return,
        total_trades=obj.total_trades,
        win_rate=obj.win_rate,
        max_drawdown=obj.max_drawdown,
        sharpe_ratio=obj.sharpe_ratio,
        created_at=obj.created_at,
    )


def _orm_to_detail(obj: BacktestRun) -> BacktestRunDetailResponse:
    """ORM 객체를 Detail dataclass로 변환"""
    return BacktestRunDetailResponse(
        id=obj.id,
        strategy_name=obj.strategy_name,
        symbol=obj.symbol,
        timeframe=obj.timeframe,
        start_date=obj.start_date,
        end_date=obj.end_date,
        initial_capital=obj.initial_capital,
        commission=obj.commission,
        final_capital=obj.final_capital,
        total_return=obj.total_return,
        total_trades=obj.total_trades,
        winning_trades=obj.winning_trades,
        losing_trades=obj.losing_trades,
        win_rate=obj.win_rate,
        max_drawdown=obj.max_drawdown,
        sharpe_ratio=obj.sharpe_ratio,
        parameters=obj.parameters,
        created_at=obj.created_at,
    )


def _trade_to_response(obj: BacktestTrade) -> TradeResponse:
    """Trade ORM 객체를 dataclass로 변환"""
    return TradeResponse(
        id=obj.id,
        backtest_run_id=obj.backtest_run_id,
        entry_time=obj.entry_time,
        exit_time=obj.exit_time,
        side=obj.side,
        entry_price=obj.entry_price,
        exit_price=obj.exit_price,
        quantity=obj.quantity,
        pnl=obj.pnl,
        pnl_pct=obj.pnl_pct,
        commission_paid=obj.commission_paid,
    )


def _equity_to_response(obj: BacktestEquity) -> EquityPointResponse:
    """Equity ORM 객체를 dataclass로 변환"""
    return EquityPointResponse(
        timestamp=obj.timestamp,
        equity=obj.equity,
        cash=obj.cash,
        position_value=obj.position_value,
    )


@router.get("/", response_model=list[BacktestRunSummaryResponse])
def list_backtests(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    strategy_name: str | None = None,
    symbol: str | None = None,
    db: Session = Depends(get_db),
) -> list[BacktestRunSummaryResponse]:
    """
    백테스트 실행 목록 조회

    Parameters:
    - skip: 건너뛸 개수 (페이지네이션)
    - limit: 조회할 최대 개수
    - strategy_name: 전략 이름 필터
    - symbol: 심볼 필터
    """
    query = db.query(BacktestRun)

    if strategy_name:
        query = query.filter(BacktestRun.strategy_name == strategy_name)
    if symbol:
        query = query.filter(BacktestRun.symbol == symbol)

    query = query.order_by(BacktestRun.created_at.desc())
    backtests = query.offset(skip).limit(limit).all()

    return [_orm_to_summary(bt) for bt in backtests]


@router.get("/{backtest_id}", response_model=BacktestRunDetailResponse)
def get_backtest(
    backtest_id: int,
    db: Session = Depends(get_db),
) -> BacktestRunDetailResponse:
    """백테스트 실행 상세 조회 (거래 및 자산 곡선 제외)"""
    backtest = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()

    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    return _orm_to_detail(backtest)


@router.get("/{backtest_id}/full", response_model=BacktestRunFullResponse)
def get_backtest_full(
    backtest_id: int,
    db: Session = Depends(get_db),
) -> BacktestRunFullResponse:
    """백테스트 실행 전체 조회 (거래 + 자산 곡선 포함)"""
    backtest = (
        db.query(BacktestRun)
        .options(
            joinedload(BacktestRun.trades),
            joinedload(BacktestRun.equity_curve),
        )
        .filter(BacktestRun.id == backtest_id)
        .first()
    )

    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    trades = [_trade_to_response(t) for t in backtest.trades]
    equity_curve = [_equity_to_response(e) for e in backtest.equity_curve]

    return BacktestRunFullResponse(
        id=backtest.id,
        strategy_name=backtest.strategy_name,
        symbol=backtest.symbol,
        timeframe=backtest.timeframe,
        start_date=backtest.start_date,
        end_date=backtest.end_date,
        initial_capital=backtest.initial_capital,
        commission=backtest.commission,
        final_capital=backtest.final_capital,
        total_return=backtest.total_return,
        total_trades=backtest.total_trades,
        winning_trades=backtest.winning_trades,
        losing_trades=backtest.losing_trades,
        win_rate=backtest.win_rate,
        max_drawdown=backtest.max_drawdown,
        sharpe_ratio=backtest.sharpe_ratio,
        parameters=backtest.parameters,
        created_at=backtest.created_at,
        trades=trades,
        equity_curve=equity_curve,
    )


@router.get("/{backtest_id}/trades", response_model=list[TradeResponse])
def get_backtest_trades(
    backtest_id: int,
    db: Session = Depends(get_db),
) -> list[TradeResponse]:
    """백테스트 거래 내역 조회"""
    backtest = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    trades = (
        db.query(BacktestTrade)
        .filter(BacktestTrade.backtest_run_id == backtest_id)
        .order_by(BacktestTrade.entry_time)
        .all()
    )

    return [_trade_to_response(t) for t in trades]


@router.get("/{backtest_id}/equity", response_model=list[EquityPointResponse])
def get_backtest_equity(
    backtest_id: int,
    db: Session = Depends(get_db),
) -> list[EquityPointResponse]:
    """백테스트 자산 곡선 조회"""
    backtest = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    equity_curve = (
        db.query(BacktestEquity)
        .filter(BacktestEquity.backtest_run_id == backtest_id)
        .order_by(BacktestEquity.timestamp)
        .all()
    )

    return [_equity_to_response(e) for e in equity_curve]


@router.get("/stats/summary", response_model=StatsResponse)
def get_stats_summary(db: Session = Depends(get_db)) -> StatsResponse:
    """전체 백테스트 통계 요약"""
    total_runs = db.query(func.count(BacktestRun.id)).scalar() or 0

    avg_return = db.query(func.avg(BacktestRun.total_return)).scalar()
    max_return = db.query(func.max(BacktestRun.total_return)).scalar()
    min_return = db.query(func.min(BacktestRun.total_return)).scalar()

    strategy_stats = (
        db.query(
            BacktestRun.strategy_name,
            func.count(BacktestRun.id).label("count"),
            func.avg(BacktestRun.total_return).label("avg_return"),
        )
        .group_by(BacktestRun.strategy_name)
        .all()
    )

    return StatsResponse(
        total_runs=total_runs,
        avg_return=float(avg_return) if avg_return else 0.0,
        max_return=float(max_return) if max_return else 0.0,
        min_return=float(min_return) if min_return else 0.0,
        strategy_stats=[
            {
                "strategy_name": stat.strategy_name,
                "count": stat.count,
                "avg_return": float(stat.avg_return) if stat.avg_return else 0.0,
            }
            for stat in strategy_stats
        ],
    )
