-- Mineral AI Tracker - Alert Tables (PRD v9.0 Phase 1)
-- Version: 9.0
-- Description: Tables for alert configuration and history

-- Alert configurations table
CREATE TABLE IF NOT EXISTS alert_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),
    confidence_threshold INTEGER DEFAULT 90,
    price_drift_threshold DECIMAL(5,2) DEFAULT 8.0,
    alert_on_buy BOOLEAN DEFAULT true,
    alert_on_sell BOOLEAN DEFAULT true,
    alert_on_pass BOOLEAN DEFAULT false,
    telegram_enabled BOOLEAN DEFAULT false,
    telegram_chat_id VARCHAR(255),
    discord_enabled BOOLEAN DEFAULT false,
    discord_webhook_url TEXT,
    email_enabled BOOLEAN DEFAULT false,
    email_address VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Alert history table
CREATE TABLE IF NOT EXISTS alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID REFERENCES investment_signals(id),
    config_id UUID REFERENCES alert_configs(id),
    channel VARCHAR(50),
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20),
    error_message TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_alert_history_signal_id ON alert_history(signal_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_sent_at ON alert_history(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_configs_user_id ON alert_configs(user_id);

-- Comment
COMMENT ON TABLE alert_configs IS 'User alert configuration for The Sentinel notification system';
COMMENT ON TABLE alert_history IS 'History of sent alerts for tracking and debugging';
