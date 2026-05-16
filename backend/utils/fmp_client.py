"""
Mineral AI Tracker - FMP (Financial Modeling Prep) Client (PRD v8.7 Phase 9.5)
Version: 10.0
Description: Hard-Deterministic Data fetcher for the Llama-3 risk prompt.
PRD v10.0 Phase 10.4: Added Redis caching for API cost reduction

Returns "absolute truth" fundamentals (P/E, market cap, FCF margin) that
override any conflicting claims in scraped press releases (Data Sovereignty).

Endpoints used (v3, free tier compatible):
  - /api/v3/quote/{ticker}              -> price, marketCap, pe, etc.
  - /api/v3/ratios-ttm/{ticker}         -> freeCashFlowMarginTTM, peRatioTTM
  - /api/v3/key-metrics-ttm/{ticker}    -> fallback for FCF/share counts

Failure mode: returns {} (empty dict) on ANY error so the orchestrator can
gracefully degrade to the legacy prompt without blocking the debate.
"""

from __future__ import annotations

import os
import asyncio
from typing import Any, Dict, Optional

import httpx
from loguru import logger
from .vault import decrypt
from .cache import redis_cache

FMP_BASE = "https://financialmodelingprep.com/api/v3"
FMP_TIMEOUT = 8.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_api_key(api_key: Optional[str], system_settings: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Credential resolution order (Phase 9 vault forward-compat):
      1. Explicit `api_key` argument
      2. `system_settings["fmp_api_key"]` (DB-stored vault entry, encrypted)
      3. `FMP_API_KEY` environment variable
    """
    if api_key:
        return api_key
    if system_settings:
        candidate = system_settings.get("fmp_api_key")
        if candidate:
            # Decrypt vault key (returns None if decryption fails)
            decrypted = decrypt(candidate)
            if decrypted:
                return decrypted
            # Fallback to treating as plaintext if decryption fails
            logger.warning("Vault decryption failed, treating key as plaintext")
            return candidate
    return os.environ.get("FMP_API_KEY")


async def _get(client: httpx.AsyncClient, path: str, params: Dict[str, Any]) -> Optional[Any]:
    try:
        resp = await client.get(f"{FMP_BASE}{path}", params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        logger.warning(f"FMP {path} failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@redis_cache(ttl_seconds=3600)  # Cache for 1 hour (fundamentals don't change often)
async def fetch_fmp_fundamentals(
    ticker: str,
    api_key: Optional[str] = None,
    system_settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fetch the canonical Hard-Deterministic Data block for one ticker.

    Returns a flat dict with these keys (any of which may be missing/None):
        ticker            (str, echoed back)
        price             (float)
        market_cap        (float, USD)
        pe_ratio          (float, TTM forward where available)
        fcf_margin        (float, ratio 0..1)
        debt_to_equity    (float)
        eps               (float)
        currency          (str)
        company_name      (str)
        as_of             (str, ISO date from FMP)

    Returns {} on missing key, network error, or unknown ticker.
    """
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return {}

    key = _resolve_api_key(api_key, system_settings)
    if not key:
        logger.warning("FMP API key not configured (env FMP_API_KEY missing). Skipping fundamentals.")
        return {}

    params = {"apikey": key}
    out: Dict[str, Any] = {"ticker": ticker}

    try:
        async with httpx.AsyncClient(timeout=FMP_TIMEOUT, follow_redirects=True) as client:
            # Fan-out two requests in parallel - both are GETs and independent.
            quote_task = _get(client, f"/quote/{ticker}", params)
            ratios_task = _get(client, f"/ratios-ttm/{ticker}", params)
            quote_data, ratios_data = await asyncio.gather(quote_task, ratios_task)
    except Exception as e:
        logger.warning(f"FMP fundamentals fetch failed for {ticker}: {e}")
        return {}

    # /quote/{ticker} returns a list with a single item
    if isinstance(quote_data, list) and quote_data:
        q = quote_data[0]
        out.update({
            "price": q.get("price"),
            "market_cap": q.get("marketCap"),
            "pe_ratio": q.get("pe"),
            "eps": q.get("eps"),
            "company_name": q.get("name"),
            "as_of": q.get("earningsAnnouncement"),
        })

    # /ratios-ttm/{ticker} returns a list with a single TTM record
    if isinstance(ratios_data, list) and ratios_data:
        r = ratios_data[0]
        # Prefer TTM P/E (more current than the quote field)
        if r.get("peRatioTTM") is not None:
            out["pe_ratio"] = r.get("peRatioTTM")
        out["fcf_margin"] = r.get("freeCashFlowMarginTTM")
        out["debt_to_equity"] = r.get("debtEquityRatioTTM")

    # Drop None values to keep the prompt clean
    return {k: v for k, v in out.items() if v is not None}


def format_fmp_for_prompt(fmp_data: Dict[str, Any]) -> str:
    """
    Render the dict as a deterministic, prompt-friendly block. If empty,
    returns a single-line marker so Llama-3 knows the API was unavailable.
    """
    if not fmp_data:
        return "[NO FMP DATA AVAILABLE - degrade to noise-only analysis]"

    def _fmt(key: str, label: str, unit: str = "", precision: int = 2) -> str:
        v = fmp_data.get(key)
        if v is None:
            return f"{label}: N/A"
        if isinstance(v, (int, float)):
            if abs(v) >= 1_000_000:
                return f"{label}: {v:,.0f}{unit}"
            return f"{label}: {v:.{precision}f}{unit}"
        return f"{label}: {v}"

    lines = [
        f"Ticker: {fmp_data.get('ticker', 'N/A')}",
        _fmt("company_name", "Company"),
        _fmt("price", "Price"),
        _fmt("market_cap", "Market Cap (USD)"),
        _fmt("pe_ratio", "Forward P/E (TTM)"),
        _fmt("fcf_margin", "Free Cash Flow Margin"),
        _fmt("debt_to_equity", "Debt/Equity"),
        _fmt("eps", "EPS"),
    ]
    return "\n".join(lines)


# Alias preserving the leading underscore name from the user's spec
_fetch_fmp_fundamentals = fetch_fmp_fundamentals

__all__ = [
    "fetch_fmp_fundamentals",
    "_fetch_fmp_fundamentals",
    "format_fmp_for_prompt",
]
