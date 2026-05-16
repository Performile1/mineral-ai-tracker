-- Migration: Add Backtesting Results Tables (PRD v10.0 Phase 10.6 - Local PostgreSQL)
-- Description: Tables for storing backtesting results and performance metrics
-- Date: 2026-05-14
-- Note: Removed Supabase-specific auth functions for local PostgreSQL

-- Table: backtest_runs
-- Stores individual backtest run metadata
CREATE TABLE IF NOT EXISTS backtest_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(15, 2) NOT NULL,
    final_capital DECIMAL(15, 2),
    total_return_percentage DECIMAL(10, 4),
    annualized_return DECIMAL(10, 4),
    max_drawdown_percentage DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    win_rate DECIMAL(10, 4),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    average_return_per_trade DECIMAL(10, 4),
    best_trade DECIMAL(10, 4),
    worst_trade DECIMAL(10, 4),
    use_real_data BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID
);

-- Table: backtest_trades
-- Stores individual trades from backtest runs
CREATE TABLE IF NOT EXISTS backtest_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_run_id UUID NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    ticker VARCHAR(50) NOT NULL,
    entry_date DATE NOT NULL,
    exit_date DATE,
    entry_price DECIMAL(15, 4) NOT NULL,
    exit_price DECIMAL(15, 4),
    shares DECIMAL(15, 4) NOT NULL,
    position_size DECIMAL(10, 4) NOT NULL,
    buffett_score DECIMAL(10, 4),
    recommendation VARCHAR(50),
    win BOOLEAN,
    return_pct DECIMAL(10, 4),
    exit_reason VARCHAR(100),
    ai_recommendation VARCHAR(50),
    ai_confidence DECIMAL(10, 4)
);

-- Table: backtest_equity_curve
-- Stores equity curve data points for backtest runs
CREATE TABLE IF NOT EXISTS backtest_equity_curve (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_run_id UUID NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    capital DECIMAL(15, 2) NOT NULL,
    open_positions INTEGER NOT NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_backtest_runs_user_id ON backtest_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_created_at ON backtest_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_backtest_run_id ON backtest_trades(backtest_run_id);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_ticker ON backtest_trades(ticker);
CREATE INDEX IF NOT EXISTS idx_backtest_equity_curve_backtest_run_id ON backtest_equity_curve(backtest_run_id);
CREATE INDEX IF NOT EXISTS idx_backtest_equity_curve_date ON backtest_equity_curve(date);

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON backtest_runs TO mineral_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON backtest_trades TO mineral_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON backtest_equity_curve TO mineral_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mineral_user;
