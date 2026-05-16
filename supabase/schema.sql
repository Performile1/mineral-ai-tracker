-- ============================================================================
-- Mineral AI Tracker - Supabase PostgreSQL Schema
-- Version: 3.0
-- Description: Database schema for Buffett-Radar mineral investment tracking system
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- TABLE: Assets (Mineral/Commodity Assets)
-- Description: Stores information about mineral stocks, commodities, and mining assets
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    asset_type VARCHAR(50) NOT NULL CHECK (asset_type IN ('stock', 'commodity', 'etf')),
    commodity_type VARCHAR(50) CHECK (commodity_type IN ('lithium', 'cobalt', 'nickel', 'copper', 'rare_earth', 'uranium', 'gold', 'other')),
    country_code VARCHAR(2) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    isin VARCHAR(20) UNIQUE,
    sector VARCHAR(100),
    stage VARCHAR(50) CHECK (stage IN ('prospecting', 'exploration', 'development', 'production')),
    production_capacity_tonnes DECIMAL(18, 2),
    reserve_estimate_tonnes DECIMAL(18, 2),
    
    -- Discovery & Status (PRD v3.1)
    status VARCHAR(20) NOT NULL DEFAULT 'verified' CHECK (status IN ('verified', 'user_added', 'scouted')),
    discovery_source TEXT, -- URL or source where asset was discovered
    
    -- Financial data
    current_price DECIMAL(18, 4),
    market_cap_million DECIMAL(18, 2),
    pe_ratio DECIMAL(10, 2),
    dividend_yield DECIMAL(5, 4),
    
    -- Buffett Score components
    macro_score DECIMAL(5, 4) CHECK (macro_score BETWEEN 0 AND 1),
    commodity_aisc_score DECIMAL(5, 4) CHECK (commodity_aisc_score BETWEEN 0 AND 1),
    geo_policy_score DECIMAL(5, 4) CHECK (geo_policy_score BETWEEN 0 AND 1),
    insider_score DECIMAL(5, 4) CHECK (insider_score BETWEEN 0 AND 1),
    trader_sentiment_score DECIMAL(5, 4) CHECK (trader_sentiment_score BETWEEN 0 AND 1),
    
    -- Composite scores
    buffett_score DECIMAL(5, 4) CHECK (buffett_score BETWEEN 0 AND 1),
    confidence_score DECIMAL(5, 4) CHECK (confidence_score BETWEEN 0 AND 1),
    
    -- Risk management
    target_price DECIMAL(18, 4),
    stop_loss DECIMAL(18, 4),
    kelly_position_size DECIMAL(5, 4) CHECK (kelly_position_size BETWEEN 0 AND 1),
    risk_reward_ratio DECIMAL(5, 4),
    
    -- Metadata
    logo_url TEXT,
    avanza_url TEXT,
    nordnet_url TEXT,
    last_price_update TIMESTAMP WITH TIME ZONE,
    last_score_update TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- TABLE: MacroDemand (Industrial Macro Data)
-- Description: Stores macroeconomic demand indicators from IEA, Eurostat, LME, etc.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.macro_demand (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES public.assets(id) ON DELETE CASCADE,
    
    -- Demand indicators
    source VARCHAR(50) NOT NULL CHECK (source IN ('IEA', 'Eurostat', 'LME', 'Benchmark', 'other')),
    indicator_type VARCHAR(100) NOT NULL,
    indicator_value DECIMAL(18, 4),
    unit VARCHAR(50),
    
    -- Time series data
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- Metadata
    data_quality_score DECIMAL(5, 4) CHECK (data_quality_score BETWEEN 0 AND 1),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- AI/RAG support (768 dimensions for Ollama embeddings)
    embedding vector(768),
    
    UNIQUE(asset_id, source, indicator_type, period_start)
);

-- ============================================================================
-- TABLE: GeoEvents (Geopolitical & Policy Events)
-- Description: Stores geopolitical events, policy changes (CRMA, IRA), and regulatory updates
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.geo_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event details
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('policy', 'regulation', 'geopolitical', 'trade_war', 'sanction', 'black_swan')),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    
    -- Geographic scope
    country_code VARCHAR(2),
    region VARCHAR(100),
    
    -- Impact assessment
    affected_commodities VARCHAR(100)[], -- Array of commodity types
    impact_level VARCHAR(20) CHECK (impact_level IN ('low', 'medium', 'high', 'critical')),
    sentiment_score DECIMAL(5, 4) CHECK (sentiment_score BETWEEN -1 AND 1),
    
    -- Time data
    event_date DATE NOT NULL,
    is_ongoing BOOLEAN DEFAULT FALSE,
    end_date DATE,
    
    -- Sources
    source VARCHAR(100) NOT NULL,
    source_url TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- AI/RAG support (768 dimensions for Ollama embeddings)
    embedding vector(768)
);

-- ============================================================================
-- TABLE: AssetTags (Automatic Tagging for Discovered Assets)
-- Description: PRD v3.1 - Tags for automatic categorization of discovered assets
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.asset_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES public.assets(id) ON DELETE CASCADE,
    
    -- Tag details
    tag_name VARCHAR(50) NOT NULL,
    tag_category VARCHAR(30) CHECK (tag_category IN ('commodity', 'region', 'stage', 'technology', 'other')),
    
    -- Tag metadata
    auto_generated BOOLEAN DEFAULT TRUE,
    confidence DECIMAL(5, 4) CHECK (confidence BETWEEN 0 AND 1),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(asset_id, tag_name)
);

-- ============================================================================
-- TABLE: TraderSentiment (Social & Trader Sentiment)
-- Description: Scraped sentiment from forums, trader blogs, Reddit, eToro profiles
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.trader_sentiment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES public.assets(id) ON DELETE CASCADE,
    
    -- Source details
    source_platform VARCHAR(50) NOT NULL CHECK (source_platform IN ('placera', 'reddit', 'etoro', 'trader_blog', 'other')),
    source_url TEXT NOT NULL,
    author_handle VARCHAR(255),
    
    -- Content analysis
    post_title VARCHAR(500),
    post_content TEXT,
    sentiment_score DECIMAL(5, 4) CHECK (sentiment_score BETWEEN -1 AND 1),
    confidence DECIMAL(5, 4) CHECK (confidence BETWEEN 0 AND 1),
    
    -- Trader credentials (for weighting)
    trader_success_rate DECIMAL(5, 4) CHECK (trader_success_rate BETWEEN 0 AND 1),
    trader_followers_count INTEGER,
    is_verified_trader BOOLEAN DEFAULT FALSE,
    
    -- Trade details (if available)
    trade_direction VARCHAR(10) CHECK (trade_direction IN ('long', 'short', 'neutral')),
    trade_timeframe VARCHAR(20),
    entry_price DECIMAL(18, 4),
    target_price DECIMAL(18, 4),
    
    -- Outcome tracking (for learning)
    actual_outcome VARCHAR(20) CHECK (actual_outcome IN ('profit', 'loss', 'breakeven', 'pending')),
    outcome_percentage DECIMAL(10, 4),
    outcome_date DATE,
    
    -- Metadata
    post_date TIMESTAMP WITH TIME ZONE NOT NULL,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- TABLE: TradeJournal (RLHF Feedback Loop)
-- Description: User trade journaling for reinforcement learning from human feedback
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.trade_journal (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL, -- Links to Supabase auth.users
    asset_id UUID REFERENCES public.assets(id) ON DELETE CASCADE,
    
    -- AI Recommendation at time of trade
    ai_buffett_score DECIMAL(5, 4) CHECK (ai_buffett_score BETWEEN 0 AND 1),
    ai_confidence DECIMAL(5, 4) CHECK (ai_confidence BETWEEN 0 AND 1),
    ai_recommendation VARCHAR(20) CHECK (ai_recommendation IN ('strong_buy', 'buy', 'hold', 'sell', 'strong_sell')),
    ai_kelly_position_size DECIMAL(5, 4) CHECK (ai_kelly_position_size BETWEEN 0 AND 1),
    
    -- User Decision
    user_decision VARCHAR(20) CHECK (user_decision IN ('buy', 'sell', 'hold', 'ignore')),
    user_position_size DECIMAL(18, 4),
    user_reasoning TEXT,
    
    -- Trade Execution
    entry_price DECIMAL(18, 4),
    exit_price DECIMAL(18, 4),
    entry_date TIMESTAMP WITH TIME ZONE,
    exit_date TIMESTAMP WITH TIME ZONE,
    
    -- Outcome (evaluated after 3 months or when position closed)
    actual_return_percentage DECIMAL(10, 4),
    outcome VARCHAR(20) CHECK (outcome IN ('profit', 'loss', 'breakeven', 'pending')),
    holding_period_days INTEGER,
    
    -- Learning metrics
    ai_was_correct BOOLEAN,
    user_was_correct BOOLEAN,
    learning_weight_adjustment DECIMAL(5, 4), -- Adjustment to apply to formula weights
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- TABLE: UserPortfolio (User Portfolio Holdings)
-- Description: Tracks user's current portfolio holdings
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.user_portfolio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL, -- Links to Supabase auth.users
    asset_id UUID REFERENCES public.assets(id) ON DELETE CASCADE,
    
    -- Position details
    shares_held DECIMAL(18, 4) NOT NULL,
    average_cost DECIMAL(18, 4) NOT NULL,
    current_value DECIMAL(18, 4),
    unrealized_pnl DECIMAL(18, 4),
    unrealized_pnl_percentage DECIMAL(10, 4),
    
    -- Risk management
    stop_loss_price DECIMAL(18, 4),
    target_price DECIMAL(18, 4),
    is_stop_loss_active BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    purchased_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, asset_id)
);

-- ============================================================================
-- TABLE: Alerts (SMS & Notification Alerts)
-- Description: Stores alert configurations and trigger history
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL, -- Links to Supabase auth.users
    asset_id UUID REFERENCES public.assets(id) ON DELETE CASCADE,
    
    -- Alert configuration
    alert_type VARCHAR(30) NOT NULL CHECK (alert_type IN ('stop_loss', 'target_price', 'buffett_score', 'geo_event', 'price_change')),
    threshold_value DECIMAL(18, 4),
    comparison_operator VARCHAR(10) CHECK (comparison_operator IN ('above', 'below', 'equal')),
    
    -- Alert status
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    trigger_count INTEGER DEFAULT 0,
    
    -- SMS delivery
    sms_sent BOOLEAN DEFAULT FALSE,
    sms_sent_at TIMESTAMP WITH TIME ZONE,
    sms_status VARCHAR(20) CHECK (sms_status IN ('pending', 'sent', 'delivered', 'failed')),
    
    -- Metadata
    message_template TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- TABLE: BacktestingResults (Backtesting Engine Results)
-- Description: Stores backtesting results for strategy validation
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.backtesting_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL, -- Links to Supabase auth.users
    
    -- Backtesting parameters
    strategy_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(18, 2) NOT NULL,
    
    -- Formula weights used
    weight_macro DECIMAL(5, 4) NOT NULL,
    weight_commodity DECIMAL(5, 4) NOT NULL,
    weight_geo DECIMAL(5, 4) NOT NULL,
    weight_insider DECIMAL(5, 4) NOT NULL,
    weight_sentiment DECIMAL(5, 4) NOT NULL,
    
    -- Performance metrics
    final_capital DECIMAL(18, 2),
    total_return_percentage DECIMAL(10, 4),
    annualized_return DECIMAL(10, 4),
    max_drawdown_percentage DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    win_rate DECIMAL(5, 4),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    
    -- Benchmark comparison
    benchmark_return_percentage DECIMAL(10, 4),
    alpha DECIMAL(10, 4),
    beta DECIMAL(10, 4),
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES (Performance Optimization)
-- ============================================================================

-- Assets indexes
CREATE INDEX IF NOT EXISTS idx_assets_ticker ON public.assets(ticker);
CREATE INDEX IF NOT EXISTS idx_assets_commodity_type ON public.assets(commodity_type);
CREATE INDEX IF NOT EXISTS idx_assets_country ON public.assets(country_code);
CREATE INDEX IF NOT EXISTS idx_assets_buffett_score ON public.assets(buffett_score DESC);
CREATE INDEX IF NOT EXISTS idx_assets_stage ON public.assets(stage);

-- MacroDemand indexes
CREATE INDEX IF NOT EXISTS idx_macro_demand_asset_id ON public.macro_demand(asset_id);
CREATE INDEX IF NOT EXISTS idx_macro_demand_source ON public.macro_demand(source);
CREATE INDEX IF NOT EXISTS idx_macro_demand_period ON public.macro_demand(period_start, period_end);

-- GeoEvents indexes
CREATE INDEX IF NOT EXISTS idx_geo_events_type ON public.geo_events(event_type);
CREATE INDEX IF NOT EXISTS idx_geo_events_date ON public.geo_events(event_date DESC);
CREATE INDEX IF NOT EXISTS idx_geo_events_impact ON public.geo_events(impact_level);
CREATE INDEX IF NOT EXISTS idx_geo_events_commodities ON public.geo_events USING GIN(affected_commodities);

-- TraderSentiment indexes
CREATE INDEX IF NOT EXISTS idx_trader_sentiment_asset_id ON public.trader_sentiment(asset_id);
CREATE INDEX IF NOT EXISTS idx_trader_sentiment_platform ON public.trader_sentiment(source_platform);
CREATE INDEX IF NOT EXISTS idx_trader_sentiment_date ON public.trader_sentiment(post_date DESC);
CREATE INDEX IF NOT EXISTS idx_trader_sentiment_outcome ON public.trader_sentiment(actual_outcome);

-- TradeJournal indexes
CREATE INDEX IF NOT EXISTS idx_trade_journal_user_id ON public.trade_journal(user_id);
CREATE INDEX IF NOT EXISTS idx_trade_journal_asset_id ON public.trade_journal(asset_id);
CREATE INDEX IF NOT EXISTS idx_trade_journal_outcome ON public.trade_journal(outcome);
CREATE INDEX IF NOT EXISTS idx_trade_journal_ai_correct ON public.trade_journal(ai_was_correct);

-- UserPortfolio indexes
CREATE INDEX IF NOT EXISTS idx_user_portfolio_user_id ON public.user_portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_user_portfolio_asset_id ON public.user_portfolio(asset_id);

-- Alerts indexes
CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON public.alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_asset_id ON public.alerts(asset_id);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON public.alerts(is_active);

-- BacktestingResults indexes
CREATE INDEX IF NOT EXISTS idx_backtesting_user_id ON public.backtesting_results(user_id);
CREATE INDEX IF NOT EXISTS idx_backtesting_dates ON public.backtesting_results(start_date, end_date);

-- AssetTags indexes (PRD v3.1)
CREATE INDEX IF NOT EXISTS idx_asset_tags_asset_id ON public.asset_tags(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_tags_name ON public.asset_tags(tag_name);
CREATE INDEX IF NOT EXISTS idx_asset_tags_category ON public.asset_tags(tag_category);

-- Assets indexes for discovery (PRD v3.1)
CREATE INDEX IF NOT EXISTS idx_assets_status ON public.assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_isin ON public.assets(isin);
CREATE INDEX IF NOT EXISTS idx_assets_discovery_source ON public.assets(discovery_source);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.macro_demand ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.geo_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trader_sentiment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trade_journal ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_portfolio ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.backtesting_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.asset_tags ENABLE ROW LEVEL SECURITY;

-- Assets RLS Policies (Public read, authenticated write)
CREATE POLICY "Assets: Public read access" ON public.assets
    FOR SELECT USING (true);

CREATE POLICY "Assets: Authenticated insert" ON public.assets
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "Assets: Authenticated update" ON public.assets
    FOR UPDATE USING (auth.uid() IS NOT NULL);

-- MacroDemand RLS Policies (Public read, authenticated write)
CREATE POLICY "MacroDemand: Public read access" ON public.macro_demand
    FOR SELECT USING (true);

CREATE POLICY "MacroDemand: Authenticated insert" ON public.macro_demand
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "MacroDemand: Authenticated update" ON public.macro_demand
    FOR UPDATE USING (auth.uid() IS NOT NULL);

-- GeoEvents RLS Policies (Public read, authenticated write)
CREATE POLICY "GeoEvents: Public read access" ON public.geo_events
    FOR SELECT USING (true);

CREATE POLICY "GeoEvents: Authenticated insert" ON public.geo_events
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "GeoEvents: Authenticated update" ON public.geo_events
    FOR UPDATE USING (auth.uid() IS NOT NULL);

-- TraderSentiment RLS Policies (Public read, authenticated write)
CREATE POLICY "TraderSentiment: Public read access" ON public.trader_sentiment
    FOR SELECT USING (true);

CREATE POLICY "TraderSentiment: Authenticated insert" ON public.trader_sentiment
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "TraderSentiment: Authenticated update" ON public.trader_sentiment
    FOR UPDATE USING (auth.uid() IS NOT NULL);

-- TradeJournal RLS Policies (User-specific access)
CREATE POLICY "TradeJournal: User read own" ON public.trade_journal
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "TradeJournal: User insert own" ON public.trade_journal
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "TradeJournal: User update own" ON public.trade_journal
    FOR UPDATE USING (user_id = auth.uid());

-- UserPortfolio RLS Policies (User-specific access)
CREATE POLICY "UserPortfolio: User read own" ON public.user_portfolio
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "UserPortfolio: User insert own" ON public.user_portfolio
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "UserPortfolio: User update own" ON public.user_portfolio
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "UserPortfolio: User delete own" ON public.user_portfolio
    FOR DELETE USING (user_id = auth.uid());

-- Alerts RLS Policies (User-specific access)
CREATE POLICY "Alerts: User read own" ON public.alerts
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Alerts: User insert own" ON public.alerts
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Alerts: User update own" ON public.alerts
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "Alerts: User delete own" ON public.alerts
    FOR DELETE USING (user_id = auth.uid());

-- BacktestingResults RLS Policies (User-specific access)
CREATE POLICY "BacktestingResults: User read own" ON public.backtesting_results
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "BacktestingResults: User insert own" ON public.backtesting_results
    FOR INSERT WITH CHECK (user_id = auth.uid());

-- AssetTags RLS Policies (Public read, authenticated write) (PRD v3.1)
CREATE POLICY "AssetTags: Public read access" ON public.asset_tags
    FOR SELECT USING (true);

CREATE POLICY "AssetTags: Authenticated insert" ON public.asset_tags
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "AssetTags: Authenticated update" ON public.asset_tags
    FOR UPDATE USING (auth.uid() IS NOT NULL);

CREATE POLICY "AssetTags: Authenticated delete" ON public.asset_tags
    FOR DELETE USING (auth.uid() IS NOT NULL);

-- ============================================================================
-- TRIGGERS & FUNCTIONS (Automatic Timestamp Updates)
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers to all relevant tables
CREATE TRIGGER update_assets_updated_at BEFORE UPDATE ON public.assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_macro_demand_updated_at BEFORE UPDATE ON public.macro_demand
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_geo_events_updated_at BEFORE UPDATE ON public.geo_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trader_sentiment_updated_at BEFORE UPDATE ON public.trader_sentiment
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trade_journal_updated_at BEFORE UPDATE ON public.trade_journal
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_portfolio_updated_at BEFORE UPDATE ON public.user_portfolio
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON public.alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS (Common Query Patterns)
-- ============================================================================

-- View: Assets with composite score
CREATE OR REPLACE VIEW public.v_assets_summary AS
SELECT 
    a.id,
    a.ticker,
    a.name,
    a.asset_type,
    a.commodity_type,
    a.country_code,
    a.current_price,
    a.buffett_score,
    a.confidence_score,
    a.target_price,
    a.stop_loss,
    a.kelly_position_size,
    a.stage,
    a.logo_url,
    a.avanza_url,
    a.nordnet_url,
    a.last_price_update,
    COUNT(DISTINCT ts.id) as sentiment_count,
    AVG(ts.sentiment_score) as avg_sentiment_score,
    COUNT(DISTINCT ge.id) as relevant_geo_events
FROM public.assets a
LEFT JOIN public.trader_sentiment ts ON a.id = ts.asset_id
LEFT JOIN public.geo_events ge ON a.commodity_type = ANY(ge.affected_commodities)
GROUP BY a.id;

-- View: User portfolio with performance
CREATE OR REPLACE VIEW public.v_user_portfolio_performance AS
SELECT 
    up.id,
    up.user_id,
    up.asset_id,
    a.ticker,
    a.name,
    a.current_price,
    up.shares_held,
    up.average_cost,
    up.current_value,
    up.unrealized_pnl,
    up.unrealized_pnl_percentage,
    up.stop_loss_price,
    up.target_price,
    up.is_stop_loss_active,
    up.purchased_at
FROM public.user_portfolio up
JOIN public.assets a ON up.asset_id = a.id;

-- ============================================================================
-- AI/RAG: Similarity Search Functions
-- ============================================================================

-- Function to search macro_demand by embedding similarity
CREATE OR REPLACE FUNCTION match_macro_demand (
  query_embedding vector(768),
  match_threshold float DEFAULT 0.5,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id uuid,
  asset_id uuid,
  indicator_type text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    md.id,
    md.asset_id,
    md.indicator_type,
    1 - (md.embedding <=> query_embedding) AS similarity
  FROM macro_demand md
  WHERE md.embedding IS NOT NULL
    AND 1 - (md.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;

-- Function to search geo_events by embedding similarity
CREATE OR REPLACE FUNCTION match_geo_events (
  query_embedding vector(768),
  match_threshold float DEFAULT 0.5,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id uuid,
  event_type text,
  title text,
  description text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    ge.id,
    ge.event_type,
    ge.title,
    ge.description,
    1 - (ge.embedding <=> query_embedding) AS similarity
  FROM geo_events ge
  WHERE ge.embedding IS NOT NULL
    AND 1 - (ge.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;

-- ============================================================================
-- SCHEMA VALIDATION COMPLETE
-- ============================================================================
