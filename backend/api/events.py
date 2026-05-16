"""
Mineral AI Tracker - Events API (Phase 12.1 - Event Correlation Engine)
Description: API endpoints for asset events correlated with price movements
Critical Hotfix: Added authentication dependency to enforce JWT validation
"""

import os
from typing import Optional, List
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from loguru import logger

from utils.database import get_db_connection
from api.deps import get_current_user

router = APIRouter(prefix="/api/events", tags=["events"])


# ============================================================================
# Pydantic Models
# ============================================================================

class AssetEvent(BaseModel):
    id: str
    ticker: str
    published_at: str
    title: str
    url: Optional[str]
    source_authority_score: float
    ai_summary: Optional[str]
    price_impact_4h: Optional[float]
    created_at: str


class EventListResponse(BaseModel):
    ticker: str
    events: List[AssetEvent]
    total: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/{ticker}", response_model=EventListResponse)
async def get_events(
    ticker: str,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    min_authority: Optional[float] = Query(None, description="Minimum authority score (0.1-1.0)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of events to return"),
    current_user: dict = Depends(get_current_user)  # Phase 12.1 spec 4.1: Require authentication
):
    """
    Get historical asset events for a ticker.
    
    Args:
        ticker: Asset ticker symbol
        start_date: Optional start date filter (ISO format)
        end_date: Optional end date filter (ISO format)
        min_authority: Optional minimum authority score filter
        limit: Maximum number of events to return (default: 100, max: 500)
        
    Returns:
        List of asset events with their metadata
    """
    try:
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query with optional filters
                query = """
                    SELECT id, ticker, published_at, title, url, 
                           source_authority_score, ai_summary, price_impact_4h, created_at
                    FROM asset_events
                    WHERE ticker = %s
                """
                params = [ticker.upper()]
                
                if start_date:
                    query += " AND published_at >= %s"
                    params.append(start_date)
                
                if end_date:
                    query += " AND published_at <= %s"
                    params.append(end_date)
                
                if min_authority:
                    query += " AND source_authority_score >= %s"
                    params.append(min_authority)
                
                query += " ORDER BY published_at DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                events = [AssetEvent(**row) for row in rows]
                
                # Get total count
                count_query = "SELECT COUNT(*) FROM asset_events WHERE ticker = %s"
                cur.execute(count_query, [ticker.upper()])
                total = cur.fetchone()["count"]
                
                return EventListResponse(
                    ticker=ticker.upper(),
                    events=events,
                    total=total
                )
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to fetch events for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticker}", status_code=201)
async def create_event(
    ticker: str,
    title: str,
    url: Optional[str] = None,
    source_type: str = Field(..., description="Type of source (e.g., 'financial_report', 'press_release', 'news_article')"),
    source_name: Optional[str] = Field(None, description="Name of the source"),
    published_at: str = Field(..., description="Publication timestamp (ISO format)"),
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Create a new asset event.
    
    This endpoint is typically called by the Celery worker after fetching news.
    The authority score is calculated using the Source Authority Matrix.
    
    Args:
        ticker: Asset ticker symbol
        title: Event title
        url: Optional URL to the event source
        source_type: Type of source for authority calculation
        source_name: Optional source name for authority calculation
        published_at: Publication timestamp (ISO format)
        
    Returns:
        Created event ID
    """
    try:
        from utils.authority_matrix import get_authority_score
        
        # Calculate authority score
        authority_score = get_authority_score(source_type, source_name)
        
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO asset_events 
                    (ticker, published_at, title, url, source_authority_score)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (ticker, published_at, url) DO NOTHING
                    RETURNING id
                    """,
                    (ticker.upper(), published_at, title, url, authority_score)
                )
                row = cur.fetchone()
                conn.commit()
                
                if not row:
                    raise HTTPException(status_code=409, detail="Event already exists")
                
                logger.info(f"Created event {row['id']} for {ticker} with authority {authority_score}")
                
                return {"id": str(row["id"]), "authority_score": authority_score}
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        raise HTTPException(status_code=500, detail=str(e))
