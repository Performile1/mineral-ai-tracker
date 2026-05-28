"""
Mineral AI Tracker - Macro Pulse Aggregator (PRD v8.6 Phase 8)
Version: 8.6
Description: GET /api/macro/pulse - aggregates DXY, US10Y, and the top 3
             commodity supply deficits for the GlobalPulse top row.
             Reads from `macro_indicators` table when available; otherwise
             falls back to a sane default snapshot.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone, date

from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Depends
from loguru import logger

from config import settings
from api.deps import get_current_user
from utils.database import get_db_connection, release_db_connection

# ---------------------------------------------------------------------------
# Secondary Supply helpers
# ---------------------------------------------------------------------------

COPPER_SCRAP_SPREAD_FLOOR: float = 0.10  # $/lb — smelter profitability cliff


def _seed_mock_spread_series() -> List[Dict[str, Any]]:
    """
    Generate a 30-day synthetic trend when the DB has no historical data.
    Copper Scrap: healthy spread ($0.35/lb) deteriorating to a squeeze ($0.08).
    Black Mass Index: wide spread, stable (EV recycling still expensive).
    """
    today = date.today()
    rows: List[Dict[str, Any]] = []
    for i in range(30):
        day = today - timedelta(days=29 - i)
        # Copper Scrap: linear decay from 0.35 → 0.08 over 30 days
        copper_spread = round(0.35 - (0.27 / 29) * i, 4)
        rows.append({
            "date": day.isoformat(),
            "material_name": "Copper Scrap",
            "price_spread_usd": copper_spread,
            "is_critical_squeeze": copper_spread < COPPER_SCRAP_SPREAD_FLOOR,
        })
        # Black Mass: mild random walk around $5.40, no squeeze
        bm_spread = round(5.60 - (0.20 / 29) * i, 4)
        rows.append({
            "date": day.isoformat(),
            "material_name": "Black Mass Index",
            "price_spread_usd": bm_spread,
            "is_critical_squeeze": False,
        })
    return rows

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
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
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
            release_db_connection(conn)
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


@router.get("/secondary-supply")
async def get_secondary_supply(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Sprint 21 — Secondary Supply Pressure time series.

    Returns up to 30 days of spread data per material.
    Falls back to a seeded 30-day synthetic trend when the DB table is empty
    (fresh install / scheduler not yet run), so the chart is always useful.

    Response shape:
      {
        "items": [
          {
            "date": "2026-05-28",
            "material_name": "Copper Scrap",
            "price_spread_usd": 0.12,
            "is_critical_squeeze": false
          },
          ...
        ],
        "spread_floor_usd": 0.10,
        "source": "db" | "mock"
      }
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).date()

    try:
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        DATE(updated_at)              AS date,
                        material_name,
                        primary_secondary_spread      AS price_spread_usd
                    FROM secondary_supply
                    WHERE updated_at >= %s
                    ORDER BY updated_at ASC
                    """,
                    (cutoff,),
                )
                db_rows = cur.fetchall()
        finally:
            release_db_connection(conn)

        if db_rows:
            items = [
                {
                    "date": str(row["date"]),
                    "material_name": row["material_name"],
                    "price_spread_usd": float(row["price_spread_usd"]) if row["price_spread_usd"] is not None else None,
                    "is_critical_squeeze": (
                        row["material_name"] == "Copper Scrap"
                        and row["price_spread_usd"] is not None
                        and float(row["price_spread_usd"]) < COPPER_SCRAP_SPREAD_FLOOR
                    ),
                }
                for row in db_rows
            ]
            return {"items": items, "spread_floor_usd": COPPER_SCRAP_SPREAD_FLOOR, "source": "db"}

    except Exception as exc:
        logger.warning(f"/api/macro/secondary-supply DB error, using mock: {exc}")

    return {
        "items": _seed_mock_spread_series(),
        "spread_floor_usd": COPPER_SCRAP_SPREAD_FLOOR,
        "source": "mock",
    }
