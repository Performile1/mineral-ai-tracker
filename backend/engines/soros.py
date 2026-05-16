"""
Mineral AI Tracker - Soros Macro Engine (PRD v8.3)
Version: 8.3
Description: Shorting radar - oversupply, PR-fluff, strong DXY signals
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class SorosResult:
    score: float          # -100 (strong short) to +100 (strong long)
    direction: str        # LONG, SHORT, NEUTRAL
    dxy_signal: str
    supply_signal: str
    pr_fluff_score: float
    reasoning: str


class SorosEngine:
    """
    Soros Macro Engine: Reflexivity-based shorting/long signals.

    Bearish triggers:
    - Strong DXY (>105) crushes commodities
    - Oversupply in commodity (inventory build-up)
    - PR fluff (press releases without substance)
    - Falling 10y rates while commodity prices fall

    Bullish triggers:
    - DXY weakening (<100)
    - Supply deficit
    - Real fundamental news
    """

    PR_FLUFF_KEYWORDS = [
        "exciting", "unprecedented", "world-class",
        "game-changer", "transformational", "company-making",
        "leading", "premier", "next big",
    ]

    def score(self, ctx: Dict[str, Any]) -> SorosResult:
        dxy = ctx.get("dxy", 100.0)
        dxy_signal, dxy_score = self._dxy_signal(dxy)

        supply_balance = ctx.get("supply_balance_pct", 0.0)  # positive = surplus
        supply_signal, supply_score = self._supply_signal(supply_balance)

        recent_pr = ctx.get("recent_press_releases", [])
        pr_fluff = self._pr_fluff_score(recent_pr)

        # Combine - high fluff and surplus = short signal
        total = dxy_score + supply_score - (pr_fluff * 0.5)
        total = max(-100.0, min(100.0, total))

        if total < -40:
            direction = "SHORT"
        elif total > 40:
            direction = "LONG"
        else:
            direction = "NEUTRAL"

        reasoning = (
            f"DXY {dxy:.1f} ({dxy_signal}) | Supply: {supply_signal} | "
            f"PR fluff: {pr_fluff:.1f}/100. Net Soros Score: {total:.1f}."
        )
        return SorosResult(
            score=total,
            direction=direction,
            dxy_signal=dxy_signal,
            supply_signal=supply_signal,
            pr_fluff_score=pr_fluff,
            reasoning=reasoning,
        )

    def _dxy_signal(self, dxy: float) -> tuple[str, float]:
        if dxy >= 107:
            return ("STRONG_DOLLAR_BEARISH", -50)
        if dxy >= 103:
            return ("DOLLAR_BEARISH", -25)
        if dxy <= 95:
            return ("WEAK_DOLLAR_BULLISH", 40)
        if dxy <= 100:
            return ("DOLLAR_BULLISH", 20)
        return ("NEUTRAL", 0)

    def _supply_signal(self, balance_pct: float) -> tuple[str, float]:
        if balance_pct > 10:
            return ("OVERSUPPLY", -40)
        if balance_pct > 3:
            return ("MILD_SURPLUS", -15)
        if balance_pct < -10:
            return ("DEFICIT", 40)
        if balance_pct < -3:
            return ("MILD_DEFICIT", 20)
        return ("BALANCED", 0)

    def _pr_fluff_score(self, releases) -> float:
        """Higher = more fluffy/promotional language = bearish"""
        if not releases:
            return 0.0
        hits = 0
        total_words = 0
        for r in releases:
            text = (r.get("text") if isinstance(r, dict) else str(r)).lower()
            total_words += max(1, len(text.split()))
            for kw in self.PR_FLUFF_KEYWORDS:
                hits += text.count(kw)
        density = (hits / total_words) * 1000
        return min(100.0, density * 20)
