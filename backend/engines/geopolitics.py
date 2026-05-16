"""
Mineral AI Tracker - Geopolitics Engine (PRD v8.3)
Version: 8.3
Description: Friend-Shoring premium + EU CBAM penalty + sanctions/trade-war risk
"""

from typing import Dict, Any, List
from dataclasses import dataclass


# ----------------------------------------------------------------------------
# Country tiers (Friend-Shoring doctrine)
# ----------------------------------------------------------------------------
TIER_1_FRIEND_SHORE = {
    # Nordic / EU - resource secure, stable rule of law
    "SE", "NO", "FI", "DK", "IS",
    # CANZUK
    "CA", "AU", "NZ", "GB",
    # USA + allies
    "US", "IE",
}

TIER_2_NEUTRAL = {
    "DE", "FR", "NL", "BE", "AT", "CH", "ES", "PT", "IT",
    "CZ", "PL", "EE", "LV", "LT", "SK", "SI",
    "JP", "KR", "TW", "SG",
    "CL", "MX", "BR",
}

TIER_3_GEOPOLITICAL_RISK = {
    "CN", "RU", "IR", "KP", "MM", "VE", "BY", "SY",
    "AF", "LY", "SD", "SS", "YE",
}

TIER_4_NEUTRAL_DEVELOPING = {
    # Resource-rich but jurisdictional risk
    "ZA", "ZM", "CD", "GH", "BF", "ML", "ID", "PH", "MN", "KZ", "PE", "AR",
}


# EU member states subject to CBAM (Carbon Border Adjustment Mechanism)
EU_CBAM_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE",
}

# Commodity carbon-intensity proxy (kg CO2e / tonne).
# Higher = harder hit by CBAM / ESG screens.
COMMODITY_CARBON_INTENSITY = {
    "coal": 2400,
    "iron": 1800,
    "steel": 1850,
    "cement": 900,
    "aluminium": 11500,
    "aluminum": 11500,
    "copper": 4000,
    "nickel": 12000,
    "zinc": 3500,
    "lead": 1500,
    "gold": 16000,
    "silver": 9000,
    "lithium": 5000,
    "cobalt": 7000,
    "rare_earth": 6000,
    "uranium": 1200,
    "graphite": 3500,
    "tin": 16000,
}


@dataclass
class GeopoliticsResult:
    score: float                      # 0-100
    friend_shore_premium: float       # 0-30
    cbam_penalty: float               # 0..40 (subtracted from baseline)
    sanctions_penalty: float          # 0..50
    tier: str
    reasoning: str


class GeopoliticsEngine:
    """
    Geopolitics Engine (PRD v8.3).

    Three sub-scores combined into a single 0-100 jurisdiction score:

      1. Friend-Shoring Premium (+):  Tier 1 western allies score higher.
      2. CBAM Penalty (-):            EU operations producing energy-intensive,
                                      carbon-heavy commodities get penalized.
      3. Sanctions / Trade-War (-):   Tier 3 jurisdictions are heavily penalized.

    Score interpretation:
      - 80-100: Best-in-class jurisdiction (Sweden, Canada, Australia)
      - 50-79:  Acceptable (most EU + OECD non-EU allies)
      - 30-49:  Caution (developing producers, ESG headwinds)
      - 0-29:   Avoid (sanctioned / hostile jurisdictions)
    """

    BASELINE_SCORE = 60.0

    def score(self, ctx: Dict[str, Any]) -> GeopoliticsResult:
        country = (ctx.get("country_code") or "").upper()
        commodity = (ctx.get("commodity_type") or "").lower()
        is_fossil = bool(ctx.get("is_fossil_fuel", commodity in {"coal", "oil", "gas", "lignite"}))
        sanctioned = bool(ctx.get("under_sanctions", False))

        reasoning_parts: List[str] = []

        # 1. Friend-Shoring tier
        tier, friend_shore_premium = self._friend_shore_tier(country)
        reasoning_parts.append(f"{tier} country ({country}): {friend_shore_premium:+.0f} premium")

        # 2. CBAM penalty: only applies to EU producers of high-carbon commodities
        cbam_penalty = self._cbam_penalty(country, commodity, is_fossil)
        if cbam_penalty > 0:
            reasoning_parts.append(
                f"CBAM penalty -{cbam_penalty:.0f} ({commodity or 'unknown commodity'} in EU)"
            )

        # 3. Sanctions / trade-war hit
        sanctions_penalty = self._sanctions_penalty(country, sanctioned)
        if sanctions_penalty > 0:
            reasoning_parts.append(f"Sanctions/trade-war penalty -{sanctions_penalty:.0f}")

        # Composite
        score = self.BASELINE_SCORE + friend_shore_premium - cbam_penalty - sanctions_penalty
        score = max(0.0, min(100.0, score))

        reasoning = "; ".join(reasoning_parts) + f". Final geopolitics score: {score:.1f}."

        return GeopoliticsResult(
            score=score,
            friend_shore_premium=friend_shore_premium,
            cbam_penalty=cbam_penalty,
            sanctions_penalty=sanctions_penalty,
            tier=tier,
            reasoning=reasoning,
        )

    # ------------------------------------------------------------------
    # Sub-scores
    # ------------------------------------------------------------------

    def _friend_shore_tier(self, country: str) -> tuple[str, float]:
        if not country:
            return ("UNKNOWN", 0.0)
        if country in TIER_1_FRIEND_SHORE:
            return ("TIER_1_FRIEND_SHORE", 30.0)
        if country in TIER_2_NEUTRAL:
            return ("TIER_2_NEUTRAL_ALLY", 15.0)
        if country in TIER_4_NEUTRAL_DEVELOPING:
            return ("TIER_4_NEUTRAL_DEVELOPING", -5.0)
        if country in TIER_3_GEOPOLITICAL_RISK:
            return ("TIER_3_HOSTILE", -30.0)
        return ("UNCATEGORIZED", 0.0)

    def _cbam_penalty(self, country: str, commodity: str, is_fossil: bool) -> float:
        """
        EU CBAM hits energy-intensive fossil production hardest.

        Scoring:
          - Non-EU producers: 0
          - EU producers of low-carbon commodity (<1500 kg/t): 0
          - EU + fossil fuel: flat 40 (max penalty)
          - EU + high-carbon: scales 5-30 with carbon intensity
        """
        if country not in EU_CBAM_COUNTRIES:
            return 0.0

        if is_fossil:
            return 40.0

        intensity = COMMODITY_CARBON_INTENSITY.get(commodity, 0)
        if intensity < 1500:
            return 0.0
        if intensity < 4000:
            return 10.0
        if intensity < 8000:
            return 20.0
        return 30.0

    def _sanctions_penalty(self, country: str, sanctioned: bool) -> float:
        if sanctioned:
            return 50.0
        if country in TIER_3_GEOPOLITICAL_RISK:
            return 20.0
        return 0.0
