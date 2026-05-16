-- Migration: Add Credit System to Users Table (Phase 13.0 - Tokenomics)
-- Purpose: Add credits_remaining and credits_used columns for credit-based AI analysis
-- Date: 2026-05-16
-- Context: Phase 13 Basic - Credit system for monetization and usage tracking

-- Add credits_remaining column
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS credits_remaining INT DEFAULT 10;

-- Add credits_used column for tracking total credits consumed
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS credits_used INT DEFAULT 0;

-- Create index on credits_remaining for performance
CREATE INDEX IF NOT EXISTS idx_users_credits_remaining ON users(credits_remaining);

-- Add comments
COMMENT ON COLUMN users.credits_remaining IS 'Available credits for AI analysis (default 10 for new users)';
COMMENT ON COLUMN users.credits_used IS 'Total credits consumed by user (lifetime tracking)';
