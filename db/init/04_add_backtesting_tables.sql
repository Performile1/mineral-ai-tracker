-- Mineral AI Tracker - Backtesting Tables (PRD v9.0 Phase 3)
-- Version: 9.0
-- Description: Tables for storing backtest results and trade history

-- Backtest runs table
CREATE TABLE IF NOT EXISTS backtest_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(15,2) NOT NULL,
    final_capital DECIMAL(15,2),
    total_return_pct DECIMAL(10,2),
    sharpe_ratio DECIMAL(10,4),
    max_drawdown_pct DECIMAL(10,2),
    win_rate DECIMAL(5,2),
    trade_count INTEGER,
    kelly_effectiveness JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Backtest trades table
CREATE TABLE IF NOT EXISTS backtest_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_run_id UUID REFERENCES backtest_runs(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    entry_date DATE NOT NULL,
    exit_date DATE,
    entry_price DECIMAL(15,4),
    exit_price DECIMAL(15,4),
    shares DECIMAL(15,4),
    position_size DECIMAL(15,2),
    ai_recommendation VARCHAR(20),
    ai_confidence INTEGER,
    win BOOLEAN,
    return_pct DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy ON backtest_runs(strategy_name);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_created_at ON backtest_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_run_id ON backtest_trades(backtest_run_id);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_ticker ON backtest_trades(ticker);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_entry_date ON backtest_trades(entry_date);

-- Comments
COMMENT ON TABLE backtest_runs IS 'Historical backtest simulation results for The Time Machine';
COMMENT ON TABLE backtest_trades IS 'Individual trades from backtest simulations';
