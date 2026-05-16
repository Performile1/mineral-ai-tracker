-- ============================================================================
-- Mineral AI Tracker - PRD v8.7 Phase 9 Migration
-- Adds encrypted API key storage to system_settings for the vault.
-- Safe to re-run (IF NOT EXISTS).
-- ============================================================================

-- Add vault column for FMP API key (encrypted at rest)
ALTER TABLE system_settings
ADD COLUMN IF NOT EXISTS fmp_api_key TEXT;

-- Optional: Add a comment to indicate this field is encrypted
COMMENT ON COLUMN system_settings.fmp_api_key IS 'Encrypted FMP API key (AES-256-GCM). Store via /api/settings/vault endpoint.';
