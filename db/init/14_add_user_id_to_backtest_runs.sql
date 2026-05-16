-- Migration: Add user_id to Backtesting Tables (Phase 10.1 - Multi-user Isolation)
-- Purpose: Add user_id column to backtest_runs and backtest_trades for user data isolation
-- Date: 2026-05-16
-- Context: Security hardening - ensure backtest results are isolated per user

-- Add user_id column to backtest_runs
ALTER TABLE backtest_runs 
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id column to backtest_trades
ALTER TABLE backtest_trades 
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Create index on user_id for backtest_runs for performance
CREATE INDEX IF NOT EXISTS idx_backtest_runs_user_id ON backtest_runs(user_id);

-- Create index on user_id for backtest_trades for performance
CREATE INDEX IF NOT EXISTS idx_backtest_trades_user_id ON backtest_trades(user_id);

-- Add comments
COMMENT ON COLUMN backtest_runs.user_id IS 'User who created this backtest run (for multi-user isolation)';
COMMENT ON COLUMN backtest_trades.user_id IS 'User who owns this trade record (for multi-user isolation)';

-- Note: Existing records will have NULL user_id. This is acceptable for historical data.
-- New backtest runs will always include user_id.
