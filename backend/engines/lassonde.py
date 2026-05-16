"""
Mineral AI Tracker - Lassonde Curve Engine (PRD v8.3)
Version: 8.3
Description: Asymmetric entries during "The Orphan Period" (proven discovery, dead hype)
"""

from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum


class LassondePhase(Enum):
    DISCOVERY = "discovery"          # Hype peak after first find
    ORPHAN = "orphan"                # The sweet spot - hype dead, value building
    FEASIBILITY = "feasibility"      # PEA/PFS/FS rebuilding interest
    CONSTRUCTION = "construction"    # Capex heavy, sentiment recovering
    PRODUCTION = "production"        # Cash flow phase

    def opportunity_weight(self) -> float:
        return {
            "discovery": 0.2,
            "orphan": 1.0,        # Maximum asymmetric upside
            "feasibility": 0.7,
            "construction": 0.4,
            "production": 0.3,
        }[self.value]


@dataclass
class LassondeResult:
    score: float           # 0-100
    phase: LassondePhase
    asymmetry_ratio: float # potential upside / downside
    reasoning: str


class LassondeEngine:
    """
    Detects The Orphan Period - the sentiment trough between
    discovery hype and re-rating on construction.

    Key signals:
    - Resource defined (Indicated/Measured) but no recent news
    - Stock price well below ATH (drawdown > 60%)
    - Volume drying up (low retail interest)
    """

    def score(self, project: Dict[str, Any]) -> LassondeResult:
        phase = self._detect_phase(project)
        drawdown = project.get("drawdown_from_ath_pct", 0.0)
        resource_quality = self._resource_quality(project)

        # Asymmetry: deep drawdown + good resources = orphan opportunity
        asymmetry = (drawdown / 100.0) * (resource_quality / 100.0) * phase.opportunity_weight()
        asymmetry_ratio = max(0.0, min(10.0, asymmetry * 10))

        # Score combines phase weight and asymmetry
        score = phase.opportunity_weight() * 100 * (resource_quality / 100.0)
        if phase == LassondePhase.ORPHAN and drawdown > 60:
            score = min(100.0, score * 1.3)

        score = max(0.0, min(100.0, score))

        reasoning = (
            f"Phase: {phase.value} | Drawdown: {drawdown:.1f}% | "
            f"Resource quality: {resource_quality:.1f} | "
            f"Asymmetry ratio: {asymmetry_ratio:.2f}x."
        )
        return LassondeResult(
            score=score,
            phase=phase,
            asymmetry_ratio=asymmetry_ratio,
            reasoning=reasoning,
        )

    def _detect_phase(self, p: Dict[str, Any]) -> LassondePhase:
        status = (p.get("project_status") or "").lower()
        if "production" in status:
            return LassondePhase.PRODUCTION
        if "construction" in status:
            return LassondePhase.CONSTRUCTION
        if "feasibility" in status or "pfs" in status or "pea" in status:
            return LassondePhase.FEASIBILITY
        # Heuristic for orphan: indicated/measured resource with low volume
        category = (p.get("resource_category") or "").lower()
        avg_vol_k = p.get("avg_daily_volume_k", 0)
        if category in ("indicated", "measured", "reserve") and avg_vol_k < 1000:
            return LassondePhase.ORPHAN
        return LassondePhase.DISCOVERY

    def _resource_quality(self, p: Dict[str, Any]) -> float:
        category = (p.get("resource_category") or "").lower()
        cat_weight = {
            "inferred": 30.0,
            "indicated": 60.0,
            "measured": 85.0,
            "reserve": 100.0,
            "proven": 100.0,
            "probable": 75.0,
        }.get(category, 40.0)
        tonnage = p.get("tonnage", 0)
        size_score = min(100.0, (tonnage / 100.0) * 100.0)  # 100Mt = max
        return (cat_weight + size_score) / 2
