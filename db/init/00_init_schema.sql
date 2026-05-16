-- ============================================================================
-- Mineral AI Tracker - PRD v8.3 Core Schema
-- Loaded automatically by ankane/pgvector on first boot via
-- docker-entrypoint-initdb.d. Re-runs are no-ops (IF NOT EXISTS).
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------------------------------------------------------
-- system_settings (Pydantic Firewall thresholds)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    max_pe_ratio              FLOAT NOT NULL DEFAULT 25.0,
    min_market_cap_m          FLOAT NOT NULL DEFAULT 10.0,
    min_daily_volume_k        FLOAT NOT NULL DEFAULT 500.0,
    min_confidence_score      INTEGER NOT NULL DEFAULT 85,
    max_geological_grade_copper FLOAT NOT NULL DEFAULT 15.0,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

INSERT INTO system_settings (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- investment_signals (Multi-SLM Debate output + pgvector embedding)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS investment_signals (
    id SERIAL PRIMARY KEY,
    asset_id            VARCHAR(100),
    signal_type         VARCHAR(20),
    confidence_score    INTEGER,
    recommendation      TEXT,
    consensus_score     FLOAT,
    pydantic_passed     BOOLEAN,
    debate_log          JSONB,
    embedding           vector(768),
    source              VARCHAR(200),
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_created_at
    ON investment_signals (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_signal_type
    ON investment_signals (signal_type);
-- Approximate nearest neighbor index for RAG lookups
CREATE INDEX IF NOT EXISTS idx_signals_embedding
    ON investment_signals USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ----------------------------------------------------------------------------
-- trade_journal (RLHF feedback + Kelly sizing log)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trade_journal (
    id SERIAL PRIMARY KEY,
    user_id             VARCHAR(100),
    asset_id            VARCHAR(100),
    asset_ticker        VARCHAR(20),
    signal_type         VARCHAR(20),
    entry_price         FLOAT,
    exit_price          FLOAT,
    quantity            FLOAT,
    kelly_fraction      FLOAT,
    realized_pnl_pct    FLOAT,
    ai_confidence       INTEGER,
    user_feedback       VARCHAR(20),   -- agree / disagree / neutral
    feedback_notes      TEXT,
    opened_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    closed_at           TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_journal_user_id
    ON trade_journal (user_id);
CREATE INDEX IF NOT EXISTS idx_journal_asset_id
    ON trade_journal (asset_id);
CREATE INDEX IF NOT EXISTS idx_journal_created_at
    ON trade_journal (created_at DESC);

-- ----------------------------------------------------------------------------
-- macro_indicators (DXY, 10y rates, supply deficits - feeds GlobalPulse)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS macro_indicators (
    id SERIAL PRIMARY KEY,
    indicator_key   VARCHAR(50) NOT NULL,
    value           FLOAT NOT NULL,
    unit            VARCHAR(20),
    source          VARCHAR(100),
    captured_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_macro_key_time
    ON macro_indicators (indicator_key, captured_at DESC);
