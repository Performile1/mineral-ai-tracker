"""
Mineral AI Tracker — Sentiment Crawler Tests (Sprint 20)

Verifies the early-warning threshold logic using the built-in mock
signal library without touching the database, RSS feeds, or alert pipeline.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

import workers.sentiment_crawler as _sc_module  # noqa: F401 — ensures module cached in sys.modules
from workers.sentiment_crawler import run_sentiment_crawl


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signal(ticker: str, score: float) -> dict:
    """Build a minimal signal dict compatible with run_sentiment_crawl."""
    return {
        "asset_ticker": ticker,
        "facility_name": f"{ticker} Test Mine",
        "region": "Test Region",
        "domicile_country": "XX",
        "language": "en",
        "raw_signal": f"Test signal for {ticker}.",
        "keywords_matched": ["test"],
        "sentiment_score": score,
        "source_url": f"https://mock.test/{ticker.lower()}",
    }


# ---------------------------------------------------------------------------
# Tests — threshold filtering
# ---------------------------------------------------------------------------

class TestEarlyWarningThreshold:
    """Verify that run_sentiment_crawl filters signals correctly."""

    @pytest.mark.asyncio
    async def test_below_threshold_is_flagged(self):
        """Signal with score below -0.50 must become an early warning."""
        signals = [_make_signal("SCCO", -0.72)]

        with (
            patch("workers.sentiment_crawler._MOCK_SIGNALS", signals),
            patch("workers.sentiment_crawler._write_to_labor_disputes", new_callable=AsyncMock),
            patch("api.settings.dispatch_risk_alert", new_callable=AsyncMock),
        ):
            results = await run_sentiment_crawl(use_mock=True)

        assert len(results) == 1
        assert results[0].asset_ticker == "SCCO"
        assert results[0].is_early_warning is True

    @pytest.mark.asyncio
    async def test_above_threshold_not_flagged(self):
        """Signal with score above -0.50 (mild) must be filtered out."""
        signals = [_make_signal("LTR", -0.28)]

        with (
            patch("workers.sentiment_crawler._MOCK_SIGNALS", signals),
            patch("workers.sentiment_crawler._write_to_labor_disputes", new_callable=AsyncMock),
            patch("api.settings.dispatch_risk_alert", new_callable=AsyncMock),
        ):
            results = await run_sentiment_crawl(use_mock=True)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_exactly_at_threshold_not_flagged(self):
        """Score exactly equal to threshold must NOT trigger (strict <)."""
        signals = [_make_signal("TEST", -0.50)]

        with (
            patch("workers.sentiment_crawler._MOCK_SIGNALS", signals),
            patch("workers.sentiment_crawler._write_to_labor_disputes", new_callable=AsyncMock),
            patch("api.settings.dispatch_risk_alert", new_callable=AsyncMock),
        ):
            results = await run_sentiment_crawl(use_mock=True)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_mixed_signals_only_flagged_cross_threshold(self):
        """Mixed batch: only signals below -0.50 are returned."""
        signals = [
            _make_signal("SCCO", -0.72),
            _make_signal("VALE", -0.68),
            _make_signal("LTR",  -0.28),
        ]

        with (
            patch("workers.sentiment_crawler._MOCK_SIGNALS", signals),
            patch("workers.sentiment_crawler._write_to_labor_disputes", new_callable=AsyncMock),
            patch("api.settings.dispatch_risk_alert", new_callable=AsyncMock),
        ):
            results = await run_sentiment_crawl(use_mock=True)

        assert len(results) == 2
        tickers = {r.asset_ticker for r in results}
        assert tickers == {"SCCO", "VALE"}

    @pytest.mark.asyncio
    async def test_builtin_mock_signals_produce_two_warnings(self):
        """The built-in _MOCK_SIGNALS library (SCCO + VALE flagged, LTR not)."""
        with (
            patch("workers.sentiment_crawler._write_to_labor_disputes", new_callable=AsyncMock),
            patch("api.settings.dispatch_risk_alert", new_callable=AsyncMock),
        ):
            results = await run_sentiment_crawl(use_mock=True)

        assert len(results) == 2
        tickers = {r.asset_ticker for r in results}
        assert "LTR" not in tickers

    @pytest.mark.asyncio
    async def test_alert_dispatched_for_each_warning(self):
        """dispatch_risk_alert must be called once per flagged signal."""
        signals = [
            _make_signal("SCCO", -0.72),
            _make_signal("VALE", -0.68),
        ]
        mock_dispatch = AsyncMock()

        with (
            patch("workers.sentiment_crawler._MOCK_SIGNALS", signals),
            patch("workers.sentiment_crawler._write_to_labor_disputes", new_callable=AsyncMock),
            patch("api.settings.dispatch_risk_alert", mock_dispatch),
        ):
            await run_sentiment_crawl(use_mock=True)

        assert mock_dispatch.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_signal_list_returns_empty(self):
        """No signals → no warnings, no crashes."""
        with (
            patch("workers.sentiment_crawler._MOCK_SIGNALS", []),
            patch("workers.sentiment_crawler._write_to_labor_disputes", new_callable=AsyncMock),
            patch("api.settings.dispatch_risk_alert", new_callable=AsyncMock),
        ):
            results = await run_sentiment_crawl(use_mock=True)

        assert results == []

    def test_threshold_comes_from_settings(self):
        """EARLY_WARNING_THRESHOLD must be driven by settings, not hardcoded."""
        from config import settings

        assert _sc_module.EARLY_WARNING_THRESHOLD == settings.SENTIMENT_EARLY_WARNING_THRESHOLD

    def test_rss_feeds_come_from_settings(self):
        """MINING_RSS_FEEDS must be populated from settings.SENTIMENT_RSS_FEEDS."""
        from config import settings

        expected = [u.strip() for u in settings.SENTIMENT_RSS_FEEDS.split(",") if u.strip()]
        assert _sc_module.MINING_RSS_FEEDS == expected
