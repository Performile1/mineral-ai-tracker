-- Migration: Add user_id to Signals Tables (Phase 10.1 - NextAuth & RLS)
-- Purpose: Add user_id column to tables that need user isolation for multi-user support
-- Date: 2026-05-15

-- Add user_id to investment_signals table
ALTER TABLE investment_signals 
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL;

-- Create index on user_id for investment_signals
CREATE INDEX IF NOT EXISTS idx_investment_signals_user_id ON investment_signals(user_id);

-- Ensure user_portfolio has user_id (add if not exists)
ALTER TABLE user_portfolio 
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- Create index on user_id for user_portfolio
CREATE INDEX IF NOT EXISTS idx_user_portfolio_user_id ON user_portfolio(user_id);

-- Ensure paper_trades has user_id (add if not exists)
ALTER TABLE paper_trades 
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- Create index on user_id for paper_trades
CREATE INDEX IF NOT EXISTS idx_paper_trades_user_id ON paper_trades(user_id);

-- Add comments
COMMENT ON COLUMN investment_signals.user_id IS 'User who created this signal (for multi-user isolation)';
COMMENT ON COLUMN user_portfolio.user_id IS 'User who owns this portfolio';
COMMENT ON COLUMN paper_trades.user_id IS 'User who owns this paper trade';
