"""
Mineral AI Tracker — Sovereign M&A Predictor (Sprint 16)
=========================================================
AI-powered agent that estimates buyout probability for PRODUCER nodes.

Logic:
  Input  : dilution_risk_score (from _meta), domicile_country, TAKE_OR_PAY edges
  Output : buyout_probability_score (0–100) → saved to supply_chain_nodes

Claude is called when available; a transparent heuristic fallback is used
in dev/mock environments so the pipeline never stalls.

Heuristic:
  High dilution + active TAKE_OR_PAY contracts → ~85 (strategic asset + distress)
  High dilution, no contracts               → ~45 (distressed but no moat)
  Low dilution                              → dilution_score × 0.6
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from psycopg2.extras import RealDictCursor

from config import settings
from schemas.omniscient import BuyoutPrediction
from utils.database import get_db_connection, release_db_connection
from utils.fmp_client import fetch_fmp_fundamentals, format_fmp_for_prompt

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DILUTION_RISK_HIGH_THRESHOLD: float = 70.0
SCORE_HIGH_DILUTION_WITH_TOP: float = 85.0
SCORE_HIGH_DILUTION_NO_TOP: float = 45.0
SMALL_CAP_THRESHOLD_USD: float = settings.MA_SMALL_CAP_THRESHOLD_USD  # default $500M

_MA_PROMPT = """SYSTEM INSTRUCTION: SOVEREIGN M&A PROBABILITY ASSESSOR

You are a mergers-and-acquisitions analyst specialising in critical mineral supply chains.
Evaluate whether the junior mining company below is a prime acquisition target.

COMPANY DATA:
- Ticker: {ticker}
- Domicile Country: {domicile_country}
- Dilution Risk Score: {dilution_risk_score}/100  (higher = more capital-stressed)
- Active TAKE_OR_PAY Contracts: {take_or_pay_count}
- Contract Detail: {contract_details}

FINANCIAL FUNDAMENTALS (FMP live data):
{fmp_block}

EVALUATION RULES:
1. A dilution risk score > 70 signals the company needs capital — making it vulnerable to acquisition offers.
2. Active TAKE_OR_PAY contracts with major manufacturers are a STRATEGIC ASSET that attracts industrial buyers.
3. A miner in a politically stable country (AU, CA, FI, SE, NO) commands a Western-buyer premium.
4. A miner in a geopolitically stressed country (RU, CN, MM, CD) may attract a state-owned enterprise bid.
5. If both dilution risk > 70 AND take-or-pay contracts exist, score should be 80–90.
6. A market cap BELOW $500M USD combined with high debt/equity (>1.5) signals a distressed micro-cap — prime LBO or strategic buyout target.
7. Negative or very low FCF margin (<0%) with active contracts signals urgent need for a partner/acquirer.

OUTPUT (strict JSON only — no prose, no markdown):
{{
  "buyout_probability_score": <integer 0-100>,
  "reasoning": "<one concise sentence>",
  "geopolitical_context": "<strategic relevance of the domicile country>"
}}"""


# ---------------------------------------------------------------------------
# Agent — single-node evaluation
# ---------------------------------------------------------------------------

async def evaluate_buyout_probability(
    ticker: str,
) -> Optional[BuyoutPrediction]:
    """
    Sprint 16 — evaluate buyout probability for one ticker.

    1. Load node context (dilution_risk_score, domicile_country).
    2. Load active TAKE_OR_PAY edges.
    3. Call Claude; fall back to heuristic if unavailable.
    4. Persist score to supply_chain_nodes.buyout_probability_score.
    Returns BuyoutPrediction or None if the node is not found.
    """
    node_ctx = await _load_node_context(ticker)
    if node_ctx is None:
        logger.warning(f"M&A Predictor: node {ticker} not in supply_chain_nodes — skip")
        return None

    top_edges = await _load_take_or_pay_edges(ticker)
    dilution_score: float = node_ctx.get("dilution_risk_score") or 50.0
    domicile: str = node_ctx.get("domicile_country") or "Unknown"

    contract_details = "; ".join(
        f"{e['downstream_ticker']} ({e.get('raw_material_type', 'N/A')}, "
        f"{e.get('contract_volume_numeric') or 'vol N/A'}t)"
        for e in top_edges[:5]
    ) or "None"

    use_live = not settings.USE_MOCK_DATA
    fmp_data = await _load_fmp_data(ticker) if use_live else {}
    fmp_block = format_fmp_for_prompt(fmp_data) if fmp_data else "[FMP unavailable in mock mode]"

    prompt = _MA_PROMPT.format(
        ticker=ticker,
        domicile_country=domicile,
        dilution_risk_score=round(dilution_score, 1),
        take_or_pay_count=len(top_edges),
        contract_details=contract_details,
        fmp_block=fmp_block,
    )

    score, reasoning, geo_ctx = await _call_claude_or_heuristic(
        prompt=prompt,
        ticker=ticker,
        dilution_score=dilution_score,
        has_top=len(top_edges) > 0,
        fmp_data=fmp_data,
    )

    prediction = BuyoutPrediction(
        ticker=ticker,
        buyout_probability_score=round(score, 2),
        reasoning=reasoning,
        geopolitical_context=geo_ctx,
        computed_at=datetime.now(timezone.utc),
    )

    await _save_prediction(ticker, prediction.buyout_probability_score)
    return prediction


# ---------------------------------------------------------------------------
# Agent — full PRODUCER sweep (called by scheduler)
# ---------------------------------------------------------------------------

async def run_ma_predictor_sweep() -> List[BuyoutPrediction]:
    """
    Evaluate buyout probability for every PRODUCER node.
    Intended for the nightly APScheduler omniscient pipeline.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT asset_ticker FROM supply_chain_nodes WHERE company_type = 'PRODUCER'"
            )
            tickers = [r["asset_ticker"] for r in cur.fetchall()]
    finally:
        release_db_connection(conn)

    results: List[BuyoutPrediction] = []
    for ticker in tickers:
        try:
            pred = await evaluate_buyout_probability(ticker)
            if pred:
                results.append(pred)
        except Exception as exc:
            logger.error(f"M&A Predictor: sweep error for {ticker}: {exc}")

    logger.info(
        f"M&A Predictor sweep complete: {len(results)}/{len(tickers)} evaluated"
    )
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _load_node_context(ticker: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT domicile_country, extracted_data
                FROM supply_chain_nodes
                WHERE asset_ticker = %s
                """,
                (ticker,),
            )
            row = cur.fetchone()
    finally:
        release_db_connection(conn)

    if not row:
        return None

    extracted: Dict[str, Any] = dict(row.get("extracted_data") or {})
    meta: Dict[str, Any] = extracted.get("_meta") or {}
    return {
        "domicile_country": row["domicile_country"],
        "dilution_risk_score": meta.get("dilution_risk_score"),
    }


async def _load_take_or_pay_edges(ticker: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT upstream_ticker, downstream_ticker,
                       raw_material_type, contract_volume_numeric,
                       contract_expiry_date
                FROM supply_chain_edges
                WHERE (upstream_ticker = %s OR downstream_ticker = %s)
                  AND contract_type = 'TAKE_OR_PAY'
                  AND (contract_expiry_date IS NULL
                       OR contract_expiry_date >= CURRENT_DATE)
                """,
                (ticker, ticker),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_db_connection(conn)


async def _load_fmp_data(ticker: str) -> dict:
    """Fetch FMP fundamentals; returns {} silently on any error."""
    try:
        return await fetch_fmp_fundamentals(ticker)
    except Exception as exc:
        logger.warning(f"M&A Predictor: FMP fetch failed for {ticker}: {exc}")
        return {}


async def _call_claude_or_heuristic(
    prompt: str,
    ticker: str,
    dilution_score: float,
    has_top: bool,
    fmp_data: dict | None = None,
) -> tuple[float, str, str]:
    """
    Returns (score, reasoning, geo_context).
    Tries Claude first; falls back to the transparent heuristic.
    """
    try:
        from ml.claude_client import get_claude_client

        client = get_claude_client()
        if client and client.is_available():
            response = await client.generate(
                prompt=prompt, max_tokens=256, temperature=0.2
            )
            raw_text: str = (
                response.get("text", "") if isinstance(response, dict) else str(response)
            )
            json_match = re.search(r"\{.*?\}", raw_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                raw_score = float(parsed.get("buyout_probability_score", 50))
                score = max(0.0, min(100.0, raw_score))
                reasoning = str(parsed.get("reasoning", ""))
                geo_ctx = str(parsed.get("geopolitical_context", ""))
                logger.info(
                    f"M&A Predictor [{ticker}]: Claude score={score:.1f} — {reasoning}"
                )
                return score, reasoning, geo_ctx
    except Exception as exc:
        logger.warning(
            f"M&A Predictor: Claude call failed for {ticker}: {exc} — using heuristic"
        )

    # ---- Heuristic fallback -------------------------------------------------
    fmp_data = fmp_data or {}
    market_cap = fmp_data.get("market_cap")
    debt_to_equity = fmp_data.get("debt_to_equity")
    fcf_margin = fmp_data.get("fcf_margin")
    is_micro_cap = market_cap is not None and market_cap < SMALL_CAP_THRESHOLD_USD
    is_over_leveraged = debt_to_equity is not None and debt_to_equity > 1.5
    is_fcf_negative = fcf_margin is not None and fcf_margin < 0.0

    if dilution_score >= DILUTION_RISK_HIGH_THRESHOLD and has_top:
        base = SCORE_HIGH_DILUTION_WITH_TOP
        boost = 5.0 if (is_micro_cap and is_over_leveraged) else 0.0
        score = min(97.0, base + boost)
        reasoning = (
            f"High dilution risk ({dilution_score:.1f}) + active TAKE_OR_PAY "
            "contracts signal distressed but strategically valuable asset."
            + (f" Micro-cap (${market_cap:,.0f}) + D/E {debt_to_equity:.2f} amplifies urgency." if boost else "")
        )
    elif dilution_score >= DILUTION_RISK_HIGH_THRESHOLD:
        base = SCORE_HIGH_DILUTION_NO_TOP
        boost = 10.0 if is_micro_cap else 0.0
        score = min(75.0, base + boost)
        reasoning = (
            f"High dilution risk ({dilution_score:.1f}) without contractual protection."
            + (f" Micro-cap (${market_cap:,.0f}) makes it an easier opportunistic target." if boost else "")
        )
    elif is_micro_cap and is_fcf_negative:
        score = 55.0
        reasoning = (
            f"Low dilution score but micro-cap (${market_cap:,.0f}) with negative FCF — "
            "financially fragile, potential distressed sale candidate."
        )
    else:
        score = round(dilution_score * 0.6, 2)
        reasoning = f"Low capital stress ({dilution_score:.1f}) — not an immediate target."

    logger.info(f"M&A Predictor [{ticker}]: heuristic score={score:.1f} — {reasoning}")
    return score, reasoning, ""


async def _save_prediction(ticker: str, score: float) -> None:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE supply_chain_nodes
                SET buyout_probability_score = %s
                WHERE asset_ticker = %s
                """,
                (score, ticker),
            )
            conn.commit()
        logger.info(
            f"M&A Predictor [{ticker}]: buyout_probability_score = {score:.1f} persisted"
        )
    except Exception as exc:
        conn.rollback()
        logger.error(f"M&A Predictor: DB write failed for {ticker}: {exc}")
    finally:
        release_db_connection(conn)
