"""
Mineral AI Tracker - RAG Engine (Phase 12 - The Alpha & Economics Sprint)
Version: 12.0
Description: Retrieval-Augmented Generation engine for historical earnings call analysis
Purpose: Enable Llama-3 to remember what executives promised in previous earnings calls
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from loguru import logger

from config import settings
from ml.ollama_client import OllamaClient


class RAGEngine:
    """
    RAG (Retrieval-Augmented Generation) engine for historical document analysis.
    
    Uses pgvector to search for relevant historical statements from earnings calls,
    SEC filings, and press releases. The retrieved context is injected into Llama-3
    prompts to enable comparison of current statements with historical promises.
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client or OllamaClient()
        self.embedding_model = os.getenv("RAG_EMBEDDING_MODEL", "nomic-embed-text")
        self.top_k = int(os.getenv("RAG_TOP_K", "3"))  # Number of relevant chunks to retrieve
        self.similarity_threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.7"))
        
    def get_db_connection(self):
        """Get database connection for RAG queries"""
        return psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            dbname=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            cursor_factory=RealDictCursor,
        )
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using Ollama.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            Embedding vector or None if generation fails
        """
        try:
            embedding = await self.ollama.generate_embedding(
                text=text,
                model=self.embedding_model
            )
            if not embedding:
                logger.warning("Empty embedding returned by Ollama")
                return None
            return embedding
        except Exception as e:
            logger.warning(f"generate_embedding failed: {e}")
            return None
    
    async def get_historical_context(
        self,
        ticker: str,
        query: str,
        document_type: Optional[str] = None,
        days_back: int = 365,
        top_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant historical context for a ticker based on a query.
        
        Args:
            ticker: Stock ticker symbol (e.g., "SIVERS.ST")
            query: Natural language query (e.g., "production targets for next year")
            document_type: Filter by document type (earnings_call, sec_filing, press_release)
            days_back: How many days back to search (default: 365)
            top_k: Number of results to return (default: from RAG_TOP_K env var)
            
        Returns:
            Dictionary with retrieved context chunks and metadata
        """
        try:
            # Generate embedding for query
            query_embedding = await self.generate_embedding(query)
            if not query_embedding:
                logger.warning(f"Failed to generate embedding for query: {query}")
                return {"chunks": [], "total": 0, "error": "embedding_generation_failed"}
            
            top_k = top_k or self.top_k
            conn = self.get_db_connection()
            try:
                with conn.cursor() as cur:
                    # Build query with pgvector cosine similarity
                    where_clauses = ["ticker = %s"]
                    params = [ticker]
                    
                    if document_type:
                        where_clauses.append("document_type = %s")
                        params.append(document_type)
                    
                    if days_back:
                        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
                        where_clauses.append("published_date >= %s")
                        params.append(cutoff_date)
                    
                    where_sql = " AND ".join(where_clauses)
                    
                    # Use pgvector cosine similarity search
                    sql = f"""
                        SELECT 
                            id,
                            ticker,
                            document_type,
                            title,
                            content,
                            chunk_index,
                            total_chunks,
                            source_url,
                            published_date,
                            1 - (embedding <=> %s::vector) as similarity
                        FROM document_embeddings
                        WHERE {where_sql}
                        ORDER BY embedding <=> %s::vector ASC
                        LIMIT %s
                    """
                    
                    params.extend([query_embedding, query_embedding, top_k])
                    cur.execute(sql, params)
                    results = cur.fetchall()
                    
                    # Filter by similarity threshold
                    filtered_results = [
                        r for r in results 
                        if r["similarity"] >= self.similarity_threshold
                    ]
                    
                    chunks = []
                    for row in filtered_results:
                        chunks.append({
                            "id": str(row["id"]),
                            "ticker": row["ticker"],
                            "document_type": row["document_type"],
                            "title": row["title"],
                            "content": row["content"],
                            "chunk_index": row["chunk_index"],
                            "total_chunks": row["total_chunks"],
                            "source_url": row["source_url"],
                            "published_date": row["published_date"].isoformat() if row["published_date"] else None,
                            "similarity": row["similarity"]
                        })
                    
                    return {
                        "chunks": chunks,
                        "total": len(chunks),
                        "query": query,
                        "ticker": ticker,
                        "embedding_model": self.embedding_model
                    }
                    
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"get_historical_context failed: {e}")
            return {
                "chunks": [],
                "total": 0,
                "error": str(e)
            }
    
    async def store_document(
        self,
        ticker: str,
        content: str,
        document_type: str,
        title: Optional[str] = None,
        source_url: Optional[str] = None,
        published_date: Optional[datetime] = None,
        chunk_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Store a document with embeddings for RAG retrieval.
        
        Args:
            ticker: Stock ticker symbol
            content: Document text content
            document_type: Type of document (earnings_call, sec_filing, press_release)
            title: Document title
            source_url: URL where document was retrieved
            published_date: When document was published
            chunk_size: Maximum characters per chunk (for large documents)
            
        Returns:
            Dictionary with storage results
        """
        try:
            # Split content into chunks if too large
            chunks = self._chunk_text(content, chunk_size)
            total_chunks = len(chunks)
            
            stored_count = 0
            failed_count = 0
            
            for i, chunk in enumerate(chunks):
                # Generate embedding for chunk
                embedding = await self.generate_embedding(chunk)
                if not embedding:
                    logger.warning(f"Failed to generate embedding for chunk {i}")
                    failed_count += 1
                    continue
                
                # Store chunk with embedding
                conn = self.get_db_connection()
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO document_embeddings
                            (ticker, document_type, title, content, embedding, 
                             chunk_index, total_chunks, source_url, published_date)
                            VALUES (%s, %s, %s, %s, %s::vector, %s, %s, %s, %s)
                        """, (
                            ticker,
                            document_type,
                            title,
                            chunk,
                            embedding,
                            i,
                            total_chunks,
                            source_url,
                            published_date
                        ))
                        conn.commit()
                        stored_count += 1
                except Exception as e:
                    logger.error(f"Failed to store chunk {i}: {e}")
                    conn.rollback()
                    failed_count += 1
                finally:
                    conn.close()
            
            return {
                "ticker": ticker,
                "total_chunks": total_chunks,
                "stored": stored_count,
                "failed": failed_count,
                "document_type": document_type
            }
            
        except Exception as e:
            logger.error(f"store_document failed: {e}")
            return {
                "error": str(e),
                "stored": 0
            }
    
    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """
        Split text into chunks for embedding generation.
        
        Args:
            text: Text to split
            chunk_size: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i + chunk_size])
        return chunks
    
    async def get_production_targets_context(self, ticker: str) -> Dict[str, Any]:
        """
        Convenience method to get historical production targets context.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with relevant production targets context
        """
        queries = [
            "production targets for next year",
            "production goals",
            "output targets",
            "capacity expansion plans",
            "mining production forecast"
        ]
        
        all_chunks = []
        for query in queries:
            result = await self.get_historical_context(ticker, query)
            all_chunks.extend(result.get("chunks", []))
        
        # Deduplicate by ID
        seen_ids = set()
        unique_chunks = []
        for chunk in all_chunks:
            if chunk["id"] not in seen_ids:
                seen_ids.add(chunk["id"])
                unique_chunks.append(chunk)
        
        # Sort by similarity and take top 3
        unique_chunks.sort(key=lambda x: x["similarity"], reverse=True)
        top_chunks = unique_chunks[:self.top_k]
        
        return {
            "chunks": top_chunks,
            "total": len(top_chunks),
            "query_type": "production_targets",
            "ticker": ticker
        }
