-- Migration: Add Users Table (Phase 10.1 - NextAuth & RLS)
-- Purpose: Create users table for NextAuth integration and multi-user support
-- Date: 2026-05-15

-- Create users table for NextAuth integration
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    image TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Add comments
COMMENT ON TABLE users IS 'User accounts for NextAuth authentication';
COMMENT ON COLUMN users.id IS 'Unique user identifier (UUID)';
COMMENT ON COLUMN users.email IS 'User email (unique)';
COMMENT ON COLUMN users.name IS 'User display name';
COMMENT ON COLUMN users.image IS 'User profile image URL';
