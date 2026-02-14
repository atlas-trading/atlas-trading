"""Backtest Response Schemas (Frozen Dataclasses)"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TradeResponse:
    """거래 응답"""
    id: int
    backtest_run_id: int
    entry_time: datetime
    exit_time: datetime | None
    side: str
    entry_price: float
    exit_price: float | None
    quantity: float
    pnl: float | None
    pnl_pct: float | None
    commission_paid: float | None


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
    final_capital: float | None
    total_return: float | None
    total_trades: int | None
    win_rate: float | None
    max_drawdown: float | None
    sharpe_ratio: float | None
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
    final_capital: float | None
    total_return: float | None
    total_trades: int | None
    winning_trades: int | None
    losing_trades: int | None
    win_rate: float | None
    max_drawdown: float | None
    sharpe_ratio: float | None
    parameters: str | None
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
    final_capital: float | None
    total_return: float | None
    total_trades: int | None
    winning_trades: int | None
    losing_trades: int | None
    win_rate: float | None
    max_drawdown: float | None
    sharpe_ratio: float | None
    parameters: str | None
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
