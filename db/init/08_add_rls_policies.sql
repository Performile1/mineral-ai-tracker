-- Mineral AI Tracker - Row Level Security Policies (PRD v10.0 Phase 10.1)
-- Version: 10.0
-- Description: Enable RLS and create policies for user data isolation

-- Enable RLS on investment_signals
ALTER TABLE investment_signals ENABLE ROW LEVEL SECURITY;

-- Create policy for investment_signals - users can only see their own signals
CREATE POLICY user_isolation_signals ON investment_signals
  FOR ALL
  TO authenticated_user
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- Enable RLS on user_portfolio
ALTER TABLE user_portfolio ENABLE ROW LEVEL SECURITY;

-- Create policy for user_portfolio
CREATE POLICY user_isolation_portfolio ON user_portfolio
  FOR ALL
  TO authenticated_user
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- Enable RLS on paper_trades
ALTER TABLE paper_trades ENABLE ROW LEVEL SECURITY;

-- Create policy for paper_trades
CREATE POLICY user_isolation_trades ON paper_trades
  FOR ALL
  TO authenticated_user
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- Enable RLS on trade_journal
ALTER TABLE trade_journal ENABLE ROW LEVEL SECURITY;

-- Create policy for trade_journal
CREATE POLICY user_isolation_journal ON trade_journal
  FOR ALL
  TO authenticated_user
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- Enable RLS on alert_configs
ALTER TABLE alert_configs ENABLE ROW LEVEL SECURITY;

-- Create policy for alert_configs
CREATE POLICY user_isolation_alerts ON alert_configs
  FOR ALL
  TO authenticated_user
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- Comment
COMMENT ON POLICY user_isolation_signals ON investment_signals IS 'Users can only access their own investment signals';
