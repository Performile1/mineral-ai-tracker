-- Migration: Add Backtesting Results Tables (PRD v10.0 Phase 10.6)
-- Description: Tables for storing backtesting results and performance metrics
-- Date: 2026-05-14

-- Table: backtest_runs
-- Stores individual backtest run metadata
CREATE TABLE IF NOT EXISTS backtest_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(15, 2) NOT NULL,
    final_capital DECIMAL(15, 2) NOT NULL,
    total_return_percentage DECIMAL(10, 4) NOT NULL,
    annualized_return DECIMAL(10, 4) NOT NULL,
    max_drawdown_percentage DECIMAL(10, 4) NOT NULL,
    sharpe_ratio DECIMAL(10, 4) NOT NULL,
    win_rate DECIMAL(10, 4) NOT NULL,
    total_trades INTEGER NOT NULL,
    winning_trades INTEGER NOT NULL,
    losing_trades INTEGER NOT NULL,
    average_return_per_trade DECIMAL(10, 4) NOT NULL,
    best_trade DECIMAL(10, 4) NOT NULL,
    worst_trade DECIMAL(10, 4) NOT NULL,
    use_real_data BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL
);

-- Table: backtest_trades
-- Stores individual trades from backtest runs
CREATE TABLE IF NOT EXISTS backtest_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_run_id UUID NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    ticker VARCHAR(50) NOT NULL,
    entry_date DATE NOT NULL,
    exit_date DATE NOT NULL,
    entry_price DECIMAL(15, 4) NOT NULL,
    exit_price DECIMAL(15, 4) NOT NULL,
    shares DECIMAL(15, 4) NOT NULL,
    position_size DECIMAL(10, 4) NOT NULL,
    buffett_score DECIMAL(10, 4) NOT NULL,
    recommendation VARCHAR(50) NOT NULL,
    win BOOLEAN NOT NULL,
    return_pct DECIMAL(10, 4) NOT NULL,
    exit_reason VARCHAR(100) NOT NULL
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

-- Enable RLS
ALTER TABLE backtest_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtest_trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtest_equity_curve ENABLE ROW LEVEL SECURITY;

-- RLS Policies for backtest_runs
CREATE POLICY "Users can view their own backtest runs"
    ON backtest_runs FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can insert their own backtest runs"
    ON backtest_runs FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

-- RLS Policies for backtest_trades
CREATE POLICY "Users can view trades from their own backtest runs"
    ON backtest_trades FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM backtest_runs
            WHERE backtest_runs.id = backtest_trades.backtest_run_id
            AND (backtest_runs.user_id = auth.uid() OR backtest_runs.user_id IS NULL)
        )
    );

CREATE POLICY "Users can insert trades for their own backtest runs"
    ON backtest_trades FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM backtest_runs
            WHERE backtest_runs.id = backtest_trades.backtest_run_id
            AND (backtest_runs.user_id = auth.uid() OR backtest_runs.user_id IS NULL)
        )
    );

-- RLS Policies for backtest_equity_curve
CREATE POLICY "Users can view equity curve from their own backtest runs"
    ON backtest_equity_curve FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM backtest_runs
            WHERE backtest_runs.id = backtest_equity_curve.backtest_run_id
            AND (backtest_runs.user_id = auth.uid() OR backtest_runs.user_id IS NULL)
        )
    );

CREATE POLICY "Users can insert equity curve for their own backtest runs"
    ON backtest_equity_curve FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM backtest_runs
            WHERE backtest_runs.id = backtest_equity_curve.backtest_run_id
            AND (backtest_runs.user_id = auth.uid() OR backtest_runs.user_id IS NULL)
        )
    );

-- Grant necessary permissions
GRANT SELECT, INSERT ON backtest_runs TO mineral_user;
GRANT SELECT, INSERT ON backtest_trades TO mineral_user;
GRANT SELECT, INSERT ON backtest_equity_curve TO mineral_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mineral_user;
