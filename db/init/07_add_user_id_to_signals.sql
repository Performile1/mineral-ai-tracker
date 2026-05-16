-- Mineral AI Tracker - Add user_id to signals (PRD v10.0 Phase 10.1)
-- Version: 10.0
-- Description: Add user_id column to investment_signals for user isolation

-- Add user_id to investment_signals
ALTER TABLE investment_signals 
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);

-- Create index for user_id lookups
CREATE INDEX IF NOT EXISTS idx_investment_signals_user_id ON investment_signals(user_id);

-- Ensure user_portfolio has user_id (add if missing)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_portfolio' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE user_portfolio ADD COLUMN user_id UUID REFERENCES users(id);
    END IF;
END $$;

-- Ensure paper_trades has user_id (add if missing)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trades' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE paper_trades ADD COLUMN user_id UUID REFERENCES users(id);
    END IF;
END $$;

-- Create indexes for user_portfolio and paper_trades
CREATE INDEX IF NOT EXISTS idx_user_portfolio_user_id ON user_portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_user_id ON paper_trades(user_id);

-- Comment
COMMENT ON COLUMN investment_signals.user_id IS 'User who generated this signal (for RLS)';
