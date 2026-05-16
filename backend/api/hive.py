"""
Mineral AI Tracker - Hive Mind Aggregator (PRD v9.0 Phase 10.2)
Version: 9.0
Description: Swarm intelligence aggregator for The Hive Mind
"""

from typing import Dict, Any
from fastapi import APIRouter
from loguru import logger
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/api/hive", tags=["hive"])


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="mineral_ai_tracker",
        user="mineral_user",
        password="mineralpass123",
        cursor_factory=RealDictCursor
    )


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
        conn.close()


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
            conn.close()
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
