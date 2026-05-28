"""
Mineral AI Tracker - Hive Mind Global Pulse API (Phase 13.0 - Tokenomics)
Version: 13.0
Description: API endpoints for the Hive Mind Global Pulse feature
- GET /api/pulse/convictions: Top 5 high-conviction positive signals from last 24h
- GET /api/pulse/credits: User's credit balance
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger

from psycopg2.extras import RealDictCursor
from utils.database import get_db_connection, release_db_connection
from config import settings
from api.deps import get_current_user

# ---------------------------------------------------------------------------
# Mock fallback — seeded convictions shown when hive_signals is empty
# ---------------------------------------------------------------------------

_SIGNAL_LABELS: Dict[str, str] = {
    "dilution_risk":   "utspädningsrisk",
    "ma_radar":        "M&A-radar",
    "scrap_surge":     "scrap surge",
    "early_sentiment": "tidigt varningssignal",
    "chokepoint":      "flaskhals",
}

_MOCK_CONVICTIONS: List[Dict[str, Any]] = [
    {"ticker": "SCCO",  "signal_type": "dilution_risk",   "node_count": 8, "avg_confidence": 78.5},
    {"ticker": "FCX",   "signal_type": "ma_radar",        "node_count": 5, "avg_confidence": 71.2},
    {"ticker": "VALE",  "signal_type": "scrap_surge",     "node_count": 4, "avg_confidence": 65.0},
    {"ticker": "LTR",   "signal_type": "early_sentiment", "node_count": 3, "avg_confidence": 58.3},
    {"ticker": "AVN.V", "signal_type": "dilution_risk",   "node_count": 2, "avg_confidence": 55.0},
]

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
            release_db_connection(conn)
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
            release_db_connection(conn)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get credits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-convictions")
async def get_top_convictions(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Sprint 22 — Top 5 network convictions from hive_signals (last 24 h).

    Groups by (ticker, signal_type), counts contributing nodes, averages
    confidence scores, returns top 5 by node_count DESC.

    Falls back to seeded mock data when the hive_signals table is empty
    (fresh install / no contributions yet).

    Response shape:
      {
        "convictions": [
          {
            "ticker": "SCCO",
            "signal_type": "dilution_risk",
            "signal_label": "utspädningsrisk",
            "node_count": 8,
            "avg_confidence": 78.5,
            "last_seen": "2026-05-28T22:00:00Z"
          },
          ...
        ],
        "as_of": "...",
        "source": "db" | "mock"
      }
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    try:
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        ticker,
                        signal_type,
                        COUNT(*)                     AS node_count,
                        ROUND(AVG(confidence_score)::numeric, 1) AS avg_confidence,
                        MAX(contributed_at)          AS last_seen
                    FROM hive_signals
                    WHERE contributed_at >= %s
                    GROUP BY ticker, signal_type
                    ORDER BY node_count DESC, avg_confidence DESC
                    LIMIT 5
                    """,
                    (cutoff,),
                )
                rows = cur.fetchall()
        finally:
            release_db_connection(conn)

        if rows:
            convictions = [
                {
                    "ticker": row["ticker"],
                    "signal_type": row["signal_type"],
                    "signal_label": _SIGNAL_LABELS.get(row["signal_type"], row["signal_type"]),
                    "node_count": int(row["node_count"]),
                    "avg_confidence": float(row["avg_confidence"]),
                    "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None,
                }
                for row in rows
            ]
            return {
                "convictions": convictions,
                "as_of": datetime.now(timezone.utc).isoformat(),
                "source": "db",
            }

    except Exception as exc:
        logger.warning(f"/api/pulse/top-convictions DB error, using mock: {exc}")

    mock_convictions = [
        {
            **c,
            "signal_label": _SIGNAL_LABELS.get(c["signal_type"], c["signal_type"]),
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }
        for c in _MOCK_CONVICTIONS
    ]
    return {
        "convictions": mock_convictions,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": "mock",
    }
