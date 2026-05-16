-- Migration: Add Credits System (Phase 12 - The Alpha & Economics Sprint)
-- Purpose: Add credits_remaining column to users table for monetization and API protection
-- Date: 2026-05-15

-- Add credits_remaining column to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS credits_remaining INT DEFAULT 10;

-- Add index on credits_remaining for faster queries
CREATE INDEX IF NOT EXISTS idx_users_credits_remaining ON users(credits_remaining);

-- Add credits_used column for tracking total usage
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS credits_used INT DEFAULT 0;

-- Add credits_last_purchased timestamp for billing tracking
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS credits_last_purchased TIMESTAMP WITH TIME ZONE;

-- Add subscription_tier column for future tiered pricing
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(50) DEFAULT 'free';

-- Update existing users to have default credits
UPDATE users 
SET credits_remaining = 10, 
    subscription_tier = 'free'
WHERE credits_remaining IS NULL OR credits_remaining = 0;
