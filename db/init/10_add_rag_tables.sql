-- Migration: Add RAG Engine Tables (Phase 12 - The Alpha & Economics Sprint)
-- Purpose: Add document_embeddings table for historical earnings call analysis
-- Date: 2026-05-15

-- Create document_embeddings table for RAG engine
CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    document_type VARCHAR(50) NOT NULL, -- 'earnings_call', 'sec_filing', 'press_release'
    title VARCHAR(500),
    content TEXT NOT NULL,
    embedding vector(1536), -- OpenAI embedding dimension, adjust based on model used
    chunk_index INT NOT NULL, -- For large documents split into chunks
    total_chunks INT NOT NULL DEFAULT 1,
    source_url VARCHAR(500),
    published_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for RAG queries
CREATE INDEX IF NOT EXISTS idx_document_embeddings_ticker ON document_embeddings(ticker);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_type ON document_embeddings(document_type);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_published_date ON document_embeddings(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector ON document_embeddings USING ivfflat (embedding vector_cosine_ops);

-- Add comments
COMMENT ON TABLE document_embeddings IS 'Historical documents (earnings calls, SEC filings) with embeddings for RAG engine';
COMMENT ON COLUMN document_embeddings.embedding IS 'Vector embedding for semantic search (using pgvector)';
COMMENT ON COLUMN document_embeddings.chunk_index IS 'Chunk index for large documents split into parts';
