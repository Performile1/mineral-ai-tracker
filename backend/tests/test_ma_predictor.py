"""
Mineral AI Tracker — M&A Predictor Tests (Sprint 20)

Tests the heuristic scoring logic in _call_claude_or_heuristic()
without hitting Claude, FMP, or the database.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# MockFMPProvider — synthetic fundamental data
# ---------------------------------------------------------------------------

class MockFMPProvider:
    """Injects synthetic FMP data without any network calls."""

    def __init__(
        self,
        market_cap: float | None = None,
        debt_to_equity: float | None = None,
        fcf_margin: float | None = None,
    ) -> None:
        self.market_cap = market_cap
        self.debt_to_equity = debt_to_equity
        self.fcf_margin = fcf_margin

    def as_dict(self) -> dict:
        return {
            "market_cap": self.market_cap,
            "debt_to_equity": self.debt_to_equity,
            "fcf_margin": self.fcf_margin,
        }


# ---------------------------------------------------------------------------
# Helper: force the heuristic path by making Claude unavailable
# ---------------------------------------------------------------------------

def _unavailable_claude():
    """Returns a mock Claude client that reports is_available() = False."""
    client = MagicMock()
    client.is_available.return_value = False
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMAHeuristic:
    """Test _call_claude_or_heuristic() heuristic branch."""

    @pytest.mark.asyncio
    async def test_high_dilution_with_top_contracts_base(self):
        """High dilution + TAKE_OR_PAY → base score 85."""
        from agents.ma_predictor import _call_claude_or_heuristic

        fmp = MockFMPProvider(
            market_cap=2_000_000_000.0,
            debt_to_equity=0.5,
            fcf_margin=0.05,
        )
        with patch("ml.claude_client.get_claude_client", return_value=_unavailable_claude()):
            score, reasoning, _ = await _call_claude_or_heuristic(
                prompt="test",
                ticker="MOCK",
                dilution_score=80.0,
                has_top=True,
                fmp_data=fmp.as_dict(),
            )

        assert score == pytest.approx(85.0)
        assert "TAKE_OR_PAY" in reasoning

    @pytest.mark.asyncio
    async def test_high_dilution_with_top_and_microcap_boost(self):
        """High dilution + TOP + micro-cap + over-leveraged → 90 (85+5)."""
        from agents.ma_predictor import _call_claude_or_heuristic

        fmp = MockFMPProvider(
            market_cap=200_000_000.0,
            debt_to_equity=2.0,
            fcf_margin=0.01,
        )
        with patch("ml.claude_client.get_claude_client", return_value=_unavailable_claude()):
            score, reasoning, _ = await _call_claude_or_heuristic(
                prompt="test",
                ticker="MOCK",
                dilution_score=80.0,
                has_top=True,
                fmp_data=fmp.as_dict(),
            )

        assert score == pytest.approx(90.0)
        assert "Micro-cap" in reasoning

    @pytest.mark.asyncio
    async def test_high_dilution_no_top_base(self):
        """High dilution, no TAKE_OR_PAY → base score 45."""
        from agents.ma_predictor import _call_claude_or_heuristic

        fmp = MockFMPProvider(
            market_cap=2_000_000_000.0,
            debt_to_equity=0.3,
            fcf_margin=0.10,
        )
        with patch("ml.claude_client.get_claude_client", return_value=_unavailable_claude()):
            score, reasoning, _ = await _call_claude_or_heuristic(
                prompt="test",
                ticker="MOCK",
                dilution_score=75.0,
                has_top=False,
                fmp_data=fmp.as_dict(),
            )

        assert score == pytest.approx(45.0)
        assert "without contractual protection" in reasoning

    @pytest.mark.asyncio
    async def test_high_dilution_no_top_microcap_boost(self):
        """High dilution + no TOP + micro-cap → 55 (45+10)."""
        from agents.ma_predictor import _call_claude_or_heuristic

        fmp = MockFMPProvider(
            market_cap=300_000_000.0,
            debt_to_equity=0.4,
            fcf_margin=0.0,
        )
        with patch("ml.claude_client.get_claude_client", return_value=_unavailable_claude()):
            score, reasoning, _ = await _call_claude_or_heuristic(
                prompt="test",
                ticker="MOCK",
                dilution_score=75.0,
                has_top=False,
                fmp_data=fmp.as_dict(),
            )

        assert score == pytest.approx(55.0)
        assert "Micro-cap" in reasoning

    @pytest.mark.asyncio
    async def test_microcap_negative_fcf_low_dilution(self):
        """Low dilution but micro-cap with negative FCF → 55 (distressed sale)."""
        from agents.ma_predictor import _call_claude_or_heuristic

        fmp = MockFMPProvider(
            market_cap=100_000_000.0,
            debt_to_equity=1.0,
            fcf_margin=-0.05,
        )
        with patch("ml.claude_client.get_claude_client", return_value=_unavailable_claude()):
            score, reasoning, _ = await _call_claude_or_heuristic(
                prompt="test",
                ticker="MOCK",
                dilution_score=30.0,
                has_top=False,
                fmp_data=fmp.as_dict(),
            )

        assert score == pytest.approx(55.0)
        assert "distressed sale" in reasoning

    @pytest.mark.asyncio
    async def test_low_dilution_no_stress_proportional(self):
        """Low dilution, healthy balance sheet → score = dilution × 0.6."""
        from agents.ma_predictor import _call_claude_or_heuristic

        fmp = MockFMPProvider(
            market_cap=5_000_000_000.0,
            debt_to_equity=0.2,
            fcf_margin=0.15,
        )
        with patch("ml.claude_client.get_claude_client", return_value=_unavailable_claude()):
            score, reasoning, _ = await _call_claude_or_heuristic(
                prompt="test",
                ticker="MOCK",
                dilution_score=40.0,
                has_top=False,
                fmp_data=fmp.as_dict(),
            )

        assert score == pytest.approx(40.0 * 0.6, rel=1e-3)
        assert "Low capital stress" in reasoning

    @pytest.mark.asyncio
    async def test_score_capped_at_97(self):
        """Score can never exceed 97 regardless of boost factors."""
        from agents.ma_predictor import _call_claude_or_heuristic

        fmp = MockFMPProvider(
            market_cap=50_000_000.0,
            debt_to_equity=5.0,
            fcf_margin=-0.20,
        )
        with patch("ml.claude_client.get_claude_client", return_value=_unavailable_claude()):
            score, _, _ = await _call_claude_or_heuristic(
                prompt="test",
                ticker="MOCK",
                dilution_score=99.0,
                has_top=True,
                fmp_data=fmp.as_dict(),
            )

        assert score <= 97.0

    @pytest.mark.asyncio
    async def test_missing_fmp_data_does_not_crash(self):
        """Empty FMP dict (mock mode) still returns a valid score."""
        from agents.ma_predictor import _call_claude_or_heuristic

        with patch("ml.claude_client.get_claude_client", return_value=_unavailable_claude()):
            score, reasoning, _ = await _call_claude_or_heuristic(
                prompt="test",
                ticker="MOCK",
                dilution_score=80.0,
                has_top=True,
                fmp_data={},
            )

        assert 0.0 <= score <= 100.0
        assert isinstance(reasoning, str)
