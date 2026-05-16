-- ============================================================================
-- PRD v3.1 Migration - Discovery & Dynamic Assets
-- Description: Add new columns and tables for discovery functionality
-- ============================================================================

-- Add new columns to Assets table
ALTER TABLE public.assets 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'verified' CHECK (status IN ('verified', 'user_added', 'scouted'));

ALTER TABLE public.assets 
ADD COLUMN IF NOT EXISTS discovery_source TEXT;

-- Make ISIN unique (drop existing constraint if any)
ALTER TABLE public.assets 
DROP CONSTRAINT IF EXISTS assets_isin_key;

ALTER TABLE public.assets 
ADD CONSTRAINT assets_isin_key UNIQUE (isin);

-- Create AssetTags table
CREATE TABLE IF NOT EXISTS public.asset_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES public.assets(id) ON DELETE CASCADE,
    tag_name VARCHAR(50) NOT NULL,
    tag_category VARCHAR(30) CHECK (tag_category IN ('commodity', 'region', 'stage', 'technology', 'other')),
    auto_generated BOOLEAN DEFAULT TRUE,
    confidence DECIMAL(5, 4) CHECK (confidence BETWEEN 0 AND 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(asset_id, tag_name)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_asset_tags_asset_id ON public.asset_tags(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_tags_name ON public.asset_tags(tag_name);
CREATE INDEX IF NOT EXISTS idx_asset_tags_category ON public.asset_tags(tag_category);
CREATE INDEX IF NOT EXISTS idx_assets_status ON public.assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_isin ON public.assets(isin);
CREATE INDEX IF NOT EXISTS idx_assets_discovery_source ON public.assets(discovery_source);

-- Enable RLS on AssetTags
ALTER TABLE public.asset_tags ENABLE ROW LEVEL SECURITY;

-- Note: Skipping RLS policies for local PostgreSQL (auth schema doesn't exist)
-- For Supabase deployment, the policies will be applied automatically
