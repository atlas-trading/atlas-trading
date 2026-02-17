/**
 * Paper Trading TypeScript Types
 * Based on backend schemas: app/schemas/paper_trading.py
 */

export type SessionStatus = "active" | "paused" | "stopped" | "completed";

export interface PaperTradingSession {
  id: number;
  name: string | null;
  symbol: string;
  strategy: string;
  initial_capital: number;
  current_balance: number;
  current_equity: number;
  status: SessionStatus;
  start_time: string; // ISO 8601 datetime
  end_time: string | null; // ISO 8601 datetime
  last_update: string; // ISO 8601 datetime
  settings: Record<string, any> | null;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  total_pnl: number;
  total_commission: number;
  max_equity: number | null;
  max_drawdown: number;
}

export interface PaperTradingSessionCreate {
  name?: string | null;
  symbol: string;
  strategy: string;
  initial_capital: number;
  settings?: Record<string, any> | null;
}

export interface PaperTradingTrade {
  id: number;
  session_id: number;
  symbol: string;
  side: string; // "buy" | "sell"
  position_side: string; // "long" | "short"
  quantity: number;
  entry_price: number | null;
  exit_price: number | null;
  commission: number;
  slippage: number;
  pnl: number | null;
  pnl_percent: number | null;
  position_type: string | null;
  stop_loss: number | null;
  take_profit: number | null;
  exit_reason: string | null;
  timestamp: string; // ISO 8601 datetime
}

export interface PaperTradingSnapshot {
  id: number;
  session_id: number;
  balance: number;
  equity: number;
  unrealized_pnl: number;
  open_positions: Array<Record<string, any>> | null;
  market_price: number | null;
  timestamp: string; // ISO 8601 datetime
}

export interface PaperTradingStats {
  session_id: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number; // percentage
  total_pnl: number;
  total_commission: number;
  total_return: number; // percentage
  max_drawdown: number;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
}

export interface KlineData {
  time: number; // Unix timestamp in milliseconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}
