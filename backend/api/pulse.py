"""
Mineral AI Tracker - Hive Mind Global Pulse API (Phase 13.0 - Tokenomics)
Version: 13.0
Description: API endpoints for the Hive Mind Global Pulse feature
- GET /api/pulse/convictions: Top 5 high-conviction positive signals from last 24h
- GET /api/pulse/credits: User's credit balance
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger

import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings
from api.deps import get_current_user

router = APIRouter(prefix="/api/pulse", tags=["pulse"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ConvictionSignal(BaseModel):
    """Single conviction signal in the ranking"""
    id: str
    asset_id: str
    ticker: str
    signal_type: str
    confidence_score: int
    recommendation: str
    consensus_score: float
    created_at: str


class ConvictionsResponse(BaseModel):
    """Response model for convictions endpoint"""
    signals: List[ConvictionSignal]
    count: int
    as_of: str


class CreditsResponse(BaseModel):
    """Response model for credits endpoint"""
    credits_remaining: int
    credits_used: int
    as_of: str


# ============================================================================
# Database Helper Functions
# ============================================================================

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        cursor_factory=RealDictCursor
    )


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/convictions", response_model=ConvictionsResponse)
async def get_convictions(
    current_user: dict = Depends(get_current_user)
):
    """
    Get Top 5 high-conviction positive signals from the Hive Mind (last 24h)
    
    Filters for signals where majority_signal IN ('BUY', 'STRONG BUY')
    Ranks by confidence_score DESCENDING
    Only includes signals marked as is_public = TRUE
    """
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Query for top 5 high-conviction BUY signals from last 24h
                cur.execute("""
                    SELECT 
                        id,
                        asset_id,
                        signal_type,
                        confidence_score,
                        recommendation,
                        consensus_score,
                        created_at
                    FROM investment_signals
                    WHERE is_public = TRUE
                      AND created_at >= NOW() - INTERVAL '24 hours'
                      AND (recommendation IN ('BUY', 'STRONG BUY') OR signal_type = 'LONG')
                    ORDER BY confidence_score DESC
                    LIMIT 5
                """)
                rows = cur.fetchall()
                
                signals = []
                for row in rows:
                    # Extract ticker from asset_id (e.g., "sig_123" -> needs lookup, or asset_id might be ticker)
                    ticker = row.get('asset_id', 'UNKNOWN')
                    # If asset_id looks like a ticker (no "sig_" prefix), use it directly
                    if not ticker.startswith('sig_'):
                        ticker = ticker.upper()
                    else:
                        # Fallback for legacy data
                        ticker = 'UNKNOWN'
                    
                    signals.append(ConvictionSignal(
                        id=str(row['id']),
                        asset_id=row['asset_id'],
                        ticker=ticker,
                        signal_type=row['signal_type'],
                        confidence_score=row['confidence_score'],
                        recommendation=row['recommendation'],
                        consensus_score=row['consensus_score'],
                        created_at=row['created_at'].isoformat() if row.get('created_at') else None
                    ))
                
                return ConvictionsResponse(
                    signals=signals,
                    count=len(signals),
                    as_of=datetime.utcnow().isoformat()
                )
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to get convictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credits", response_model=CreditsResponse)
async def get_credits(
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's credit balance
    
    Returns the user's remaining credits and total credits used.
    """
    try:
        user_id = current_user["id"]
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT credits_remaining, credits_used
                    FROM users
                    WHERE id = %s
                """, (user_id,))
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")
                
                return CreditsResponse(
                    credits_remaining=row.get('credits_remaining', 0),
                    credits_used=row.get('credits_used', 0),
                    as_of=datetime.utcnow().isoformat()
                )
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get credits: {e}")
        raise HTTPException(status_code=500, detail=str(e))
