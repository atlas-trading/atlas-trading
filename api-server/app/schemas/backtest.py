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


@dataclass(frozen=True)
class AdvancedMetricsResponse:
    """고급 성과 지표 응답"""
    # Risk-adjusted returns
    sortino_ratio: float
    calmar_ratio: float

    # Profitability metrics
    profit_factor: float
    expectancy: float
    win_loss_ratio: float
    recovery_factor: float

    # Streak statistics
    max_consecutive_wins: int
    max_consecutive_losses: int

    # Additional metrics
    net_profit: float
    net_profit_pct: float
    total_commission_paid: float
    avg_trade_duration_hours: float


@dataclass(frozen=True)
class TradeAnalysisResponse:
    """거래 분석 응답"""
    # Holding periods
    avg_holding_hours: float
    median_holding_hours: float
    min_holding_hours: float
    max_holding_hours: float

    # Distribution
    avg_pnl: float
    median_pnl: float
    largest_win: float
    largest_loss: float
    avg_win: float
    avg_loss: float

    # Quality
    small_wins_count: int
    medium_wins_count: int
    large_wins_count: int
    small_losses_count: int
    medium_losses_count: int
    large_losses_count: int

    # MAE/MFE
    avg_mae: float | None
    avg_mfe: float | None
    avg_efficiency: float | None


@dataclass(frozen=True)
class MonteCarloResponse:
    """Monte Carlo 시뮬레이션 결과 응답"""
    n_simulations: int
    initial_capital: float

    # 최종 자본 통계
    final_capital_mean: float
    final_capital_median: float
    final_capital_std: float
    final_capital_5th: float
    final_capital_95th: float
    final_capital_min: float
    final_capital_max: float

    # 수익률 통계
    total_return_mean: float
    total_return_median: float
    total_return_std: float
    total_return_5th: float
    total_return_95th: float

    # MDD 통계
    max_drawdown_mean: float
    max_drawdown_median: float
    max_drawdown_worst: float
    max_drawdown_best: float

    # 샤프 비율 통계
    sharpe_ratio_mean: float
    sharpe_ratio_median: float

    # 리스크 분석
    probability_of_loss: float
    value_at_risk_5: float
    conditional_var_5: float
    confidence_interval_95: tuple[float, float]
    volatility_ratio: float
    risk_grade: str

    # 샘플 데이터
    sample_equity_curves: list[list[float]]
    all_final_capitals: list[float]


@dataclass(frozen=True)
class CostStressResponse:
    """Cost Stress Test 결과 응답"""
    # Base case
    base_sharpe: float
    base_cagr: float
    base_total_return: float
    base_max_drawdown: float

    # Commission 2x stress
    comm_2x_sharpe: float
    comm_2x_cagr: float
    comm_2x_total_return: float
    comm_2x_sharpe_delta: float
    comm_2x_sharpe_delta_pct: float

    # Slippage +1 tick stress
    slip_1tick_sharpe: float
    slip_1tick_cagr: float
    slip_1tick_total_return: float
    slip_1tick_cagr_delta: float
    slip_1tick_cagr_delta_pct: float

    # Execution delay (1 bar)
    delay_1bar_sharpe: float
    delay_1bar_cagr: float
    delay_1bar_total_return: float
    delay_1bar_max_drawdown: float
    delay_1bar_total_return_delta: float
    delay_1bar_total_return_delta_pct: float

    # Risk assessment
    passes_stress_test: bool
    failure_reasons: list[str]
    risk_grade: str
