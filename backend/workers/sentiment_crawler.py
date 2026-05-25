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

import os
from typing import Any, Dict, List, Optional

from loguru import logger

from schemas.omniscient import SentimentEarlyWarning
from utils.database import get_db_connection, release_db_connection

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EARLY_WARNING_THRESHOLD: float = float(
    os.getenv("SENTIMENT_EARLY_WARNING_THRESHOLD", "-0.50")
)

# ---------------------------------------------------------------------------
# Keyword sets (for future live RSS scoring)
# ---------------------------------------------------------------------------

CHILE_KEYWORDS = frozenset(
    ["huelga", "sindicato", "paralización", "paro", "protesta laboral"]
)
INDONESIA_KEYWORDS = frozenset(
    ["mogok kerja", "protes pekerja", "aksi buruh", "unjuk rasa"]
)

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
        use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

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
    Placeholder for live RSS / news-API integration (Phase 3+).
    Will integrate a language-detection + keyword-matching pipeline
    for Spanish (Chile) and Bahasa Indonesia (Morowali/Sulawesi).
    """
    logger.debug(
        "Sentiment Crawler: live signal fetch not yet implemented — "
        "set USE_MOCK_DATA=true for seeded data"
    )
    return []
