// TypeScript interfaces for backtest data
// Mirrors backend schemas from api-server/app/schemas/backtest.py

export interface BacktestRunSummary {
  id: number;
  strategy_name: string;
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  commission: number;
  final_capital: number | null;
  total_return: number | null;
  total_trades: number | null;
  win_rate: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  created_at: string;
}

export interface BacktestRunDetail extends BacktestRunSummary {
  winning_trades: number | null;
  losing_trades: number | null;
  parameters: string | null;
}

export interface Trade {
  id: number;
  backtest_run_id: number;
  entry_time: string;
  exit_time: string | null;
  side: 'long' | 'short';
  entry_price: number;
  exit_price: number | null;
  quantity: number;
  pnl: number | null;
  pnl_pct: number | null;
  commission_paid: number | null;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
  cash: number;
  position_value: number;
}

export interface AdvancedMetrics {
  sortino_ratio: number;
  calmar_ratio: number;
  profit_factor: number;
  expectancy: number;
  win_loss_ratio: number;
  recovery_factor: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  net_profit: number;
  net_profit_pct: number;
  total_commission_paid: number;
  avg_trade_duration_hours: number;
}

export interface TradeAnalysis {
  avg_holding_hours: number;
  median_holding_hours: number;
  min_holding_hours: number;
  max_holding_hours: number;
  avg_pnl: number;
  median_pnl: number;
  largest_win: number;
  largest_loss: number;
  avg_win: number;
  avg_loss: number;
  small_wins_count: number;
  medium_wins_count: number;
  large_wins_count: number;
  small_losses_count: number;
  medium_losses_count: number;
  large_losses_count: number;
  avg_mae: number | null;
  avg_mfe: number | null;
  avg_efficiency: number | null;
}

export interface MonteCarloResult {
  n_simulations: number;
  initial_capital: number;

  // 최종 자본 통계
  final_capital_mean: number;
  final_capital_median: number;
  final_capital_std: number;
  final_capital_5th: number;
  final_capital_95th: number;
  final_capital_min: number;
  final_capital_max: number;

  // 수익률 통계
  total_return_mean: number;
  total_return_median: number;
  total_return_std: number;
  total_return_5th: number;
  total_return_95th: number;

  // MDD 통계
  max_drawdown_mean: number;
  max_drawdown_median: number;
  max_drawdown_worst: number;
  max_drawdown_best: number;

  // 샤프 비율 통계
  sharpe_ratio_mean: number;
  sharpe_ratio_median: number;

  // 리스크 분석
  probability_of_loss: number;
  value_at_risk_5: number;
  conditional_var_5: number;
  confidence_interval_95: [number, number];
  volatility_ratio: number;
  risk_grade: string;

  // 샘플 데이터
  sample_equity_curves: number[][];
  all_final_capitals: number[];
}

export interface CostStressResult {
  // Base case
  base_sharpe: number;
  base_cagr: number;
  base_total_return: number;
  base_max_drawdown: number;

  // Commission 2x stress
  comm_2x_sharpe: number;
  comm_2x_cagr: number;
  comm_2x_total_return: number;
  comm_2x_sharpe_delta: number;
  comm_2x_sharpe_delta_pct: number;

  // Slippage +1 tick stress
  slip_1tick_sharpe: number;
  slip_1tick_cagr: number;
  slip_1tick_total_return: number;
  slip_1tick_cagr_delta: number;
  slip_1tick_cagr_delta_pct: number;

  // Execution delay (1 bar)
  delay_1bar_sharpe: number;
  delay_1bar_cagr: number;
  delay_1bar_total_return: number;
  delay_1bar_max_drawdown: number;
  delay_1bar_total_return_delta: number;
  delay_1bar_total_return_delta_pct: number;

  // Risk assessment
  passes_stress_test: boolean;
  failure_reasons: string[];
  risk_grade: string;
}

export interface BacktestRunFull extends BacktestRunDetail {
  trades: Trade[];
  equity_curve: EquityPoint[];
}

// Computed analytics interfaces
export interface DrawdownPoint {
  timestamp: string;
  drawdown_pct: number;
  peak_equity: number;
}

export interface RollingMetrics {
  timestamp: string;
  rolling_sharpe: number;
  rolling_volatility: number;
  rolling_return: number;
}
