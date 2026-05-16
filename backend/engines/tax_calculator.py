"""
Mineral AI Tracker - Swedish ISK Tax Calculator (PRD v8.6)
Version: 8.6
Description: Investeringssparkonto (ISK) schablonskatt calculation - True Net Yield
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


# ----------------------------------------------------------------------------
# Constants (Swedish tax rules 2024/2025)
# ----------------------------------------------------------------------------
# Statslåneräntan (SLR) - government borrowing rate as of Nov 30 prior year
DEFAULT_SLR_PCT = 2.62  # 2024 figure; user can override

# Skattemyndigheten rules:
SLR_FLOOR_PCT = 1.25         # Statsrate floor (minimum)
ISK_RATE_BUMP_PCT = 1.0      # +1 percentage point added to SLR
CAPITAL_TAX_RATE = 0.30      # 30% schablonskatt


@dataclass
class ISKTaxResult:
    """Result of an ISK tax calculation for a single year."""
    capital_base: float          # Genomsnittligt kapitalunderlag
    schablon_rate_pct: float     # SLR + 1pp (with floor)
    schablonintakt: float        # Capital base × schablon_rate
    tax_due: float               # 30% of schablonintakt
    effective_rate_pct: float    # tax_due / capital_base * 100
    gross_yield_pct: float
    net_yield_pct: float
    gross_yield_sek: float
    net_yield_sek: float
    reasoning: str


class ISKTaxCalculator:
    """
    Swedish ISK schablonskatt calculator.

    Formula (Skatteverket):
        schablonintakt = capital_base × max(SLR_floor, SLR + 1%)
        tax_due        = schablonintakt × 30%

    The "capital base" (kapitalunderlag) is the average of:
        - Account value at start of each quarter (Q1-Q4)
        - All deposits made during the year (added 4x in this approximation)

    For the simplified Shadow Portfolio simulation we use the average of
    `start_balance` and `end_balance` as a proxy. Users wanting strict
    compliance should supply full quarterly snapshots via `capital_base`.
    """

    def __init__(
        self,
        slr_pct: float = DEFAULT_SLR_PCT,
        floor_pct: float = SLR_FLOOR_PCT,
        bump_pct: float = ISK_RATE_BUMP_PCT,
        tax_rate: float = CAPITAL_TAX_RATE,
    ):
        self.slr_pct = slr_pct
        self.floor_pct = floor_pct
        self.bump_pct = bump_pct
        self.tax_rate = tax_rate

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def schablon_rate(self) -> float:
        """Effective schablon rate (in percent), respecting the legal floor."""
        return max(self.floor_pct, self.slr_pct + self.bump_pct)

    def calculate(
        self,
        start_balance: float,
        end_balance: float,
        deposits: Optional[List[float]] = None,
        capital_base: Optional[float] = None,
    ) -> ISKTaxResult:
        """
        Calculate ISK tax for a year.

        Args:
            start_balance: Portfolio value at Jan 1.
            end_balance:   Portfolio value at Dec 31.
            deposits:      Total deposits during the year (added 4 times for
                           the quarterly-snapshot approximation).
            capital_base:  Override - if user supplies their own kapitalunderlag,
                           we use that directly.

        Returns:
            ISKTaxResult with both gross and true-net yield.
        """
        deposits = deposits or []

        if capital_base is None:
            # Skatteverket: average of quarterly snapshots + 4x deposits, /4
            quarterly_avg = (start_balance + end_balance) / 2.0
            capital_base = quarterly_avg + sum(deposits)

        rate_pct = self.schablon_rate()
        schablonintakt = capital_base * (rate_pct / 100.0)
        tax_due = schablonintakt * self.tax_rate

        # Yields
        gross_yield_sek = end_balance - start_balance - sum(deposits)
        net_yield_sek = gross_yield_sek - tax_due
        gross_yield_pct = (
            (gross_yield_sek / start_balance) * 100.0 if start_balance > 0 else 0.0
        )
        net_yield_pct = (
            (net_yield_sek / start_balance) * 100.0 if start_balance > 0 else 0.0
        )

        effective_rate = (
            (tax_due / capital_base) * 100.0 if capital_base > 0 else 0.0
        )

        reasoning = (
            f"SLR {self.slr_pct:.2f}% + {self.bump_pct:.0f}pp -> schablon rate "
            f"{rate_pct:.2f}% (floor {self.floor_pct:.2f}%). "
            f"Capital base {capital_base:,.0f} SEK -> schablonintakt "
            f"{schablonintakt:,.0f} SEK -> tax {tax_due:,.0f} SEK "
            f"({self.tax_rate * 100:.0f}%). "
            f"Gross {gross_yield_pct:+.2f}% -> Net {net_yield_pct:+.2f}%."
        )

        return ISKTaxResult(
            capital_base=capital_base,
            schablon_rate_pct=rate_pct,
            schablonintakt=schablonintakt,
            tax_due=tax_due,
            effective_rate_pct=effective_rate,
            gross_yield_pct=gross_yield_pct,
            net_yield_pct=net_yield_pct,
            gross_yield_sek=gross_yield_sek,
            net_yield_sek=net_yield_sek,
            reasoning=reasoning,
        )

    def to_dict(self, result: ISKTaxResult) -> Dict[str, Any]:
        return {
            "capital_base": result.capital_base,
            "schablon_rate_pct": result.schablon_rate_pct,
            "schablonintakt": result.schablonintakt,
            "tax_due": result.tax_due,
            "effective_rate_pct": result.effective_rate_pct,
            "gross_yield_pct": result.gross_yield_pct,
            "net_yield_pct": result.net_yield_pct,
            "gross_yield_sek": result.gross_yield_sek,
            "net_yield_sek": result.net_yield_sek,
            "reasoning": result.reasoning,
        }


# Singleton helper for FastAPI endpoints
default_isk_calculator = ISKTaxCalculator()
