"""
Mineral AI Tracker - Hive Mind Aggregator (Sprint 22)
======================================================
POST /api/hive/contribute  — anonymous node conviction ingest
GET  /api/hive/consensus/{ticker} — per-ticker 48h consensus (legacy)

Rate-limit window: 65 seconds per anonymised node hash.
No PII is stored. Client IP is one-way hashed (sha256[:32]).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field

from utils.database import get_db_connection, release_db_connection

router = APIRouter(prefix="/api/hive", tags=["hive"])

# ---------------------------------------------------------------------------
# Rate-limit state (in-memory, 65-second window)
# ---------------------------------------------------------------------------

_RATE_WINDOW_SECONDS: int = 65
_last_contribution: Dict[str, datetime] = {}  # node_hash → last accepted UTC


def _node_hash(request: Request) -> str:
    ip = (request.client.host if request.client else "unknown").encode()
    return hashlib.sha256(ip).hexdigest()[:32]


def _rate_check(node_hash: str) -> tuple[bool, float]:
    """Return (allowed, retry_after_seconds)."""
    now = datetime.now(timezone.utc)
    last = _last_contribution.get(node_hash)
    if last is None:
        return True, 0.0
    elapsed = (now - last).total_seconds()
    if elapsed >= _RATE_WINDOW_SECONDS:
        return True, 0.0
    return False, round(_RATE_WINDOW_SECONDS - elapsed, 1)


# ---------------------------------------------------------------------------
# hive_signals DDL (no-migration approach — idempotent CREATE TABLE IF NOT EXISTS)
# ---------------------------------------------------------------------------

def ensure_hive_signals_table() -> None:
    """Create hive_signals table if it does not exist. Safe to call on every startup."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS hive_signals (
                    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                    ticker           VARCHAR(20) NOT NULL,
                    signal_type      VARCHAR(50) NOT NULL,
                    confidence_score FLOAT       NOT NULL
                                     CHECK (confidence_score BETWEEN 0.0 AND 100.0),
                    node_hash        VARCHAR(64) NOT NULL,
                    contributed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_hive_signals_contributed_at
                    ON hive_signals (contributed_at DESC);
                CREATE INDEX IF NOT EXISTS idx_hive_signals_ticker
                    ON hive_signals (ticker);
            """)
            conn.commit()
        logger.info("hive_signals table ready")
    except Exception as exc:
        conn.rollback()
        logger.warning(f"ensure_hive_signals_table: {exc}")
    finally:
        release_db_connection(conn)


# ---------------------------------------------------------------------------
# Pydantic model for inbound contribution
# ---------------------------------------------------------------------------

class ContributePayload(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    signal_type: str = Field(..., min_length=1, max_length=50)
    confidence_score: float = Field(..., ge=0.0, le=100.0)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/contribute", status_code=202)
async def contribute_signal(
    payload: ContributePayload,
    request: Request,
) -> Dict[str, Any]:
    """
    Sprint 22 — Anonymous node conviction ingest.

    Accepts a {ticker, signal_type, confidence_score} signal from any network
    node and writes it to hive_signals. No PII is stored; the client IP is
    one-way hashed before persistence.

    Rate-limited to one contribution per node per 65 seconds.
    """
    nhash = _node_hash(request)
    allowed, retry_after = _rate_check(nhash)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": f"Contribution window resets in {retry_after}s.",
                "retry_after_seconds": retry_after,
            },
        )

    ticker = payload.ticker.upper().strip()
    signal_type = payload.signal_type.lower().strip()
    score = round(payload.confidence_score, 2)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO hive_signals (ticker, signal_type, confidence_score, node_hash)
                VALUES (%s, %s, %s, %s)
                """,
                (ticker, signal_type, score, nhash),
            )
            conn.commit()

        _last_contribution[nhash] = datetime.now(timezone.utc)
        logger.info(
            f"Hive: contribution accepted — {ticker} / {signal_type} / "
            f"conf={score} from node {nhash[:8]}…"
        )
        return {
            "status": "accepted",
            "ticker": ticker,
            "signal_type": signal_type,
            "confidence_score": score,
            "rate_limit_window_seconds": _RATE_WINDOW_SECONDS,
        }
    except Exception as exc:
        conn.rollback()
        logger.error(f"Hive contribute DB error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to persist signal")
    finally:
        release_db_connection(conn)



def ensure_hive_columns():
    """Ensure is_public column exists"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE investment_signals 
                ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;
            """)
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to ensure hive columns: {e}")
    finally:
        release_db_connection(conn)


@router.get("/consensus/{ticker}")
async def get_hive_consensus(ticker: str):
    """
    Get Hive Mind consensus for a ticker (PRD v9.0 Phase 10.2)
    
    Aggregates public analyses from the last 48 hours to calculate:
    - total_signals: Number of public analyses
    - average_confidence: Average confidence score
    - majority_signal: BUY, SELL, or PASS
    """
    try:
        ensure_hive_columns()
        
        ticker = ticker.upper().strip()
        if not ticker:
            return {
                "ticker": ticker,
                "total_signals": 0,
                "average_confidence": 0,
                "majority_signal": "NO_DATA"
            }
        
        # Calculate 48 hour cutoff
        cutoff_time = datetime.now() - timedelta(hours=48)
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Query public signals for this ticker from last 48 hours
                cur.execute("""
                    SELECT 
                        signal_type,
                        confidence_score
                    FROM investment_signals
                    WHERE ticker = %s
                      AND is_public = TRUE
                      AND created_at >= %s
                """, (ticker, cutoff_time))
                
                rows = cur.fetchall()
                
                if not rows:
                    return {
                        "ticker": ticker,
                        "total_signals": 0,
                        "average_confidence": 0,
                        "majority_signal": "NO_DATA"
                    }
                
                # Calculate metrics
                total_signals = len(rows)
                total_confidence = sum(row["confidence_score"] or 0 for row in rows)
                average_confidence = total_confidence / total_signals if total_signals > 0 else 0
                
                # Count signal types
                signal_counts = {"BUY": 0, "SELL": 0, "PASS": 0}
                for row in rows:
                    signal_type = row["signal_type"]
                    if signal_type in signal_counts:
                        signal_counts[signal_type] += 1
                
                # Determine majority signal
                majority_signal = max(signal_counts, key=signal_counts.get)
                
                logger.info(f"Hive consensus for {ticker}: {total_signals} signals, "
                           f"avg_conf={average_confidence:.1f}, majority={majority_signal}")
                
                return {
                    "ticker": ticker,
                    "total_signals": total_signals,
                    "average_confidence": round(average_confidence, 1),
                    "majority_signal": majority_signal,
                    "signal_breakdown": signal_counts,
                    "timeframe_hours": 48
                }
        finally:
            release_db_connection(conn)
    except Exception as e:
        logger.error(f"Failed to get hive consensus for {ticker}: {e}")
        # Return degraded state instead of crashing
        return {
            "ticker": ticker,
            "total_signals": 0,
            "average_confidence": 0,
            "majority_signal": "ERROR",
            "error": str(e)
        }


__all__ = ["router"]
