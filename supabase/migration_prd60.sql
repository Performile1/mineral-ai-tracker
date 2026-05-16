-- ============================================================================
-- PRD v6.0 Migration - Key Personnel Radar & Scenario Engine
-- Description: Add KeyPersonnel tracking, ScenarioModels for stress testing, Battery Passport
-- ============================================================================

-- Add battery_passport_readiness to Assets (PRD 6.0)
ALTER TABLE public.assets 
ADD COLUMN IF NOT EXISTS battery_passport_readiness DECIMAL(5, 4) CHECK (battery_passport_readiness BETWEEN 0 AND 1);

-- Create KeyPersonnel table for tracking geologists and mining executives
CREATE TABLE IF NOT EXISTS public.key_personnel (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL,  -- e.g., "Chief Geologist", "Mining CEO", "Exploration Manager"
    company VARCHAR(255),
    linkedin_url VARCHAR(500),
    expertise VARCHAR(100),  -- e.g., "Lithium", "Copper", "Nickel"
    star_rating DECIMAL(3, 2) CHECK (star_rating BETWEEN 0 AND 5),  -- 0-5 star rating
    career_moves_count INTEGER DEFAULT 0,
    last_company_change DATE,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create PersonnelEvents table for tracking career moves
CREATE TABLE IF NOT EXISTS public.personnel_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID REFERENCES public.key_personnel(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('new_company', 'promotion', 'departure', 'board_join', 'award')),
    from_company VARCHAR(255),
    to_company VARCHAR(255),
    asset_id UUID REFERENCES public.assets(id) ON DELETE SET NULL,  -- If move involves a tracked asset
    event_date DATE,
    description TEXT,
    source_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create ScenarioModels table for Black Swan stress testing
CREATE TABLE IF NOT EXISTS public.scenario_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    scenario_type VARCHAR(50) NOT NULL CHECK (scenario_type IN ('commodity_shock', 'geopolitical', 'regulatory', 'supply_disruption')),
    
    -- Impact parameters
    affected_commodity VARCHAR(50),  -- e.g., "copper", "lithium"
    price_impact_percentage DECIMAL(10, 2),  -- e.g., -30 for 30% drop
    duration_days INTEGER,
    
    -- Historical correlation data
    historical_correlation DECIMAL(5, 4),
    similar_historical_event VARCHAR(255),
    similar_event_date DATE,
    
    -- Metadata
    is_template BOOLEAN DEFAULT TRUE,  -- True for predefined scenarios, False for user-created
    created_by_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create ScenarioResults table for storing stress test results
CREATE TABLE IF NOT EXISTS public.scenario_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    scenario_id UUID REFERENCES public.scenario_models(id) ON DELETE CASCADE,
    
    -- Portfolio snapshot before scenario
    portfolio_value_before DECIMAL(18, 2),
    portfolio_value_after DECIMAL(18, 2),
    portfolio_impact_percentage DECIMAL(10, 4),
    
    -- Detailed breakdown
    asset_id UUID REFERENCES public.assets(id) ON DELETE SET NULL,
    asset_impact_percentage DECIMAL(10, 4),
    asset_value_before DECIMAL(18, 2),
    asset_value_after DECIMAL(18, 2),
    
    -- Metadata
    simulated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_key_personnel_expertise ON public.key_personnel(expertise);
CREATE INDEX IF NOT EXISTS idx_key_personnel_company ON public.key_personnel(company);
CREATE INDEX IF NOT EXISTS idx_key_personnel_star_rating ON public.key_personnel(star_rating);
CREATE INDEX IF NOT EXISTS idx_personnel_events_personnel_id ON public.personnel_events(personnel_id);
CREATE INDEX IF NOT EXISTS idx_personnel_events_asset_id ON public.personnel_events(asset_id);
CREATE INDEX IF NOT EXISTS idx_personnel_events_date ON public.personnel_events(event_date);
CREATE INDEX IF NOT EXISTS idx_scenario_models_type ON public.scenario_models(scenario_type);
CREATE INDEX IF NOT EXISTS idx_scenario_models_commodity ON public.scenario_models(affected_commodity);
CREATE INDEX IF NOT EXISTS idx_scenario_results_user_id ON public.scenario_results(user_id);
CREATE INDEX IF NOT EXISTS idx_scenario_results_scenario_id ON public.scenario_results(scenario_id);
CREATE INDEX IF NOT EXISTS idx_assets_battery_passport ON public.assets(battery_passport_readiness);

-- Enable RLS
ALTER TABLE public.key_personnel ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.personnel_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scenario_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scenario_results ENABLE ROW LEVEL SECURITY;

-- RLS Policies for KeyPersonnel (public read for Pro users)
CREATE POLICY "KeyPersonnel: Public read for Pro" ON public.key_personnel
    FOR SELECT USING (true);  -- Public read for all (personnel data is public)

CREATE POLICY "KeyPersonnel: Insert for admin" ON public.key_personnel
    FOR INSERT WITH CHECK (true);  -- Admin/system can insert

CREATE POLICY "KeyPersonnel: Update for admin" ON public.key_personnel
    FOR UPDATE USING (true);  -- Admin/system can update

-- RLS Policies for PersonnelEvents
CREATE POLICY "PersonnelEvents: Public read" ON public.personnel_events
    FOR SELECT USING (true);

CREATE POLICY "PersonnelEvents: Insert for admin" ON public.personnel_events
    FOR INSERT WITH CHECK (true);

-- RLS Policies for ScenarioModels (Pro feature)
CREATE POLICY "ScenarioModels: Read for Pro" ON public.scenario_models
    FOR SELECT USING (true);  -- Public read for templates

CREATE POLICY "ScenarioModels: User can read own" ON public.scenario_models
    FOR SELECT USING (auth.uid() = created_by_user_id OR is_template = true);

CREATE POLICY "ScenarioModels: User can insert own" ON public.scenario_models
    FOR INSERT WITH CHECK (auth.uid() = created_by_user_id);

CREATE POLICY "ScenarioModels: User can update own" ON public.scenario_models
    FOR UPDATE USING (auth.uid() = created_by_user_id);

-- RLS Policies for ScenarioResults
CREATE POLICY "ScenarioResults: User can read own" ON public.scenario_results
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "ScenarioResults: User can insert own" ON public.scenario_results
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Update function to trigger updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers
DROP TRIGGER IF EXISTS update_key_personnel_updated_at ON public.key_personnel;
CREATE TRIGGER update_key_personnel_updated_at
    BEFORE UPDATE ON public.key_personnel
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_scenario_models_updated_at ON public.scenario_models;
CREATE TRIGGER update_scenario_models_updated_at
    BEFORE UPDATE ON public.scenario_models
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default scenario templates
INSERT INTO public.scenario_models (name, description, scenario_type, affected_commodity, price_impact_percentage, duration_days, historical_correlation, similar_historical_event, similar_event_date, is_template) VALUES
('China Graphite Export Ban', 'China blocks graphite export to EU/US, causing supply crisis', 'supply_disruption', 'graphite', -50.00, 180, 0.85, 'China rare earth export restrictions 2010', '2010-09-01', true),
('Copper Price Collapse', 'Global economic slowdown causes copper to drop 30%', 'commodity_shock', 'copper', -30.00, 90, 0.70, '2008 Financial Crisis', '2008-09-15', true),
('Lithium Glut', 'Oversupply causes lithium prices to crash', 'commodity_shock', 'lithium', -40.00, 365, 0.60, 'Lithium price crash 2018', '2018-05-01', true),
('EU CRMA Implementation', 'EU Critical Raw Materials Act imposes strict regulations', 'regulatory', 'multiple', 10.00, 365, 0.45, 'EU GDPR implementation', '2018-05-25', true),
('Mining Strike in Chile', 'Major copper mines in Chile go on strike', 'supply_disruption', 'copper', 25.00, 60, 0.55, 'Chile mining strike 2011', '2011-07-01', true)
ON CONFLICT DO NOTHING;
