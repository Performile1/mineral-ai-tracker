"""
Mineral AI Tracker - Thematic Basket Engine (PRD v8.6 §4, Phase 8)
Version: 8.6
Description: AI-managed thematic baskets ("Critical Minerals Europe", etc.)
             Auto-rebalances when underlying holdings receive a SELL/SHORT
             signal from the SLM Orchestrator, swapping them for the
             highest-ranked reserve from the Target List.

Single-purpose: pure functions, no DB writes. The caller (a future scheduler
hook or API endpoint) is responsible for persisting the resulting plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Iterable
from datetime import datetime
from loguru import logger


# ----------------------------------------------------------------------------
# Built-in basket definitions (PRD v8.6 §4)
# Each basket lists its core tickers + a reserve list pulled from Target List.
# ----------------------------------------------------------------------------

DEFAULT_BASKETS: Dict[str, Dict[str, List[str]]] = {
    "critical_minerals_eu": {
        "core": ["BOL.ST", "LUC.TO", "EUR.AX", "TLO.ST"],
        "reserve": ["NEO.TO", "ENO.ST", "AIE.PA", "BEZ.ST"],
        "label": "Critical Minerals Europe",
    },
    "uranium_revival": {
        "core": ["CCJ", "UEC", "DNN", "URA"],
        "reserve": ["NXE.TO", "PDN.AX", "BOE.AX", "FCU.TO"],
        "label": "Uranium Revival",
    },
    "robotics_ev_alloys": {
        "core": ["LIT", "ALB", "PLL", "MP"],
        "reserve": ["LAC", "SQM", "PILBF", "TLO.ST"],
        "label": "Robotics & EV Alloys",
    },
}


# ----------------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------------

@dataclass
class Holding:
    ticker: str
    weight: float = 0.0
    shares: float = 0.0


@dataclass
class Signal:
    """Represents a Multi-SLM Debate output for a ticker."""
    ticker: str
    signal_type: str          # "BUY" | "SELL" | "HOLD" | "SHORT"
    confidence_score: int     # 0-100
    rank_score: float = 0.0   # higher = better candidate (e.g. consensus * confidence)


@dataclass
class RebalanceAction:
    action: str               # "SELL" | "BUY" | "HOLD"
    ticker: str
    reason: str
    target_weight: float = 0.0
    swap_for: Optional[str] = None


@dataclass
class RebalancePlan:
    basket_name: str
    label: str
    actions: List[RebalanceAction] = field(default_factory=list)
    final_holdings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ----------------------------------------------------------------------------
# Core API
# ----------------------------------------------------------------------------

SELL_TYPES = {"SELL", "SHORT"}


def _signal_lookup(signals: Iterable[Signal]) -> Dict[str, Signal]:
    return {s.ticker.upper(): s for s in signals}


def rebalance_basket(
    basket_name: str,
    current_holdings: List[Holding],
    target_signals: List[Signal],
    reserve_pool: Optional[List[str]] = None,
    max_swaps: int = 5,
    label: Optional[str] = None,
) -> RebalancePlan:
    """
    Iterate over current holdings, identify SELL/SHORT signals, and replace
    them with the highest-ranked reserve ticker that has a current BUY signal
    (or the highest-confidence reserve if no BUY exists yet).

    Args:
        basket_name:      Internal id (e.g. "critical_minerals_eu")
        current_holdings: List[Holding] held in the basket today.
        target_signals:   Latest SLM signals across the universe (core + reserve).
        reserve_pool:     Candidate tickers used to refill the basket.
                          Defaults to DEFAULT_BASKETS[basket_name]['reserve'].
        max_swaps:        Cap to prevent over-trading in a single rebalance.
        label:            Optional human-friendly label override.

    Returns:
        RebalancePlan with deterministic actions and final_holdings list.
    """
    basket_meta = DEFAULT_BASKETS.get(basket_name, {})
    reserve = list(reserve_pool or basket_meta.get("reserve", []))
    label = label or basket_meta.get("label", basket_name.replace("_", " ").title())

    sig_map = _signal_lookup(target_signals)

    # Reserve candidates ranked by rank_score (BUY first, then HOLD)
    reserve_signals = [
        sig_map[r.upper()] for r in reserve if r.upper() in sig_map
    ]
    reserve_buys = sorted(
        [s for s in reserve_signals if s.signal_type.upper() == "BUY"],
        key=lambda s: (s.rank_score, s.confidence_score),
        reverse=True,
    )
    reserve_holds = sorted(
        [s for s in reserve_signals if s.signal_type.upper() == "HOLD"],
        key=lambda s: (s.rank_score, s.confidence_score),
        reverse=True,
    )
    candidate_queue: List[str] = (
        [s.ticker.upper() for s in reserve_buys] +
        [s.ticker.upper() for s in reserve_holds] +
        # last resort: tickers we have no signal for (still better than holding a SELL)
        [r.upper() for r in reserve if r.upper() not in sig_map]
    )

    actions: List[RebalanceAction] = []
    current_set = {h.ticker.upper(): h for h in current_holdings}
    used_swaps = 0

    # Pass 1: find SELL/SHORT in core holdings, swap them out
    for ticker, holding in list(current_set.items()):
        sig = sig_map.get(ticker)
        if sig and sig.signal_type.upper() in SELL_TYPES:
            if used_swaps >= max_swaps:
                actions.append(RebalanceAction(
                    action="HOLD",
                    ticker=ticker,
                    reason=f"SELL signal but max_swaps={max_swaps} cap reached",
                    target_weight=holding.weight,
                ))
                continue

            replacement = next(
                (c for c in candidate_queue if c not in current_set),
                None,
            )
            if replacement is None:
                actions.append(RebalanceAction(
                    action="SELL",
                    ticker=ticker,
                    reason=f"{sig.signal_type} signal (conf {sig.confidence_score}); "
                           f"no replacement in reserve pool",
                    target_weight=0.0,
                ))
                current_set.pop(ticker, None)
            else:
                actions.append(RebalanceAction(
                    action="SELL",
                    ticker=ticker,
                    reason=f"{sig.signal_type} signal (conf {sig.confidence_score})",
                    target_weight=0.0,
                    swap_for=replacement,
                ))
                actions.append(RebalanceAction(
                    action="BUY",
                    ticker=replacement,
                    reason=f"Replacement for {ticker} (highest-ranked reserve)",
                    target_weight=holding.weight,
                ))
                current_set.pop(ticker, None)
                current_set[replacement] = Holding(ticker=replacement, weight=holding.weight)
                # Don't reuse the same replacement twice
                candidate_queue = [c for c in candidate_queue if c != replacement]
                used_swaps += 1

    # Pass 2: holdings without matching signal -> annotate as HOLD
    for ticker, holding in current_set.items():
        if any(a.ticker == ticker for a in actions if a.action == "BUY"):
            continue
        sig = sig_map.get(ticker)
        actions.append(RebalanceAction(
            action="HOLD",
            ticker=ticker,
            reason=(
                f"{sig.signal_type} signal (conf {sig.confidence_score})"
                if sig else "no current signal"
            ),
            target_weight=holding.weight,
        ))

    plan = RebalancePlan(
        basket_name=basket_name,
        label=label,
        actions=actions,
        final_holdings=sorted(current_set.keys()),
    )
    logger.info(
        f"🧺 Rebalance {basket_name}: {used_swaps} swap(s), "
        f"{len(plan.final_holdings)} final holdings"
    )
    return plan


def plan_to_dict(plan: RebalancePlan) -> Dict:
    return {
        "basket_name": plan.basket_name,
        "label": plan.label,
        "timestamp": plan.timestamp,
        "final_holdings": plan.final_holdings,
        "actions": [
            {
                "action": a.action,
                "ticker": a.ticker,
                "reason": a.reason,
                "target_weight": a.target_weight,
                "swap_for": a.swap_for,
            }
            for a in plan.actions
        ],
    }


__all__ = [
    "DEFAULT_BASKETS",
    "Holding",
    "Signal",
    "RebalanceAction",
    "RebalancePlan",
    "rebalance_basket",
    "plan_to_dict",
]
