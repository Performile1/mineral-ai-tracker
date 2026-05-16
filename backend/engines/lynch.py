"""
Mineral AI Tracker - Peter Lynch GARP Engine (PRD v8.3)
Version: 8.3
Description: Growth At Reasonable Price with PEG adjusted for production growth
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class LynchResult:
    score: float            # 0-100
    peg_ratio: float
    production_growth_pct: float
    reasoning: str


class LynchEngine:
    """
    Peter Lynch GARP (Growth at Reasonable Price) Engine.

    Adapted for mining: PEG ratio uses **production growth** (oz/ton per year)
    instead of pure earnings growth, since miners can grow output before
    earnings catch up.

    PEG = P/E / (production_growth_pct + earnings_growth_pct)

    Scoring:
    - PEG < 1.0 -> bargain GARP (high score)
    - PEG 1.0-2.0 -> fair
    - PEG > 2.0 -> overpriced for growth
    """

    def score(self, financials: Dict[str, Any]) -> LynchResult:
        pe = financials.get("pe_ratio") or 0.0
        prod_growth = financials.get("production_growth_pct", 0.0)
        eps_growth = financials.get("eps_growth_pct", 0.0)
        combined_growth = prod_growth + eps_growth

        if pe <= 0:
            return LynchResult(
                score=0.0,
                peg_ratio=0.0,
                production_growth_pct=prod_growth,
                reasoning="No P/E available (loss-making or pre-revenue).",
            )

        if combined_growth <= 0:
            return LynchResult(
                score=20.0,
                peg_ratio=999.0,
                production_growth_pct=prod_growth,
                reasoning="No production or earnings growth - skip GARP play.",
            )

        peg = pe / combined_growth

        # Lynch loved PEG < 1
        if peg < 0.5:
            base = 100.0
        elif peg < 1.0:
            base = 85.0
        elif peg < 1.5:
            base = 65.0
        elif peg < 2.0:
            base = 45.0
        elif peg < 3.0:
            base = 25.0
        else:
            base = 10.0

        # Bonus for strong production growth (mining-specific)
        if prod_growth > 30:
            base = min(100.0, base + 10)
        elif prod_growth > 15:
            base = min(100.0, base + 5)

        reasoning = (
            f"PEG: {peg:.2f} (P/E {pe:.1f} / growth {combined_growth:.1f}%). "
            f"Production growth: {prod_growth:.1f}%. GARP score: {base:.1f}."
        )
        return LynchResult(
            score=base,
            peg_ratio=peg,
            production_growth_pct=prod_growth,
            reasoning=reasoning,
        )
