"""
Mineral AI Tracker - Buffett Engine (PRD v8.3)
Version: 8.3
Description: Buffett-style quality scoring - Cash Flow, Moat, AISC
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class BuffettResult:
    score: float  # 0-100
    cash_flow_score: float
    moat_score: float
    aisc_score: float
    reasoning: str


class BuffettEngine:
    """
    Buffett Engine: Quality investing based on:
    - Free Cash Flow strength
    - Economic Moat (competitive advantage)
    - AISC (All-In Sustaining Cost) per ounce/ton
    """

    def __init__(self, fcf_weight: float = 0.4, moat_weight: float = 0.3, aisc_weight: float = 0.3):
        self.fcf_weight = fcf_weight
        self.moat_weight = moat_weight
        self.aisc_weight = aisc_weight

    def score(self, financials: Dict[str, Any]) -> BuffettResult:
        """
        Calculate Buffett score (0-100) from financial data.

        Expected keys:
        - free_cash_flow_m (millions USD)
        - revenue_m
        - debt_to_equity
        - aisc_per_oz (or aisc_per_ton)
        - commodity_price (market price)
        - market_cap_m
        """
        fcf = self._score_cash_flow(financials)
        moat = self._score_moat(financials)
        aisc = self._score_aisc(financials)

        total = (
            fcf * self.fcf_weight
            + moat * self.moat_weight
            + aisc * self.aisc_weight
        )
        total = max(0.0, min(100.0, total))

        reasoning = (
            f"FCF: {fcf:.1f} | Moat: {moat:.1f} | AISC margin: {aisc:.1f}. "
            f"Weighted Buffett Score: {total:.1f}."
        )
        return BuffettResult(
            score=total,
            cash_flow_score=fcf,
            moat_score=moat,
            aisc_score=aisc,
            reasoning=reasoning,
        )

    def _score_cash_flow(self, f: Dict[str, Any]) -> float:
        fcf = f.get("free_cash_flow_m") or 0.0
        revenue = f.get("revenue_m") or 0.0
        if revenue <= 0:
            return 0.0
        fcf_margin = fcf / revenue
        # 30% FCF margin = max score
        return max(0.0, min(100.0, (fcf_margin / 0.30) * 100.0))

    def _score_moat(self, f: Dict[str, Any]) -> float:
        # Moat proxy: low debt + high return on capital + size advantage
        de = f.get("debt_to_equity")
        market_cap = f.get("market_cap_m") or 0.0
        score = 50.0
        if de is not None:
            if de < 0.3:
                score += 25
            elif de < 0.6:
                score += 15
            elif de > 1.5:
                score -= 25
        if market_cap > 5000:
            score += 15
        elif market_cap > 1000:
            score += 10
        elif market_cap < 50:
            score -= 15
        return max(0.0, min(100.0, score))

    def _score_aisc(self, f: Dict[str, Any]) -> float:
        # AISC margin: (commodity_price - aisc) / commodity_price
        price = f.get("commodity_price")
        aisc = f.get("aisc_per_oz") or f.get("aisc_per_ton")
        if not price or not aisc or price <= 0:
            return 50.0
        margin = (price - aisc) / price
        # 50% margin = max
        return max(0.0, min(100.0, (margin / 0.50) * 100.0))
