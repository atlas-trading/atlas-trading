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
