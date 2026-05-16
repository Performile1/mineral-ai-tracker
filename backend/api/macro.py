"""
Mineral AI Tracker - Macro Pulse Aggregator (PRD v8.6 Phase 8)
Version: 8.6
Description: GET /api/macro/pulse - aggregates DXY, US10Y, and the top 3
             commodity supply deficits for the GlobalPulse top row.
             Reads from `macro_indicators` table when available; otherwise
             falls back to a sane default snapshot.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Depends
from loguru import logger

from config import settings
from api.deps import get_current_user

router = APIRouter(prefix="/api/macro", tags=["macro"])


# Indicators we surface in the GlobalPulse strip (key, label, unit, hint)
PULSE_KEYS = [
    ("dxy",      "DXY",       "",     "USD index"),
    ("us10y",    "US 10Y",    "%",    "10-yr treasury yield"),
    ("copper_deficit",   "Cu Deficit", "%", "Supply balance"),
    ("lithium_deficit",  "Li Deficit", "%", "Supply balance"),
    ("uranium_deficit",  "U Deficit",  "%", "Supply balance"),
]

# Fallback snapshot when DB is empty (boot day) - tuned to current consensus
FALLBACK_VALUES: Dict[str, Dict[str, Any]] = {
    "dxy":              {"value": 103.4, "delta_pct": -0.2},
    "us10y":            {"value": 4.32,  "delta_pct": 0.4},
    "copper_deficit":   {"value": -8,    "delta_pct": 1.1},
    "lithium_deficit":  {"value": -12,   "delta_pct": 0.6},
    "uranium_deficit":  {"value": -22,   "delta_pct": 0.9},
}


def _get_db_connection():
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        cursor_factory=RealDictCursor,
    )


def _latest_two_values(cur, indicator_key: str) -> Optional[Dict[str, float]]:
    """Return the latest value and a delta_pct vs the prior reading."""
    cur.execute(
        """
        SELECT value, captured_at FROM macro_indicators
        WHERE indicator_key = %s
        ORDER BY captured_at DESC
        LIMIT 2
        """,
        (indicator_key,),
    )
    rows = cur.fetchall()
    if not rows:
        return None
    latest = float(rows[0]["value"])
    prev = float(rows[1]["value"]) if len(rows) > 1 else None
    delta = None
    if prev is not None and prev != 0:
        delta = (latest - prev) / abs(prev) * 100.0
    return {"value": latest, "delta_pct": delta}


@router.get("/pulse")
async def get_pulse(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Returns the Global Pulse snapshot consumed by the dashboard top row.

    Response shape:
      {
        "metrics": [
          {"key": "dxy", "label": "DXY", "value": 103.4, "delta_pct": -0.2, "hint": "..."},
          ...
        ],
        "as_of": "2026-05-13T20:00:00Z",
        "source": "db" | "fallback"
      }
    """
    logger.info(f"User {current_user.get('id')} requesting macro pulse")
    metrics: List[Dict[str, Any]] = []
    using_fallback = True

    try:
        conn = _get_db_connection()
        try:
            with conn.cursor() as cur:
                for key, label, unit, hint in PULSE_KEYS:
                    snap = _latest_two_values(cur, key)
                    if snap is None:
                        fb = FALLBACK_VALUES[key]
                        metrics.append({
                            "key": key, "label": label, "unit": unit, "hint": hint,
                            "value": fb["value"], "delta_pct": fb["delta_pct"],
                        })
                    else:
                        using_fallback = False
                        metrics.append({
                            "key": key, "label": label, "unit": unit, "hint": hint,
                            "value": snap["value"], "delta_pct": snap["delta_pct"],
                        })
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"/api/macro/pulse fallback (DB unavailable): {e}")
        for key, label, unit, hint in PULSE_KEYS:
            fb = FALLBACK_VALUES[key]
            metrics.append({
                "key": key, "label": label, "unit": unit, "hint": hint,
                "value": fb["value"], "delta_pct": fb["delta_pct"],
            })

    return {
        "metrics": metrics,
        "as_of": datetime.utcnow().isoformat() + "Z",
        "source": "fallback" if using_fallback else "db",
    }
