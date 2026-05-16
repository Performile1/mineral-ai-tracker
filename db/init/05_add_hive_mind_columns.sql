-- Mineral AI Tracker - Hive Mind Columns (PRD v9.0 Phase 10.2)
-- Version: 9.0
-- Description: Add is_public column to investment_signals for swarm intelligence

-- Add is_public column to investment_signals
ALTER TABLE investment_signals 
ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;

-- Add index for efficient hive consensus queries
CREATE INDEX IF NOT EXISTS idx_investment_signals_hive 
ON investment_signals(ticker, is_public, created_at DESC) 
WHERE is_public = TRUE;

-- Comment
COMMENT ON COLUMN investment_signals.is_public IS 'Opt-in flag for sharing analysis with The Hive Mind (Swarm Intelligence)';
