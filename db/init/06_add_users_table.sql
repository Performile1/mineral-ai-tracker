-- Mineral AI Tracker - Users Table (PRD v10.0 Phase 10.1)
-- Version: 10.0
-- Description: Add users table for NextAuth integration

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    image TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for email lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Comment
COMMENT ON TABLE users IS 'User accounts for NextAuth authentication';
