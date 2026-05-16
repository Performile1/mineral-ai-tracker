"""
Mineral AI Tracker - Institutional Alpha Engine (PRD v8.3)
Version: 8.3
Description: M&A "Nearology", Insider Clusters, Unusual Options Activity
"""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class InstitutionalAlphaResult:
    score: float                    # 0-100
    nearology_score: float
    insider_cluster_score: float
    unusual_options_score: float
    signals: List[str]
    reasoning: str


class InstitutionalAlphaEngine:
    """
    Institutional Alpha Engine.

    Detects "smart money" footprints before broad market sees them:

    1. **Nearology**: Small co (<10% market cap of nearby major) sitting next
       to a producing mine. Classic M&A take-out candidate.

    2. **Insider Clusters**: 3+ insiders buying within 30 days = strong signal.

    3. **Unusual Options Activity (UOA)**: Call volume > 3x average open
       interest with short DTE = whale positioning / squeeze setup.
    """

    def score(self, ctx: Dict[str, Any]) -> InstitutionalAlphaResult:
        signals: List[str] = []

        nearology = self._nearology_score(ctx, signals)
        insiders = self._insider_cluster_score(ctx, signals)
        options = self._unusual_options_score(ctx, signals)

        # Weighted: nearology 40%, insiders 35%, options 25%
        total = nearology * 0.40 + insiders * 0.35 + options * 0.25
        total = max(0.0, min(100.0, total))

        reasoning = (
            f"Nearology: {nearology:.1f} | Insider cluster: {insiders:.1f} | "
            f"UOA: {options:.1f}. Institutional Alpha: {total:.1f}. "
            f"Signals: {', '.join(signals) if signals else 'none'}."
        )
        return InstitutionalAlphaResult(
            score=total,
            nearology_score=nearology,
            insider_cluster_score=insiders,
            unusual_options_score=options,
            signals=signals,
            reasoning=reasoning,
        )

    def _nearology_score(self, ctx: Dict[str, Any], signals: List[str]) -> float:
        target_mcap = ctx.get("market_cap_m", 0.0)
        neighbor_mcap = ctx.get("nearest_major_market_cap_m", 0.0)
        distance_km = ctx.get("distance_to_major_km", 9999.0)

        if neighbor_mcap <= 0 or target_mcap <= 0:
            return 0.0

        ratio = target_mcap / neighbor_mcap
        if ratio >= 0.10:
            return 20.0

        # Sweet spot: small target near a major
        if distance_km < 25:
            signals.append(f"Nearology: <25km from major, ratio {ratio:.2%}")
            return 95.0
        if distance_km < 50:
            signals.append(f"Nearology: <50km from major, ratio {ratio:.2%}")
            return 80.0
        if distance_km < 100:
            return 55.0
        return 20.0

    def _insider_cluster_score(self, ctx: Dict[str, Any], signals: List[str]) -> float:
        purchases = ctx.get("insider_purchases_30d", [])
        if not purchases:
            return 30.0

        unique_buyers = len({p.get("name") for p in purchases if isinstance(p, dict)})
        total_value = sum(
            (p.get("value_usd", 0) for p in purchases if isinstance(p, dict)),
            start=0,
        )

        score = 30.0
        if unique_buyers >= 5:
            score = 95.0
            signals.append(f"Insider cluster: {unique_buyers} buyers, ${total_value:,.0f}")
        elif unique_buyers >= 3:
            score = 80.0
            signals.append(f"Insider cluster: {unique_buyers} buyers")
        elif unique_buyers >= 2:
            score = 60.0
        elif unique_buyers == 1 and total_value > 250_000:
            score = 55.0
            signals.append("Large single insider buy")

        return score

    def _unusual_options_score(self, ctx: Dict[str, Any], signals: List[str]) -> float:
        call_volume = ctx.get("call_volume", 0)
        avg_oi = ctx.get("avg_open_interest", 0)
        days_to_expiry = ctx.get("days_to_expiry", 30)

        if avg_oi <= 0:
            return 30.0

        vol_oi_ratio = call_volume / avg_oi

        score = 30.0
        if vol_oi_ratio >= 5.0 and days_to_expiry < 45:
            score = 95.0
            signals.append(f"UOA: {vol_oi_ratio:.1f}x OI, {days_to_expiry}d to expiry")
        elif vol_oi_ratio >= 3.0:
            score = 75.0
            signals.append(f"UOA: {vol_oi_ratio:.1f}x OI")
        elif vol_oi_ratio >= 2.0:
            score = 55.0

        return score
