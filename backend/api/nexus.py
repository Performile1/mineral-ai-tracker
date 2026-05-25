"""
Mineral AI Tracker - Nexus Graph API (Phase 19.0 - 20.5)
Version: 19.0
Description: FastAPI routes for the Nexus supply chain graph.
             Returns nodes and edges for the ForceDirectedGraph frontend component.
             Supports filtering by raw_material_type and relationship_strength.
"""

import asyncio
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from api.deps import get_current_user
from utils.database import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor


class PatchDomicileRequest(BaseModel):
    manual_country_code: str = Field(
        ...,
        min_length=2,
        max_length=3,
        description="ISO-2 or ISO-3 country code, e.g. 'US', 'CA', 'AU'",
    )

router = APIRouter(prefix="/api/nexus", tags=["Nexus Graph"])

BINDING_STRENGTHS = {"CONFIRMED_NAME", "REVENUE_CONCENTRATION"}
INTENT_STRENGTHS = {"INTENT_MOU", "INTENT_LOI", "INFERRED"}


@router.get("/graph", response_model=Dict[str, Any])
async def get_nexus_graph(
    material: Optional[str] = Query(default=None, description="Filter by raw material type, e.g. 'Copper'"),
    include_non_binding: bool = Query(default=True, description="Include MoU/LoI/Inferred edges"),
    upstream_ticker: Optional[str] = Query(default=None, description="Filter graph from a specific upstream node"),
    downstream_ticker: Optional[str] = Query(default=None, description="Filter graph to a specific downstream node"),
    limit: int = Query(default=500, ge=1, le=5000, description="Maximum number of edges to return"),
    offset: int = Query(default=0, ge=0, description="Number of edges to skip"),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns the full supply chain graph as nodes and edges.
    
    Edge line styles (for frontend rendering):
    - CONFIRMED_NAME / REVENUE_CONCENTRATION -> solid thick line
    - INTENT_MOU / INTENT_LOI / INFERRED -> dashed line
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Build edge filter
            # Sprint 14 (Skuld I): always exclude edges with a past expiry date
            edge_filters = [
                "(e.contract_expiry_date IS NULL OR e.contract_expiry_date >= CURRENT_DATE)"
            ]
            edge_params: List[Any] = []

            if material:
                edge_filters.append("LOWER(e.raw_material_type) = LOWER(%s)")
                edge_params.append(material)

            if not include_non_binding:
                placeholders = ", ".join(["%s"] * len(BINDING_STRENGTHS))
                edge_filters.append(f"e.relationship_strength IN ({placeholders})")
                edge_params.extend(list(BINDING_STRENGTHS))

            if upstream_ticker:
                edge_filters.append("e.upstream_ticker = %s")
                edge_params.append(upstream_ticker.upper())

            if downstream_ticker:
                edge_filters.append("e.downstream_ticker = %s")
                edge_params.append(downstream_ticker.upper())

            where_clause = " AND ".join(edge_filters)

            # Total count for pagination metadata
            cur.execute(
                f"SELECT COUNT(*) FROM supply_chain_edges e WHERE {where_clause}",
                edge_params,
            )
            total_edge_count = cur.fetchone()["count"]

            cur.execute(f"""
                SELECT
                    e.id,
                    e.upstream_ticker,
                    e.downstream_ticker,
                    e.relationship_strength,
                    e.raw_material_type,
                    e.contract_type,
                    e.contract_volume_numeric,
                    e.contract_expiry_date,
                    e.expected_materialization_date,
                    e.source_document,
                    e.updated_at,
                    e.geopolitical_friction_cost
                FROM supply_chain_edges e
                WHERE {where_clause}
                ORDER BY
                    CASE e.relationship_strength
                        WHEN 'CONFIRMED_NAME'       THEN 1
                        WHEN 'REVENUE_CONCENTRATION' THEN 2
                        WHEN 'INTENT_MOU'           THEN 3
                        WHEN 'INTENT_LOI'           THEN 4
                        WHEN 'INFERRED'             THEN 5
                    END
                LIMIT %s OFFSET %s
            """, edge_params + [limit, offset])
            edge_rows = cur.fetchall()

            # Collect all referenced tickers
            tickers_in_graph = set()
            for row in edge_rows:
                tickers_in_graph.add(row["upstream_ticker"])
                tickers_in_graph.add(row["downstream_ticker"])

            # Fetch node data for referenced tickers
            nodes_data = {}
            if tickers_in_graph:
                placeholders = ", ".join(["%s"] * len(tickers_in_graph))
                cur.execute(f"""
                    SELECT asset_ticker, company_type, company_name, primary_sector,
                           domicile_country, extracted_data, last_scanned_at,
                           buyout_probability_score
                    FROM supply_chain_nodes
                    WHERE asset_ticker IN ({placeholders})
                """, list(tickers_in_graph))
                for row in cur.fetchall():
                    nodes_data[row["asset_ticker"]] = dict(row)

        # Build nodes array
        nodes = []
        for ticker in tickers_in_graph:
            nd = nodes_data.get(ticker, {})
            extracted = nd.get("extracted_data") or {}
            meta = extracted.get("_meta", {}) if isinstance(extracted, dict) else {}
            node = {
                "id": ticker,
                "ticker": ticker,
                "company_type": nd.get("company_type", "UNKNOWN"),
                "company_name": nd.get("company_name") or ticker,
                "primary_sector": nd.get("primary_sector"),
                "domicile_country": nd.get("domicile_country"),
                "last_scanned_at": nd["last_scanned_at"].isoformat() if nd.get("last_scanned_at") else None,
                "dilution_risk_score": meta.get("dilution_risk_score"),
                "buyout_probability_score": float(nd["buyout_probability_score"]) if nd.get("buyout_probability_score") is not None else None,
                "chokepoint_exposure": meta.get("chokepoint_exposure"),
                "group": nd.get("company_type", "UNKNOWN"),
            }
            nodes.append(node)

        # Build edges array with rendering hints
        edges = []
        for row in edge_rows:
            strength = row["relationship_strength"]
            is_binding = strength in BINDING_STRENGTHS

            ct = row["contract_type"] or "STANDARD"
            base_width = 3 if strength == "CONFIRMED_NAME" else (2 if strength == "REVENUE_CONCENTRATION" else 1)
            edges.append({
                "id": str(row["id"]),
                "source": row["upstream_ticker"],
                "target": row["downstream_ticker"],
                "relationship_strength": strength,
                "raw_material_type": row["raw_material_type"],
                "contract_type": ct,
                "contract_volume_numeric": float(row["contract_volume_numeric"]) if row["contract_volume_numeric"] is not None else None,
                "contract_expiry_date": row["contract_expiry_date"].isoformat() if row.get("contract_expiry_date") else None,
                "expected_materialization_date": (
                    row["expected_materialization_date"].isoformat()
                    if row["expected_materialization_date"] else None
                ),
                "source_document": row["source_document"],
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                "geopolitical_friction_cost": float(row["geopolitical_friction_cost"]) if row.get("geopolitical_friction_cost") is not None else None,
                # Frontend rendering hints
                "line_style": "solid" if is_binding else "dashed",
                "line_width": base_width * 2 if ct == "TAKE_OR_PAY" else base_width,
                "is_binding": is_binding,
            })

        # Material legend (unique materials for UI filter)
        materials = sorted(set(
            e["raw_material_type"] for e in edges
            if e["raw_material_type"]
        ))

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "binding_edges": sum(1 for e in edges if e["is_binding"]),
            "intent_edges": sum(1 for e in edges if not e["is_binding"]),
            "available_materials": materials,
            "pagination": {
                "total_edges": total_edge_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_edge_count,
            },
            "filters_applied": {
                "material": material,
                "include_non_binding": include_non_binding,
                "upstream_ticker": upstream_ticker,
                "downstream_ticker": downstream_ticker,
            },
        }

    except Exception as e:
        logger.error(f"nexus graph error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        release_db_connection(conn)


@router.get("/node/{ticker}", response_model=Dict[str, Any])
async def get_node_detail(
    ticker: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get full detail for a single supply chain node including its edges."""
    ticker = ticker.upper()
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT asset_ticker, company_type, company_name, primary_sector,
                       extracted_data, last_scanned_at, created_at
                FROM supply_chain_nodes
                WHERE asset_ticker = %s
            """, (ticker,))
            node = cur.fetchone()

            if not node:
                raise HTTPException(status_code=404, detail=f"Node {ticker} not found")

            cur.execute("""
                SELECT id, upstream_ticker, downstream_ticker, relationship_strength,
                       raw_material_type, expected_materialization_date,
                       source_document, updated_at
                FROM supply_chain_edges
                WHERE upstream_ticker = %s OR downstream_ticker = %s
                ORDER BY relationship_strength
            """, (ticker, ticker))
            edges = cur.fetchall()

        result = dict(node)
        result["last_scanned_at"] = result["last_scanned_at"].isoformat() if result["last_scanned_at"] else None
        result["created_at"] = result["created_at"].isoformat() if result["created_at"] else None
        result["connections"] = []

        for e in edges:
            edge_dict = dict(e)
            edge_dict["id"] = str(edge_dict["id"])
            edge_dict["expected_materialization_date"] = (
                edge_dict["expected_materialization_date"].isoformat()
                if edge_dict["expected_materialization_date"] else None
            )
            edge_dict["updated_at"] = edge_dict["updated_at"].isoformat() if edge_dict["updated_at"] else None
            result["connections"].append(edge_dict)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"node detail error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        release_db_connection(conn)


@router.post("/trigger-nightly", response_model=Dict[str, Any])
async def trigger_nightly_nexus(
    consumer_tickers: str = Query(..., description="Comma-separated manufacturer tickers"),
    producer_tickers: str = Query(..., description="Comma-separated miner tickers"),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Manually trigger a Nexus Engine nightly analysis run."""
    consumers = [t.strip().upper() for t in consumer_tickers.split(",") if t.strip()]
    producers = [t.strip().upper() for t in producer_tickers.split(",") if t.strip()]

    if not consumers or not producers:
        raise HTTPException(status_code=400, detail="Both consumer_tickers and producer_tickers are required")

    try:
        from engines.nexus_engine import NexusEngine
        engine = NexusEngine()
        result = await engine.run_nightly(consumers, producers)
        return result
    except Exception as e:
        logger.error(f"Nexus nightly trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/node/{ticker}/domicile", response_model=Dict[str, Any])
async def patch_node_domicile(
    ticker: str,
    body: PatchDomicileRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    God Mode override: manually set the domicile_country for a supply chain node.
    Immediately re-evaluates geopolitical friction on all edges involving this node.
    """
    ticker = ticker.upper()
    country = body.manual_country_code.upper()

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT asset_ticker FROM supply_chain_nodes WHERE asset_ticker = %s",
                (ticker,),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"Node {ticker} not found")

            cur.execute(
                "UPDATE supply_chain_nodes SET domicile_country = %s WHERE asset_ticker = %s",
                (country, ticker),
            )
            conn.commit()
        logger.info(f"God Mode: {ticker} domicile_country set to {country}")
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Domicile patch failed for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        release_db_connection(conn)

    # Async: re-evaluate geo-friction in the background so the caller gets an immediate response
    async def _reeval():
        try:
            from engines.nexus_engine import NexusEngine
            engine = NexusEngine()
            loop = asyncio.get_event_loop()
            updated = await loop.run_in_executor(None, engine.evaluate_geopolitical_friction)
            logger.info(f"God Mode re-eval: {updated} edges updated after {ticker} country change")
        except Exception as exc:
            logger.error(f"God Mode re-eval failed: {exc}")

    asyncio.create_task(_reeval())

    return {
        "ticker": ticker,
        "domicile_country": country,
        "message": f"domicile_country updated to '{country}'. Geo-friction re-evaluation triggered.",
    }
