"""
Mineral AI Tracker — Local Sentiment Crawler (Sprint 16)
=========================================================
Early-warning agent: scans for industrial unrest signals in local languages
BEFORE they escalate into official strikes or production halts.

Domain focus (2026):
  Chile / Copper  (Escondida)  — Spanish keywords:   huelga, sindicato, paralización
  Indonesia / Nickel (Morowali) — Bahasa Indonesia:  mogok kerja, protes pekerja

Signal pipeline:
  1. Fetch signals (mock or live RSS).
  2. Score each signal — if sentiment_score < EARLY_WARNING_THRESHOLD:
       a. Write to labor_disputes  (is_early_warning=TRUE, severity_level=1)
       b. dispatch_risk_alert(category='early_sentiment')
  3. Return list of SentimentEarlyWarning objects.

USE_MOCK_DATA=true  → returns domain-seeded mock signals
USE_MOCK_DATA=false → _fetch_live_signals() placeholder (Phase 3+)
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger

from config import settings
from schemas.omniscient import SentimentEarlyWarning
from utils.database import get_db_connection, release_db_connection

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EARLY_WARNING_THRESHOLD: float = settings.SENTIMENT_EARLY_WARNING_THRESHOLD

# ---------------------------------------------------------------------------
# Keyword sets (for future live RSS scoring)
# ---------------------------------------------------------------------------

CHILE_KEYWORDS = frozenset(
    ["huelga", "sindicato", "paralización", "paro", "protesta laboral"]
)
INDONESIA_KEYWORDS = frozenset(
    ["mogok kerja", "protes pekerja", "aksi buruh", "unjuk rasa"]
)

# Region keywords used to pre-filter RSS headlines before sending to Gemini
REGION_KEYWORDS = frozenset([
    # Chile / copper
    "chile", "escondida", "chuquicamata", "codelco", "antofagasta",
    "copper mine", "mina de cobre", "sindicato", "huelga",
    # Indonesia / nickel
    "indonesia", "morowali", "sulawesi", "nickel mine", "mogok",
    "iwip", "vale indonesia", "trimegah",
    # General mining labour
    "mining strike", "mine workers", "mine protest", "labour dispute",
    "mine union", "workers walk out", "mine shutdown",
])

# Public RSS feeds covering mining / commodity regions (no auth required)
MINING_RSS_FEEDS: List[str] = [
    url.strip()
    for url in settings.SENTIMENT_RSS_FEEDS.split(",")
    if url.strip()
]

_GEMINI_CLASSIFY_PROMPT = """
You are a mining-industry labour-risk analyst.
Below is a numbered list of news headlines. Identify ONLY those that indicate
an active or imminent labour dispute, strike, protest, walkout, or production
halt at a specific mine or smelter.

For each flagged headline return JSON (one object per line, no array wrapper):
{{"headline_index": <int>, "asset_ticker": "<TICKER or UNKNOWN>",
  "facility_name": "<mine name or blank>", "region": "<country/region>",
  "sentiment_score": <float -1.0 to 0.0>, "severity": <1-3>}}

If NO headline indicates a labour dispute, return the single word: NONE

HEADLINES:
{headlines_block}
"""

# ---------------------------------------------------------------------------
# Domain-seeded mock signal library
# ---------------------------------------------------------------------------

_MOCK_SIGNALS: List[Dict[str, Any]] = [
    {
        "asset_ticker": "SCCO",
        "facility_name": "Escondida Mine",
        "region": "Antofagasta, Chile",
        "domicile_country": "CL",
        "language": "es",
        "raw_signal": (
            "Sindicato de Mineros Escondida anuncia paralización de actividades "
            "por 48 horas debido a desacuerdo en negociación colectiva. "
            "La huelga podría afectar la producción de 400,000 toneladas de cobre."
        ),
        "keywords_matched": ["sindicato", "paralización", "huelga"],
        "sentiment_score": -0.72,
        "source_url": "https://mock.mineria.cl/noticias/escondida-huelga-2026",
    },
    {
        "asset_ticker": "VALE",
        "facility_name": "Morowali Industrial Park",
        "region": "Central Sulawesi, Indonesia",
        "domicile_country": "ID",
        "language": "id",
        "raw_signal": (
            "Ribuan buruh Morowali mogok kerja menuntut kenaikan upah dan "
            "perbaikan keselamatan kerja (K3). Protes pekerja ini diperkirakan "
            "berlangsung 3 hari dan dapat menghambat produksi nikel."
        ),
        "keywords_matched": ["mogok kerja", "protes pekerja"],
        "sentiment_score": -0.68,
        "source_url": "https://mock.mediaindonesia.com/morowali-aksi-buruh-2026",
    },
    {
        "asset_ticker": "LTR",
        "facility_name": "Kathleen Valley",
        "region": "Western Australia",
        "domicile_country": "AU",
        "language": "en",
        "raw_signal": (
            "Workers at Kathleen Valley staged a brief protest over accommodation "
            "standards. Management confirmed no production impact."
        ),
        "keywords_matched": ["protest"],
        "sentiment_score": -0.28,
        "source_url": "https://mock.miningweekly.com/kv-workers-2026",
    },
]

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

async def run_sentiment_crawl(
    use_mock: Optional[bool] = None,
) -> List[SentimentEarlyWarning]:
    """
    Sprint 16 — Sentiment Crawler main entry point.

    Evaluates each signal against EARLY_WARNING_THRESHOLD.
    Writes qualifying signals to labor_disputes and dispatches alerts.
    Returns all SentimentEarlyWarning objects that crossed the threshold.
    """
    from api.settings import dispatch_risk_alert

    if use_mock is None:
        use_mock = settings.USE_MOCK_DATA

    raw_signals: List[Dict[str, Any]] = (
        _MOCK_SIGNALS if use_mock else await _fetch_live_signals()
    )

    warnings: List[SentimentEarlyWarning] = []

    for signal in raw_signals:
        score: float = float(signal.get("sentiment_score", 0.0))

        if score >= EARLY_WARNING_THRESHOLD:
            logger.debug(
                f"Sentiment Crawler: {signal['asset_ticker']} score {score:.2f} "
                f"≥ threshold {EARLY_WARNING_THRESHOLD} — below early-warning level"
            )
            continue

        warning = SentimentEarlyWarning(
            asset_ticker=signal["asset_ticker"],
            facility_name=signal.get("facility_name"),
            region=signal.get("region"),
            raw_signal=signal["raw_signal"],
            language_detected=signal.get("language"),
            sentiment_score=score,
            is_early_warning=True,
            severity_level=1,
            source_url=signal.get("source_url"),
        )
        warnings.append(warning)

        await _write_to_labor_disputes(warning)

        # Alert score = absolute sentiment magnitude × 100 (0–100 scale)
        alert_score = min(100.0, abs(score) * 100.0)
        try:
            await dispatch_risk_alert(
                ticker=warning.asset_ticker,
                score=alert_score,
                category="early_sentiment",
            )
            logger.info(
                f"Sentiment Crawler: early_sentiment alert dispatched for "
                f"{warning.asset_ticker} (score={alert_score:.1f})"
            )
        except Exception as exc:
            logger.warning(
                f"Sentiment Crawler: alert dispatch failed for "
                f"{warning.asset_ticker}: {exc}"
            )

    logger.info(
        f"Sentiment Crawler: {len(warnings)}/{len(raw_signals)} signals "
        "crossed early-warning threshold"
    )
    return warnings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _write_to_labor_disputes(warning: SentimentEarlyWarning) -> None:
    """Persist an early-warning signal to the labor_disputes table."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO labor_disputes
                    (asset_ticker, facility_name, region, dispute_type,
                     severity_level, description, is_early_warning,
                     source_url, is_active, triggered_at)
                VALUES (%s, %s, %s, 'NEGOTIATION', %s, %s, %s, %s, TRUE, NOW())
                ON CONFLICT DO NOTHING
                """,
                (
                    warning.asset_ticker,
                    warning.facility_name,
                    warning.region,
                    warning.severity_level,
                    warning.raw_signal[:500],
                    warning.is_early_warning,
                    warning.source_url,
                ),
            )
            conn.commit()
        logger.info(
            f"Sentiment Crawler: early warning written — "
            f"{warning.asset_ticker} [{warning.facility_name}] "
            f"sentiment={warning.sentiment_score:.2f}"
        )
    except Exception as exc:
        conn.rollback()
        logger.error(
            f"Sentiment Crawler: DB write failed for {warning.asset_ticker}: {exc}"
        )
    finally:
        release_db_connection(conn)


async def _fetch_live_signals() -> List[Dict[str, Any]]:
    """
    Sprint 17 — Live RSS ingestion + Gemini Flash batch classification.

    Pipeline:
      1. Fetch all configured RSS feeds in parallel using feedparser.
      2. Pre-filter entries whose title/summary contains a REGION_KEYWORD.
      3. Batch filtered headlines → Gemini Flash for labour-dispute classification.
      4. Parse Gemini JSON lines → SentimentEarlyWarning dicts.
    """
    try:
        import feedparser  # noqa: PLC0415  (optional dep, imported lazily)
    except ImportError:
        logger.warning("Sentiment Crawler: feedparser not installed — pip install feedparser>=6.0.10")
        return []

    loop = asyncio.get_event_loop()

    # -- 1. Parallel RSS fetch (feedparser is sync; run in executor) ----------
    async def _parse_feed(url: str) -> list:
        try:
            feed = await loop.run_in_executor(None, feedparser.parse, url)
            return feed.entries or []
        except Exception as exc:
            logger.warning(f"Sentiment Crawler: RSS fetch failed for {url}: {exc}")
            return []

    all_entries_nested = await asyncio.gather(*[_parse_feed(u) for u in MINING_RSS_FEEDS])
    all_entries = [e for entries in all_entries_nested for e in entries]
    logger.info(f"Sentiment Crawler: {len(all_entries)} total RSS entries fetched")

    # -- 2. Pre-filter by region keywords ------------------------------------
    def _is_relevant(entry: Any) -> bool:
        text = ((entry.get("title") or "") + " " + (entry.get("summary") or "")).lower()
        return any(kw in text for kw in REGION_KEYWORDS)

    relevant = [e for e in all_entries if _is_relevant(e)]
    if not relevant:
        logger.info("Sentiment Crawler: no region-relevant headlines found in RSS feeds")
        return []

    logger.info(f"Sentiment Crawler: {len(relevant)} region-relevant headlines → Gemini batch")

    # -- 3. Gemini Flash batch classification ---------------------------------
    headlines_block = "\n".join(
        f"{i + 1}. {e.get('title', '').strip()}"
        for i, e in enumerate(relevant[:40])  # cap at 40 per call
    )
    prompt = _GEMINI_CLASSIFY_PROMPT.format(headlines_block=headlines_block)

    gemini_text: Optional[str] = None
    try:
        from ml.gemini_client import GeminiClient
        gc = GeminiClient()
        if gc.is_available():
            gemini_text = await gc.generate_flash(prompt)
            logger.info("Sentiment Crawler: Gemini Flash classification complete")
        else:
            logger.warning("Sentiment Crawler: Gemini unavailable — skipping live classification")
            return []
    except Exception as exc:
        logger.error(f"Sentiment Crawler: Gemini call failed: {exc}")
        return []

    if not gemini_text or gemini_text.strip().upper() == "NONE":
        logger.info("Sentiment Crawler: Gemini found no labour disputes in batch")
        return []

    # -- 4. Parse Gemini JSON lines → signal dicts ----------------------------
    signals: List[Dict[str, Any]] = []
    for line in gemini_text.strip().splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            obj = __import__("json").loads(line)
            idx = int(obj.get("headline_index", 1)) - 1
            source_entry = relevant[idx] if 0 <= idx < len(relevant) else {}
            signals.append({
                "asset_ticker": (obj.get("asset_ticker") or "UNKNOWN").upper(),
                "facility_name": obj.get("facility_name") or "",
                "region": obj.get("region") or "",
                "domicile_country": "",
                "language": "en",
                "raw_signal": source_entry.get("title") or "",
                "keywords_matched": [],
                "sentiment_score": max(-1.0, min(0.0, float(obj.get("sentiment_score", -0.6)))),
                "source_url": source_entry.get("link") or "",
            })
        except (ValueError, KeyError, IndexError) as exc:
            logger.debug(f"Sentiment Crawler: failed to parse Gemini line '{line}': {exc}")
            continue

    logger.info(f"Sentiment Crawler: {len(signals)} live signal(s) extracted from Gemini batch")
    return signals
