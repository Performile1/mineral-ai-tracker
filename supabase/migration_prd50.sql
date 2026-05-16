-- ============================================================================
-- PRD v5.0 Migration - Freemium Business Model & Shadow Portfolio
-- Description: Add Users table, PaperTrades, and update RLS for subscription tiers
-- ============================================================================

-- Create Users table
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    
    -- Subscription status
    subscription_tier VARCHAR(20) NOT NULL DEFAULT 'basic' CHECK (subscription_tier IN ('basic', 'pro')),
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    subscription_status VARCHAR(50) CHECK (subscription_status IN ('active', 'past_due', 'canceled', 'trialing', 'incomplete', 'incomplete_expired', 'unpaid')),
    subscription_start_date TIMESTAMP WITH TIME ZONE,
    subscription_end_date TIMESTAMP WITH TIME ZONE,
    
    -- Shadow Portfolio (Paper Trading)
    paper_balance_sek DECIMAL(18, 2) DEFAULT 100000.00,
    paper_initial_balance_sek DECIMAL(18, 2) DEFAULT 100000.00,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- Create PaperTrades table for Shadow Portfolio
CREATE TABLE IF NOT EXISTS public.paper_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES public.assets(id) ON DELETE CASCADE,
    
    -- Trade details
    trade_type VARCHAR(10) NOT NULL CHECK (trade_type IN ('buy', 'sell')),
    shares DECIMAL(18, 4) NOT NULL,
    price_per_share DECIMAL(18, 4) NOT NULL,
    total_value DECIMAL(18, 2) NOT NULL,
    
    -- AI recommendation at time of trade
    ai_buffett_score DECIMAL(5, 4),
    ai_recommendation VARCHAR(20),
    ai_kelly_position_size DECIMAL(5, 4),
    
    -- Trade execution
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Current status (for open positions)
    is_closed BOOLEAN DEFAULT FALSE,
    closed_at TIMESTAMP WITH TIME ZONE,
    close_price_per_share DECIMAL(18, 4),
    realized_pnl DECIMAL(18, 2),
    realized_pnl_percentage DECIMAL(5, 4),
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add alternative_data_score column to Assets (PRD 5.0)
ALTER TABLE public.assets 
ADD COLUMN IF NOT EXISTS alternative_data_score DECIMAL(5, 4) CHECK (alternative_data_score BETWEEN 0 AND 1);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_subscription ON public.users(subscription_tier, subscription_status);
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer ON public.users(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_user_id ON public.paper_trades(user_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_asset_id ON public.paper_trades(asset_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_user_open ON public.paper_trades(user_id, is_closed);
CREATE INDEX IF NOT EXISTS idx_assets_alternative_score ON public.assets(alternative_data_score);

-- Enable RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.paper_trades ENABLE ROW LEVEL SECURITY;

-- RLS Policies for Users
CREATE POLICY "Users: Can view own profile" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users: Can insert own profile" ON public.users
    FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "Users: Can update own profile" ON public.users
    FOR UPDATE USING (auth.uid() = id);

-- RLS Policies for PaperTrades
CREATE POLICY "PaperTrades: User can view own trades" ON public.paper_trades
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "PaperTrades: User can insert own trades" ON public.paper_trades
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "PaperTrades: User can update own trades" ON public.paper_trades
    FOR UPDATE USING (auth.uid() = user_id);

-- Update function to trigger updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_paper_trades_updated_at ON public.paper_trades;
CREATE TRIGGER update_paper_trades_updated_at
    BEFORE UPDATE ON public.paper_trades
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
