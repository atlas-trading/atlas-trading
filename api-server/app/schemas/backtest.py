"""Backtest Response Schemas (Frozen Dataclasses)"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class TradeResponse:
    """거래 응답"""
    id: int
    backtest_run_id: int
    entry_time: datetime
    exit_time: Optional[datetime]
    side: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: Optional[float]
    pnl_pct: Optional[float]
    commission_paid: Optional[float]


@dataclass(frozen=True)
class EquityPointResponse:
    """자산 곡선 포인트 응답"""
    timestamp: datetime
    equity: float
    cash: float
    position_value: float


@dataclass(frozen=True)
class BacktestRunSummaryResponse:
    """백테스트 실행 요약 응답 (목록용)"""
    id: int
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    commission: float
    final_capital: Optional[float]
    total_return: Optional[float]
    total_trades: Optional[int]
    win_rate: Optional[float]
    max_drawdown: Optional[float]
    sharpe_ratio: Optional[float]
    created_at: datetime


@dataclass(frozen=True)
class BacktestRunDetailResponse:
    """백테스트 실행 상세 응답"""
    id: int
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    commission: float
    final_capital: Optional[float]
    total_return: Optional[float]
    total_trades: Optional[int]
    winning_trades: Optional[int]
    losing_trades: Optional[int]
    win_rate: Optional[float]
    max_drawdown: Optional[float]
    sharpe_ratio: Optional[float]
    parameters: Optional[str]
    created_at: datetime


@dataclass(frozen=True)
class BacktestRunFullResponse:
    """백테스트 실행 전체 응답 (거래 + 자산 곡선)"""
    id: int
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    commission: float
    final_capital: Optional[float]
    total_return: Optional[float]
    total_trades: Optional[int]
    winning_trades: Optional[int]
    losing_trades: Optional[int]
    win_rate: Optional[float]
    max_drawdown: Optional[float]
    sharpe_ratio: Optional[float]
    parameters: Optional[str]
    created_at: datetime
    trades: list[TradeResponse]
    equity_curve: list[EquityPointResponse]


@dataclass(frozen=True)
class StatsResponse:
    """통계 응답"""
    total_runs: int
    avg_return: float
    max_return: float
    min_return: float
    strategy_stats: list[dict]
