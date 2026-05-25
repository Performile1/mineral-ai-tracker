"""
Mineral AI Tracker — Chokepoint Oracle (Sprint 16)
===================================================
Monitors freight/transit indices and raises geopolitical_friction_cost on
supply_chain_edges when a critical shipping corridor is disrupted.

Domain focus (2026):
  - Panama Canal Draft Restrictions  → copper/lithium from CL, PE
  - Red Sea / Suez Freight Index     → nickel/uranium from ZA, ID, AU, NG

Provider pattern (mirrors quant_watchdog.py):
  USE_MOCK_DATA=true  → MockChokepointProvider (domain-seeded data)
  USE_MOCK_DATA=false → LiveChokepointProvider (reads transit_metrics table)
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from loguru import logger
from psycopg2.extras import RealDictCursor

from schemas.omniscient import ChokepointAlert
from utils.database import get_db_connection, release_db_connection

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SPIKE_THRESHOLD_PCT = float(os.getenv("CHOKEPOINT_SPIKE_THRESHOLD_PCT", "20.0"))
FRICTION_DELTA = float(os.getenv("CHOKEPOINT_FRICTION_DELTA", "0.15"))

# Shipping corridor → upstream domicile countries most at risk
CORRIDOR_COUNTRIES: Dict[str, List[str]] = {
    "Panama":  ["CL", "PE", "MX", "CO"],          # South-American copper/lithium
    "Suez":    ["ZA", "ID", "AU", "NG", "IN"],    # African/Asian nickel & uranium
}


# ---------------------------------------------------------------------------
# Provider pattern
# ---------------------------------------------------------------------------

class BaseChokepointProvider(ABC):
    @abstractmethod
    async def get_transit_metrics(self) -> List[Dict[str, Any]]:
        """Return a list of current transit metric dicts."""


class MockChokepointProvider(BaseChokepointProvider):
    """
    Domain-seeded mock data representing 2026 corridor stress scenarios.
    Panama Canal is at RESTRICTED status (low water, draft limits).
    Red Sea is at FRICTION status (Houthi surcharges).
    """

    async def get_transit_metrics(self) -> List[Dict[str, Any]]:
        return [
            {
                "index_name": "Panama Canal Draft Restrictions",
                "current_value": 45.0,
                "weekly_change_pct": 25.0,
                "daily_change_pct": 8.0,
                "chokepoint_status": {"status": "RESTRICTED", "corridor": "Panama"},
                "alert_triggered": True,
                "alert_reason": (
                    "Low water levels — max draft reduced to 45 ft (norm 50 ft). "
                    "Affects copper/lithium exports from CL/PE."
                ),
            },
            {
                "index_name": "Red Sea / Suez Freight Index",
                "current_value": 4850.0,
                "weekly_change_pct": 18.0,
                "daily_change_pct": 3.5,
                "chokepoint_status": {"status": "FRICTION", "corridor": "Suez"},
                "alert_triggered": False,
                "alert_reason": (
                    "Elevated Houthi activity. SCFI Red Sea surcharge +$800/TEU. "
                    "Affects African/Asian nickel and uranium shipments."
                ),
            },
        ]


class LiveChokepointProvider(BaseChokepointProvider):
    """Reads latest row per index from the transit_metrics table."""

    async def get_transit_metrics(self) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT DISTINCT ON (index_name)
                        index_name, current_value, weekly_change_pct,
                        daily_change_pct, chokepoint_status,
                        alert_triggered, alert_reason
                    FROM transit_metrics
                    ORDER BY index_name, updated_at DESC
                """)
                return [dict(r) for r in cur.fetchall()]
        finally:
            release_db_connection(conn)


def get_chokepoint_provider() -> BaseChokepointProvider:
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
        return MockChokepointProvider()
    return LiveChokepointProvider()


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

async def run_chokepoint_oracle(
    provider: Optional[BaseChokepointProvider] = None,
) -> List[ChokepointAlert]:
    """
    Sprint 16 — Chokepoint Oracle main entry point.

    For each transit index where weekly_change_pct > SPIKE_THRESHOLD_PCT:
      1. Resolve the affected shipping corridor and its at-risk countries.
      2. Find supply_chain_edges whose upstream node domicile matches.
      3. Raise geopolitical_friction_cost by +FRICTION_DELTA on those edges.
      4. Dispatch a 'chokepoint' risk alert for the affected tickers.

    Returns a list of ChokepointAlert objects (one per triggered index).
    """
    from api.settings import dispatch_risk_alert

    if provider is None:
        provider = get_chokepoint_provider()

    metrics = await provider.get_transit_metrics()
    alerts: List[ChokepointAlert] = []

    for metric in metrics:
        spike_pct = float(metric.get("weekly_change_pct") or 0.0)
        if spike_pct < SPIKE_THRESHOLD_PCT:
            logger.debug(
                f"Chokepoint Oracle: {metric['index_name']} spike "
                f"{spike_pct:.1f}% < threshold {SPIKE_THRESHOLD_PCT}% — skip"
            )
            continue

        index_name = metric["index_name"]
        status_obj = metric.get("chokepoint_status") or {}
        corridor = status_obj.get("corridor", "")
        affected_countries = CORRIDOR_COUNTRIES.get(corridor, [])

        if not affected_countries:
            logger.info(
                f"Chokepoint Oracle: no country mapping for corridor '{corridor}' "
                f"({index_name}) — skipping friction update"
            )
            continue

        logger.info(
            f"Chokepoint Oracle: SPIKE — {index_name} +{spike_pct:.1f}% "
            f"| corridor={corridor} | at-risk countries: {affected_countries}"
        )

        affected_tickers = await _raise_friction_on_edges(affected_countries, FRICTION_DELTA)

        alert = ChokepointAlert(
            index_name=index_name,
            current_value=float(metric.get("current_value") or 0.0),
            spike_pct=spike_pct,
            affected_edge_ids=affected_tickers,
            friction_cost_delta=FRICTION_DELTA,
            alert_reason=metric.get("alert_reason"),
        )
        alerts.append(alert)

        # Dispatch alerts for each affected upstream ticker (cap at 20 to avoid spam)
        for ticker in affected_tickers[:20]:
            try:
                await dispatch_risk_alert(
                    ticker=ticker,
                    score=min(100.0, spike_pct),
                    category="chokepoint",
                )
            except Exception as exc:
                logger.warning(
                    f"Chokepoint Oracle: alert dispatch failed for {ticker}: {exc}"
                )

    logger.info(f"Chokepoint Oracle: pipeline complete — {len(alerts)} spike alert(s)")
    return alerts


async def _raise_friction_on_edges(
    countries: List[str],
    delta: float,
) -> List[str]:
    """
    UPDATE supply_chain_edges SET geopolitical_friction_cost += delta
    WHERE upstream node domicile_country IN countries.

    Returns the list of affected upstream_ticker values.
    """
    if not countries:
        return []

    conn = get_db_connection()
    affected: List[str] = []
    try:
        placeholders = ", ".join(["%s"] * len(countries))

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT DISTINCT sce.upstream_ticker
                FROM supply_chain_edges sce
                JOIN supply_chain_nodes scn
                    ON scn.asset_ticker = sce.upstream_ticker
                WHERE scn.domicile_country IN ({placeholders})
                """,
                countries,
            )
            affected = [r["upstream_ticker"] for r in cur.fetchall()]

        if affected:
            tick_placeholders = ", ".join(["%s"] * len(affected))
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE supply_chain_edges
                    SET geopolitical_friction_cost =
                            COALESCE(geopolitical_friction_cost, 0) + %s,
                        geo_status              = 'FRICTION',
                        geo_last_evaluated_at   = NOW()
                    WHERE upstream_ticker IN ({tick_placeholders})
                    """,
                    [delta] + affected,
                )
                conn.commit()
            logger.info(
                f"Chokepoint Oracle: friction_cost +{delta:.2f} applied to "
                f"{len(affected)} upstream ticker(s): {affected}"
            )
    except Exception as exc:
        conn.rollback()
        logger.error(f"Chokepoint Oracle: friction update failed: {exc}")
    finally:
        release_db_connection(conn)

    return affected
