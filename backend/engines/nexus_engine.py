"""
Mineral AI Tracker - Nexus Engine (Phase 19.0 - 22.0)
Version: 22.0
Description: RAG-powered supply chain analysis orchestrator.
             Runs Prompt 1 (Agent A - Manufacturer X-Ray) and Prompt 2 (Agent B - Mining Customer Registry)
             nightly to extract confirmed supply chain relationships from annual reports.
             Implements cross_reference_nexus() to auto-establish CONFIRMED_NAME edges when
             a manufacturer's named_suppliers match a miner's named_customers.
             Phase 22.0: evaluate_geopolitical_friction() overlays sovereign firewall data
             (tariffs, CBAM, IRA, sanctions) on every edge and classifies geo_status.
"""

import json
import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from loguru import logger

from utils.database import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

VALID_CONTRACT_TYPES = frozenset({"STANDARD", "OFFTAKE", "TAKE_OR_PAY"})


def parse_and_validate_claude_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Sprint 13 (Q5) \u2014 Pure function: extract and structurally validate the JSON
    blob returned by Claude.

    Responsibilities:
    1. Find the first `{...}` block in raw_text (Claude often adds prose).
    2. Parse the JSON.
    3. Validate structural invariants (named_suppliers is a list, offtake
       agreements have valid contract_type, numeric volumes are numeric).
    4. Apply defaults (contract_type defaults to 'STANDARD' when absent).

    Returns a validated dict, or None if the response is structurally corrupt
    (logs a warning but never raises).

    This is the canonical validation logic.  Tests import this function
    directly without instantiating NexusEngine or touching the DB/Claude API.
    """
    start = raw_text.find("{")
    end = raw_text.rfind("}") + 1
    if start == -1 or end <= start:
        logger.warning("parse_and_validate_claude_response: no JSON object found in text")
        return None

    try:
        data = json.loads(raw_text[start:end])
    except json.JSONDecodeError as exc:
        logger.warning(f"parse_and_validate_claude_response: JSON decode error — {exc}")
        return None

    # --- named_suppliers must be a list ----------------------------------------
    if "named_suppliers" in data and not isinstance(data["named_suppliers"], list):
        logger.warning(
            "parse_and_validate_claude_response: named_suppliers is not a list — "
            f"type={type(data['named_suppliers']).__name__}"
        )
        return None

    # --- validate offtake_agreements -------------------------------------------
    agreements = data.get("offtake_agreements")
    if agreements is not None:
        if not isinstance(agreements, list):
            logger.warning("parse_and_validate_claude_response: offtake_agreements is not a list")
            return None

        sanitised = []
        for item in agreements:
            if not isinstance(item, dict):
                logger.warning("parse_and_validate_claude_response: skipping non-dict agreement")
                continue

            # Default contract_type
            ct = item.get("contract_type", "STANDARD")
            if ct not in VALID_CONTRACT_TYPES:
                logger.warning(
                    f"parse_and_validate_claude_response: invalid contract_type '{ct}' "
                    f"— defaulting to STANDARD"
                )
                item["contract_type"] = "STANDARD"

            # Coerce volume to float
            vol = item.get("contract_volume_numeric")
            if vol is not None:
                try:
                    item["contract_volume_numeric"] = float(vol)
                except (TypeError, ValueError):
                    logger.warning(
                        f"parse_and_validate_claude_response: non-numeric volume '{vol}' "
                        f"— setting to None"
                    )
                    item["contract_volume_numeric"] = None

            # Coerce is_expiry_estimated to a boolean
            exp_est = item.get("is_expiry_estimated")
            if exp_est is None:
                item["is_expiry_estimated"] = False
            else:
                item["is_expiry_estimated"] = bool(exp_est)

            sanitised.append(item)
        data["offtake_agreements"] = sanitised

    return data


PROMPT_MANUFACTURER_XRAY = """SYSTEM INSTRUCTION: FORENSIC SUPPLY CHAIN ANALYST

Read the following annual report content for manufacturer ticker {ticker}.
Extract physical input materials and counterparties to a clean JSON object ONLY, no prose:

{{
  "named_suppliers": ["Exact company names of raw material suppliers"],
  "offtake_agreements": [
    {{
      "material": "Copper",
      "partner": "Boliden",
      "duration_months": 48,
      "contract_type": "TAKE_OR_PAY",
      "contract_volume_numeric": 5000.0,
      "contract_expiry_date": "2028-12-31",
      "is_expiry_estimated": false
    }}
  ],
  "single_source_risks": [{{"material": "Neon", "country_or_company": "China"}}],
  "supply_chain_bottlenecks": ["Quotes about material scarcity or delays"]
}}

CONTRACT CLASSIFICATION RULES (mandatory):
- Set contract_type to "TAKE_OR_PAY" if the agreement states the buyer MUST pay regardless of whether physical delivery is taken, or if keywords like 'take-or-pay', 'guaranteed minimum purchase', 'hell-or-high-water', or 'pay regardless of delivery' appear.
- Set contract_type to "OFFTAKE" if it is a binding purchase commitment WITHOUT a take-or-pay clause.
- Set contract_type to "STANDARD" for all other / unconfirmed relationships.
- Extract contract_volume_numeric as a float if a tonnage or unit volume is stated.
- Extract contract_expiry_date as ISO-8601 (YYYY-MM-DD) if an end date or expiry year is stated; otherwise null.
- Set is_expiry_estimated to true if the exact contract expiry date is not explicitly stated but has been inferred from the project's overall lifespan or context. Set to false if the date is explicitly written in the document.

DOCUMENT TEXT:
{context}"""


PROMPT_MINING_CUSTOMER_REGISTRY = """SYSTEM INSTRUCTION: FORENSIC REVENUE ANALYST

Read the following annual report content for mining company ticker {ticker}.
Identify major customers from revenue concentration sections to a clean JSON object ONLY:

{{
  "named_customers": ["Company names of stated buyers"],
  "revenue_concentration": [{{"customer": "Customer A", "percentage": 15}}],
  "offtake_commitments": [
    {{
      "material": "Uranium",
      "volume": "500t",
      "partner": "Centrus",
      "contract_type": "TAKE_OR_PAY",
      "contract_volume_numeric": 500.0,
      "contract_expiry_date": "2030-06-30",
      "is_expiry_estimated": false
    }}
  ],
  "force_majeure_risks": ["Quotes about production or delivery risks"]
}}

CONTRACT CLASSIFICATION RULES (mandatory):
- Set contract_type to "TAKE_OR_PAY" if the agreement states the buyer MUST pay regardless of whether physical delivery is taken, or if keywords like 'take-or-pay', 'guaranteed minimum purchase', 'hell-or-high-water', or 'pay regardless of delivery' appear.
- Set contract_type to "OFFTAKE" if it is a binding purchase commitment WITHOUT a take-or-pay clause.
- Set contract_type to "STANDARD" for all other / unconfirmed relationships.
- Extract contract_volume_numeric as a float if a tonnage or unit volume is stated; otherwise null.
- Extract contract_expiry_date as ISO-8601 (YYYY-MM-DD) if an end date or expiry year is stated; otherwise null.
- Set is_expiry_estimated to true if the exact contract expiry date is not explicitly stated but has been inferred from the project's overall lifespan or context. Set to false if the date is explicitly written in the document.

DOCUMENT TEXT:
{context}"""


class NexusEngine:
    """
    Phase 19.0: RAG-powered supply chain relationship extractor and matchmaker.
    
    Pipeline:
    1. For each CONSUMER node: run Prompt 1 to extract named_suppliers
    2. For each PRODUCER node: run Prompt 2 to extract named_customers
    3. cross_reference_nexus(): match named_suppliers vs named_customers -> CONFIRMED_NAME edges
    """

    def __init__(self):
        from engines.rag_engine import get_rag_engine
        self.rag = get_rag_engine()

    async def _call_claude(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Send a prompt to Claude 3.5 Sonnet and return validated JSON."""
        if not ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY not set - NexusEngine cannot run")
            return None

        import httpx
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-3-5-sonnet-20241022",
                        "max_tokens": 1024,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                if resp.status_code != 200:
                    logger.error(f"Claude API error {resp.status_code}: {resp.text[:200]}")
                    return None

                raw_text = resp.json()["content"][0]["text"]
                return parse_and_validate_claude_response(raw_text)
        except Exception as e:
            logger.error(f"Claude call failed: {e}")
            return None

    async def analyze_manufacturer(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Prompt 1 (Agent A): Extract supply chain data from a manufacturer's annual report.
        Persists result to supply_chain_nodes with company_type=CONSUMER.
        """
        ticker = ticker.upper()
        logger.info(f"NexusEngine: Manufacturer X-Ray for {ticker}")

        context = await self.rag.get_context_for_ticker(
            ticker,
            "named suppliers raw materials offtake agreements supply chain",
            limit=6,
        )
        if not context:
            logger.warning(f"No document context found for manufacturer {ticker}")
            return None

        prompt = PROMPT_MANUFACTURER_XRAY.format(ticker=ticker, context=context[:8000])
        extracted = await self._call_claude(prompt)

        if extracted:
            # Sprint 14 (Skuld B) — Quant Handshake: compute dilution risk immediately
            # after extraction so _meta.dilution_risk_score is live on first scan.
            dilution_score: Optional[float] = None
            try:
                from agents.quant_watchdog import get_dilution_risk_score
                dilution_score = await get_dilution_risk_score(ticker)
            except Exception as exc:
                logger.warning(f"Quant Handshake failed for {ticker}: {exc}")
            self._upsert_node(
                ticker, "CONSUMER", extracted,
                prompt_version="MANUFACTURER_XRAY_v25",
                dilution_risk_score=dilution_score,
            )
            logger.info(
                f"Manufacturer X-Ray complete for {ticker}: "
                f"{len(extracted.get('named_suppliers', []))} suppliers, "
                f"dilution_risk_score={dilution_score}"
            )

        return extracted

    async def analyze_miner(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Prompt 2 (Agent B): Extract customer registry from a miner's annual report.
        Persists result to supply_chain_nodes with company_type=PRODUCER.
        """
        ticker = ticker.upper()
        logger.info(f"NexusEngine: Mining Customer Registry for {ticker}")

        context = await self.rag.get_context_for_ticker(
            ticker,
            "named customers revenue concentration offtake commitments production",
            limit=6,
        )
        if not context:
            logger.warning(f"No document context found for miner {ticker}")
            return None

        prompt = PROMPT_MINING_CUSTOMER_REGISTRY.format(ticker=ticker, context=context[:8000])
        extracted = await self._call_claude(prompt)

        if extracted:
            # Sprint 14 (Skuld B) — Quant Handshake
            dilution_score: Optional[float] = None
            try:
                from agents.quant_watchdog import get_dilution_risk_score
                dilution_score = await get_dilution_risk_score(ticker)
            except Exception as exc:
                logger.warning(f"Quant Handshake failed for {ticker}: {exc}")
            self._upsert_node(
                ticker, "PRODUCER", extracted,
                prompt_version="MINING_CUSTOMER_REGISTRY_v25",
                dilution_risk_score=dilution_score,
            )
            logger.info(
                f"Customer Registry complete for {ticker}: "
                f"{len(extracted.get('named_customers', []))} customers, "
                f"dilution_risk_score={dilution_score}"
            )

        return extracted

    def _upsert_node(
        self,
        ticker: str,
        company_type: str,
        extracted_data: Dict[str, Any],
        prompt_version: str = "NEXUS_ENGINE_v25",
        dilution_risk_score: Optional[float] = None,
    ) -> None:
        """Upsert a supply chain node with extracted data + Data Lineage _meta."""
        # Sprint 10.4 — wrap payload with provenance metadata
        # Sprint 14 — write dilution_risk_score to _meta when available
        payload = dict(extracted_data)
        payload["_meta"] = {
            "source": "RAG_CLAUDE_3.5",
            "prompt_version": prompt_version,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "dilution_risk_score": dilution_risk_score,
        }
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO supply_chain_nodes
                        (asset_ticker, company_type, extracted_data, last_scanned_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (asset_ticker)
                    DO UPDATE SET
                        company_type   = EXCLUDED.company_type,
                        extracted_data = EXCLUDED.extracted_data,
                        last_scanned_at = NOW()
                """, (ticker, company_type, json.dumps(payload)))
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to upsert node for {ticker}: {e}")
        finally:
            release_db_connection(conn)

    def cross_reference_nexus(self) -> int:
        """
        Matchmaker: Cross-reference manufacturers' named_suppliers against miners' named_customers.
        When a match is found (fuzzy name match), creates a CONFIRMED_NAME edge.
        
        Returns:
            Number of new CONFIRMED_NAME edges established
        """
        logger.info("NexusEngine: Running cross_reference_nexus matchmaking")
        conn = get_db_connection()
        edges_created = 0

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT asset_ticker, extracted_data
                    FROM supply_chain_nodes
                    WHERE company_type = 'CONSUMER'
                      AND extracted_data IS NOT NULL
                """)
                consumers = cur.fetchall()

                cur.execute("""
                    SELECT asset_ticker, extracted_data
                    FROM supply_chain_nodes
                    WHERE company_type = 'PRODUCER'
                      AND extracted_data IS NOT NULL
                """)
                producers = cur.fetchall()

            # Build lookup: miner ticker -> set of named customer names (normalised)
            miner_customers: Dict[str, List[str]] = {}
            for prod in producers:
                data = prod["extracted_data"] or {}
                customers = [c.lower().strip() for c in data.get("named_customers", [])]
                if customers:
                    miner_customers[prod["asset_ticker"]] = customers

            # For each manufacturer, check if its named_suppliers appear in miner customer lists
            with conn.cursor() as cur:
                for consumer in consumers:
                    consumer_ticker = consumer["asset_ticker"]
                    data = consumer["extracted_data"] or {}
                    named_suppliers = [s.lower().strip() for s in data.get("named_suppliers", [])]

                    for miner_ticker, cust_names in miner_customers.items():
                        for supplier_name in named_suppliers:
                            # Fuzzy: check if miner ticker or company name appears in supplier name
                            miner_lower = miner_ticker.lower()
                            match = any(
                                supplier_name in cust or cust in supplier_name or miner_lower in supplier_name
                                for cust in cust_names
                            )
                            if match:
                                # Determine material from producer offtake commitments
                                prod_data = next(
                                    (p["extracted_data"] for p in producers
                                     if p["asset_ticker"] == miner_ticker), {}
                                ) or {}
                                offtakes = prod_data.get("offtake_commitments", [])
                                material = offtakes[0].get("material") if offtakes else None

                                try:
                                    # Extract contract metadata from producer offtake_commitments
                                    first_offtake = offtakes[0] if offtakes else {}
                                    contract_type = first_offtake.get("contract_type", "STANDARD")
                                    if contract_type not in ("STANDARD", "OFFTAKE", "TAKE_OR_PAY"):
                                        contract_type = "STANDARD"
                                    contract_vol = first_offtake.get("contract_volume_numeric")
                                    contract_exp = first_offtake.get("contract_expiry_date")

                                    cur.execute("""
                                        INSERT INTO supply_chain_edges
                                            (upstream_ticker, downstream_ticker,
                                             relationship_strength, raw_material_type,
                                             contract_type, contract_volume_numeric,
                                             contract_expiry_date,
                                             source_document, updated_at)
                                        VALUES (%s, %s, 'CONFIRMED_NAME', %s, %s, %s, %s,
                                                'cross_reference_nexus', NOW())
                                        ON CONFLICT (upstream_ticker, downstream_ticker) DO UPDATE SET
                                            relationship_strength   = EXCLUDED.relationship_strength,
                                            raw_material_type       = EXCLUDED.raw_material_type,
                                            contract_type           = EXCLUDED.contract_type,
                                            contract_volume_numeric = EXCLUDED.contract_volume_numeric,
                                            contract_expiry_date    = EXCLUDED.contract_expiry_date,
                                            source_document         = EXCLUDED.source_document,
                                            updated_at              = NOW()
                                        WHERE EXCLUDED.contract_type = 'TAKE_OR_PAY'
                                           OR (EXCLUDED.contract_type = 'OFFTAKE'
                                               AND supply_chain_edges.contract_type = 'STANDARD')
                                           OR (EXCLUDED.contract_type = 'STANDARD'
                                               AND supply_chain_edges.contract_type = 'STANDARD')
                                    """, (miner_ticker, consumer_ticker, material,
                                          contract_type, contract_vol, contract_exp))
                                    edges_created += 1
                                    logger.info(
                                        f"CONFIRMED_NAME edge: {miner_ticker} -> {consumer_ticker} "
                                        f"(material: {material}, match: '{supplier_name}')"
                                    )
                                except Exception as e:
                                    logger.warning(f"Edge insert failed: {e}")

                conn.commit()

        except Exception as e:
            conn.rollback()
            logger.error(f"cross_reference_nexus failed: {e}")
        finally:
            conn.close()

        logger.info(f"cross_reference_nexus: {edges_created} CONFIRMED_NAME edges established")
        return edges_created

    def evaluate_geopolitical_friction(self) -> int:
        """
        Phase 22.0 – Sovereign Firewall overlay.

        For every edge in supply_chain_edges, look up the upstream and downstream
        node's domicile_country, then query trade_policies for applicable policies.
        Aggregate friction cost and classify geo_status:
          - SUBSIDISED  : aggregate friction < 0  (IRA / subsidy benefit)
          - COMPLIANT   : no significant policy applies (0–2%)
          - FRICTION    : cost premium 2–40%   (tariff / CBAM)
          - TOXIC       : cost premium > 40%   (heavy tariff / anti-dumping)
          - SANCTIONED  : any SANCTION or EXPORT_BAN policy found (999%)
          - UNKNOWN     : missing domicile data
        """
        conn = get_db_connection()
        updated = 0
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Fetch all edges with upstream/downstream country info
                cur.execute("""
                    SELECT sce.id,
                           sce.upstream_ticker,
                           sce.downstream_ticker,
                           sce.raw_material_type,
                           up.domicile_country AS upstream_country,
                           dn.domicile_country AS downstream_country
                    FROM supply_chain_edges sce
                    LEFT JOIN supply_chain_nodes up ON up.asset_ticker = sce.upstream_ticker
                    LEFT JOIN supply_chain_nodes dn ON dn.asset_ticker = sce.downstream_ticker
                """)
                edges = cur.fetchall()

                for edge in edges:
                    origin = edge["upstream_country"]
                    dest   = edge["downstream_country"]
                    mat    = edge["raw_material_type"] or "General"

                    if not origin or not dest:
                        geo_status = "UNKNOWN"
                        friction   = None
                        worst_type = None
                    else:
                        # Look up matching policies
                        cur.execute("""
                            SELECT policy_type, percentage_impact
                            FROM trade_policies
                            WHERE is_active = TRUE
                              AND LOWER(origin_country) = LOWER(%s)
                              AND (
                                  LOWER(destination_region) = LOWER(%s)
                                  OR LOWER(destination_region) = 'global'
                              )
                              AND (
                                  LOWER(material_category) = LOWER(%s)
                                  OR LOWER(material_category) = 'general'
                              )
                            ORDER BY ABS(percentage_impact) DESC
                        """, (origin, dest, mat))
                        policies = cur.fetchall()

                        total = sum(float(p["percentage_impact"]) for p in policies)
                        has_sanction = any(
                            p["policy_type"] in ("SANCTION", "EXPORT_BAN") for p in policies
                        )
                        worst = policies[0]["policy_type"] if policies else None

                        friction = round(total, 2) if policies else None

                        if has_sanction or (friction or 0) >= 999:
                            geo_status = "SANCTIONED"
                        elif (friction or 0) > 40:
                            geo_status = "TOXIC"
                        elif (friction or 0) > 2:
                            geo_status = "FRICTION"
                        elif (friction or 0) < 0:
                            geo_status = "SUBSIDISED"
                        elif policies:
                            geo_status = "COMPLIANT"
                        else:
                            geo_status = "UNKNOWN"

                        worst_type = worst

                    # Update the edge
                    cur.execute("""
                        UPDATE supply_chain_edges
                        SET geopolitical_friction_cost = %s,
                            geo_policy_type            = %s,
                            geo_status                 = %s,
                            geo_last_evaluated_at      = NOW()
                        WHERE id = %s
                    """, (friction, worst_type, geo_status, edge["id"]))
                    updated += 1

                conn.commit()

        except Exception as e:
            conn.rollback()
            logger.error(f"evaluate_geopolitical_friction failed: {e}")
        finally:
            conn.close()

        logger.info(f"evaluate_geopolitical_friction: {updated} edges evaluated")
        return updated

    async def run_nightly(
        self,
        consumer_tickers: List[str],
        producer_tickers: List[str],
    ) -> Dict[str, Any]:
        """
        Full nightly pipeline:
        1. Analyze all manufacturers (Prompt 1)
        2. Analyze all miners (Prompt 2)
        3. Cross-reference for CONFIRMED_NAME edges
        """
        logger.info(
            f"NexusEngine nightly run: {len(consumer_tickers)} manufacturers, "
            f"{len(producer_tickers)} miners"
        )

        # Run analyses concurrently in bounded batches of 5
        async def batch(coros, size=5):
            results = []
            for i in range(0, len(coros), size):
                chunk = await asyncio.gather(*coros[i:i+size], return_exceptions=True)
                results.extend(chunk)
            return results

        manufacturer_results = await batch(
            [self.analyze_manufacturer(t) for t in consumer_tickers]
        )
        miner_results = await batch(
            [self.analyze_miner(t) for t in producer_tickers]
        )

        loop = asyncio.get_event_loop()
        edges_created = await loop.run_in_executor(None, self.cross_reference_nexus)

        # Seed domicile_country for any new nodes before running geo-friction
        try:
            from scripts.seed_domicile_country import run_seed as seed_domicile
            seed_result = await seed_domicile()
            logger.info(f"Domicile seeder: {seed_result}")
        except Exception as e:
            logger.warning(f"Domicile seeder skipped: {e}")
            seed_result = {}

        geo_edges_updated = await loop.run_in_executor(None, self.evaluate_geopolitical_friction)

        return {
            "manufacturers_analyzed": sum(1 for r in manufacturer_results if r and not isinstance(r, Exception)),
            "miners_analyzed": sum(1 for r in miner_results if r and not isinstance(r, Exception)),
            "confirmed_name_edges_created": edges_created,
            "domicile_countries_seeded": seed_result.get("updated", 0),
            "geo_friction_edges_updated": geo_edges_updated,
        }
