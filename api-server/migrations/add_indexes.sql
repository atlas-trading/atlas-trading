-- Add performance indexes for backtest tables
-- Run this SQL to improve query performance

-- Add index on created_at for faster ORDER BY queries
CREATE INDEX IF NOT EXISTS idx_backtest_runs_created_at
ON backtest_runs(created_at DESC);

-- Add composite index for common filter queries
CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy_symbol
ON backtest_runs(strategy_name, symbol);

-- Add index on symbol for symbol-based filtering
CREATE INDEX IF NOT EXISTS idx_backtest_runs_symbol
ON backtest_runs(symbol);

-- Analyze tables to update statistics
ANALYZE backtest_runs;
ANALYZE backtest_trades;
ANALYZE backtest_equity;

-- Check existing indexes
SELECT
    tablename,
    indexname,
    indexdef
FROM
    pg_indexes
WHERE
    tablename IN ('backtest_runs', 'backtest_trades', 'backtest_equity')
ORDER BY
    tablename, indexname;
