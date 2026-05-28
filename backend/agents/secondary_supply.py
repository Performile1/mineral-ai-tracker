"""
Mineral AI Tracker — Secondary Supply Engine (Sprint 16)
=========================================================
Monitors the spread between primary and recycled/scrap commodity prices.
Triggers a 'scrap_surge' alert when the Copper Scrap spread collapses,
signalling that scrap is flooding the market and threatening Junior Miners.

Domain focus (2026):
  - Copper Scrap   : LME Grade A (primary) vs #1 Bare Bright Copper (scrap)
                     Spread floor: $0.10/lb  → below = ALERT
  - Black Mass Index: recovered Li/Ni/Co from EV batteries
                     Monitored for context; no automatic alert (spread is healthy)

Provider pattern (mirrors quant_watchdog.py):
  USE_MOCK_DATA=true  → MockSecondarySupplyProvider
  USE_MOCK_DATA=false → LiveSecondarySupplyProvider (reads secondary_supply table)
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from loguru import logger
from psycopg2.extras import RealDictCursor

from config import settings
from utils.database import get_db_connection, release_db_connection

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

COPPER_SCRAP_SPREAD_FLOOR: float = 0.10  # $/lb — overrideable via settings if needed


# ---------------------------------------------------------------------------
# Provider pattern
# ---------------------------------------------------------------------------

class BaseSecondarySupplyProvider(ABC):
    @abstractmethod
    async def get_spreads(self) -> List[Dict[str, Any]]:
        """Return current spread rows for monitored materials."""


class MockSecondarySupplyProvider(BaseSecondarySupplyProvider):
    """
    Domain-seeded 2026 mock data.

    Copper Scrap spread is set BELOW the $0.10/lb floor to trigger the
    scrap_surge alert (realistic scenario: LME correction + scrap oversupply).
    Black Mass spread is healthy (EV recycling still expensive vs primary).
    """

    async def get_spreads(self) -> List[Dict[str, Any]]:
        return [
            {
                "material_name": "Copper Scrap",
                "scrap_price_usd": 3.82,          # $/lb — #1 Bare Bright Copper
                "primary_price_usd": 3.90,         # $/lb — LME Grade A
                "primary_secondary_spread": 0.08,  # BELOW floor → triggers alert
                "spread_pct": 2.05,
                "buy_signal": True,
                "recycler_tickers": ["SCCO", "FCX", "TECK"],
            },
            {
                "material_name": "Black Mass Index",
                "scrap_price_usd": 4.20,           # $/kg blended (Li/Ni/Co eq.)
                "primary_price_usd": 9.80,          # $/kg — combined carbonate eq.
                "primary_secondary_spread": 5.60,  # Healthy — no alert
                "spread_pct": 57.1,
                "buy_signal": False,
                "recycler_tickers": ["LI.UN", "NOVONIX", "LICY"],
            },
        ]


class LiveSecondarySupplyProvider(BaseSecondarySupplyProvider):
    """Reads the latest row per material from the secondary_supply table."""

    async def get_spreads(self) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT DISTINCT ON (material_name)
                        material_name, scrap_price_usd, primary_price_usd,
                        primary_secondary_spread, spread_pct, buy_signal,
                        recycler_tickers
                    FROM secondary_supply
                    ORDER BY material_name, updated_at DESC
                """)
                rows = []
                for row in cur.fetchall():
                    r = dict(row)
                    # recycler_tickers stored as JSONB — may arrive as list or str
                    if isinstance(r.get("recycler_tickers"), str):
                        try:
                            r["recycler_tickers"] = json.loads(r["recycler_tickers"])
                        except (ValueError, TypeError):
                            r["recycler_tickers"] = []
                    rows.append(r)
                return rows
        finally:
            release_db_connection(conn)


def get_secondary_supply_provider() -> BaseSecondarySupplyProvider:
    if settings.USE_MOCK_DATA:
        return MockSecondarySupplyProvider()
    return LiveSecondarySupplyProvider()


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

async def run_secondary_supply_engine(
    provider: Optional[BaseSecondarySupplyProvider] = None,
) -> List[Dict[str, Any]]:
    """
    Sprint 16 — Secondary Supply Engine main entry point.

    Rules:
      Copper Scrap: if primary_secondary_spread < COPPER_SCRAP_SPREAD_FLOOR
        → scrap is undercutting primary mining economics
        → dispatch 'scrap_surge' alert for each recycler ticker

    Returns a list of triggered-alert dicts for observability.
    """
    from api.settings import dispatch_risk_alert

    if provider is None:
        provider = get_secondary_supply_provider()

    spreads = await provider.get_spreads()
    triggered: List[Dict[str, Any]] = []

    for item in spreads:
        material = item.get("material_name", "")
        spread = item.get("primary_secondary_spread")
        spread_pct = item.get("spread_pct") or 0.0

        if material == "Copper Scrap":
            if spread is not None and float(spread) < COPPER_SCRAP_SPREAD_FLOOR:
                logger.warning(
                    f"Secondary Supply Engine: Copper Scrap spread COLLAPSED "
                    f"${float(spread):.3f}/lb < ${COPPER_SCRAP_SPREAD_FLOOR}/lb floor "
                    f"— scrap flooding primary copper market"
                )
                recycler_tickers: List[str] = item.get("recycler_tickers") or []
                for ticker in recycler_tickers:
                    try:
                        await dispatch_risk_alert(
                            ticker=ticker,
                            score=75.0,
                            category="scrap_surge",
                        )
                        logger.info(
                            f"Secondary Supply Engine: scrap_surge alert "
                            f"dispatched for {ticker}"
                        )
                    except Exception as exc:
                        logger.warning(
                            f"Secondary Supply Engine: alert dispatch failed "
                            f"for {ticker}: {exc}"
                        )
                triggered.append({
                    "material": material,
                    "spread": float(spread),
                    "spread_pct": spread_pct,
                    "alert": "scrap_surge",
                    "recycler_tickers": recycler_tickers,
                })
            else:
                spread_str = f"${float(spread):.3f}/lb" if spread is not None else "N/A"
                logger.info(
                    f"Secondary Supply Engine: Copper Scrap spread {spread_str} "
                    f"≥ floor ${COPPER_SCRAP_SPREAD_FLOOR}/lb — no alert"
                )

        elif material == "Black Mass Index":
            # Observational only for now — log but don't alert
            spread_str = f"${float(spread):.2f}/kg" if spread is not None else "N/A"
            logger.info(
                f"Secondary Supply Engine: Black Mass spread {spread_str} "
                f"({spread_pct:.1f}%) — within normal range, monitoring only"
            )

        else:
            logger.debug(
                f"Secondary Supply Engine: unclassified material '{material}' — skip"
            )

    logger.info(
        f"Secondary Supply Engine: pipeline complete — "
        f"{len(triggered)} alert(s) dispatched"
    )
    return triggered
