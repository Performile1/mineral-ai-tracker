"""
Mineral AI Tracker — God Mode Dashboard API (Sprint 17)
========================================================
Endpoint: GET /api/dashboard/summary

Returns an aggregated intelligence snapshot:
  top_ma_targets      — top 5 nodes by buyout_probability_score
  top_dilution_risks  — top 5 nodes by dilution_risk_score (from extracted_data._meta)
  active_disputes     — 5 most recent active labour disputes
  chokepoint_alerts   — supply_chain_edges with geopolitical_friction_cost > 0
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from psycopg2.extras import RealDictCursor

from api.deps import get_current_user
from utils.database import get_db_connection, release_db_connection

router = APIRouter(prefix="/api/dashboard", tags=["God Mode Dashboard"])


@router.get("/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Sprint 17 — Aggregated intelligence snapshot for the Command Center.

    Returns four sections:
      top_ma_targets      list[node]  — sorted by buyout_probability_score DESC
      top_dilution_risks  list[node]  — sorted by dilution_risk_score DESC
      active_disputes     list[dispute]
      chokepoint_alerts   list[edge]  — friction_cost > 0
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            # -- 1. Top M&A targets -----------------------------------------
            cur.execute("""
                SELECT asset_ticker, company_name, company_type, domicile_country,
                       buyout_probability_score
                FROM supply_chain_nodes
                WHERE buyout_probability_score IS NOT NULL
                ORDER BY buyout_probability_score DESC
                LIMIT 5
            """)
            top_ma = [dict(r) for r in cur.fetchall()]

            # -- 2. Top dilution risks (score lives in extracted_data._meta) --
            cur.execute("""
                SELECT asset_ticker, company_name, company_type, domicile_country,
                       (extracted_data #>> '{_meta,dilution_risk_score}')::float
                           AS dilution_risk_score
                FROM supply_chain_nodes
                WHERE extracted_data #>> '{_meta,dilution_risk_score}' IS NOT NULL
                ORDER BY dilution_risk_score DESC
                LIMIT 5
            """)
            top_dilution = [dict(r) for r in cur.fetchall()]

            # -- 3. Active labour disputes ------------------------------------
            cur.execute("""
                SELECT id, asset_ticker, facility_name, region, dispute_type,
                       severity_level, description, is_early_warning,
                       triggered_at
                FROM labor_disputes
                WHERE is_active = TRUE
                ORDER BY severity_level DESC, triggered_at DESC
                LIMIT 5
            """)
            disputes_raw = cur.fetchall()
            active_disputes: List[Dict[str, Any]] = []
            for r in disputes_raw:
                d = dict(r)
                d["id"] = str(d["id"])
                d["triggered_at"] = (
                    d["triggered_at"].isoformat() if d.get("triggered_at") else None
                )
                active_disputes.append(d)

            # -- 4. Chokepoint alerts (edges with elevated friction) ----------
            cur.execute("""
                SELECT sce.id, sce.upstream_ticker, sce.downstream_ticker,
                       sce.raw_material_type, sce.geopolitical_friction_cost,
                       sce.geo_status,
                       scn_up.domicile_country AS upstream_country,
                       scn_up.company_name     AS upstream_name
                FROM supply_chain_edges sce
                LEFT JOIN supply_chain_nodes scn_up
                    ON scn_up.asset_ticker = sce.upstream_ticker
                WHERE sce.geopolitical_friction_cost > 0
                ORDER BY sce.geopolitical_friction_cost DESC
                LIMIT 10
            """)
            chokepoints_raw = cur.fetchall()
            chokepoint_alerts: List[Dict[str, Any]] = []
            for r in chokepoints_raw:
                c = dict(r)
                c["id"] = str(c["id"])
                c["geopolitical_friction_cost"] = (
                    float(c["geopolitical_friction_cost"])
                    if c.get("geopolitical_friction_cost") is not None
                    else None
                )
                chokepoint_alerts.append(c)

        return {
            "top_ma_targets": top_ma,
            "top_dilution_risks": top_dilution,
            "active_disputes": active_disputes,
            "chokepoint_alerts": chokepoint_alerts,
        }

    except Exception as exc:
        logger.error(f"dashboard/summary error: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        release_db_connection(conn)
