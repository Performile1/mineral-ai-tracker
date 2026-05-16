-- Migration: Remove Supabase-specific RLS policies (Critical Hotfix)
-- Purpose: Drop RLS policies that use auth.uid() which is Supabase-specific and won't work with local PostgreSQL
-- Date: 2026-05-15
-- Reason: Switching to Application-Level Filtering in FastAPI instead of database-level RLS

-- Disable RLS on all tables
ALTER TABLE investment_signals DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_portfolio DISABLE ROW LEVEL SECURITY;
ALTER TABLE paper_trades DISABLE ROW LEVEL SECURITY;
ALTER TABLE trade_journal DISABLE ROW LEVEL SECURITY;
ALTER TABLE alert_configs DISABLE ROW LEVEL SECURITY;

-- Drop all RLS policies (they use auth.uid() which is Supabase-specific)
DROP POLICY IF EXISTS user_isolation_signals ON investment_signals;
DROP POLICY IF EXISTS user_isolation_portfolio ON user_portfolio;
DROP POLICY IF EXISTS user_isolation_trades ON paper_trades;
DROP POLICY IF EXISTS user_isolation_journal ON trade_journal;
DROP POLICY IF EXISTS user_isolation_alerts ON alert_configs;

-- Comment explaining the change
COMMENT ON TABLE investment_signals IS 'Investment signals - Application-Level Filtering (user_id) in FastAPI, not database RLS';
COMMENT ON TABLE user_portfolio IS 'User portfolio - Application-Level Filtering (user_id) in FastAPI, not database RLS';
COMMENT ON TABLE paper_trades IS 'User paper trades - Application-Level Filtering (user_id) in FastAPI, not database RLS';
COMMENT ON TABLE trade_journal IS 'Trade journal - Application-Level Filtering (user_id) in FastAPI, not database RLS';
COMMENT ON TABLE alert_configs IS 'Alert configurations - Application-Level Filtering (user_id) in FastAPI, not database RLS';
