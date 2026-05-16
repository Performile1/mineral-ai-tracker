-- Migration: Add asset_events table (Phase 12.1 - Event Correlation Engine)
-- Purpose: Store financial news events correlated with price movements
-- Date: 2026-05-15

CREATE TABLE IF NOT EXISTS asset_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(20) NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    source_authority_score DECIMAL(3,2) NOT NULL CHECK (source_authority_score >= 0.1 AND source_authority_score <= 1.0),
    ai_summary TEXT,
    price_impact_4h DECIMAL(10,4), -- Percentage change 4 hours after event
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for efficient queries
    CONSTRAINT unique_event UNIQUE (ticker, published_at, url)
);

-- Index for querying events by ticker
CREATE INDEX IF NOT EXISTS idx_asset_events_ticker ON asset_events(ticker);
CREATE INDEX IF NOT EXISTS idx_asset_events_published_at ON asset_events(published_at);
CREATE INDEX IF NOT EXISTS idx_asset_events_ticker_published ON asset_events(ticker, published_at DESC);

-- Comments
COMMENT ON TABLE asset_events IS 'Financial news events correlated with price movements (Phase 12.1)';
COMMENT ON COLUMN asset_events.source_authority_score IS 'Authority score: 1.0=Financial Reports/SEC, 0.8=PR, 0.4=News Articles';
COMMENT ON COLUMN asset_events.ai_summary IS 'Phi-3 AI summary of the event (one sentence)';
COMMENT ON COLUMN asset_events.price_impact_4h IS 'Price impact percentage 4 hours after event (positive=up, negative=down)';
