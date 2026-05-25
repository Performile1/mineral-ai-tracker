"""
schemas/omniscient.py
=====================
Pydantic schemas for the Sprint 16 "Omniscient Expansion" intelligence modules.

Read models mirror the DB columns used by each module's SQL queries.
Agent I/O models define the contract between the agent logic and its
persistence layer so callers can rely on typed return values.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Nexus node _meta shape (Sprint 16 extension)
# ---------------------------------------------------------------------------

class NexusNodeMeta(BaseModel):
    """
    Describes the `_meta` key stored inside
    `supply_chain_nodes.extracted_data` JSONB.

    Added in Sprint 16:
      sentiment_score      — written by Local Sentiment Crawler
      chokepoint_exposure  — written by Chokepoint Oracle
    """

    source: str = "RAG_CLAUDE_3.5"
    prompt_version: str
    extracted_at: str
    dilution_risk_score: Optional[float] = None
    sentiment_score: Optional[float] = Field(
        default=None,
        description="Normalised sentiment score [-1.0 = very negative, +1.0 = very positive]",
    )
    chokepoint_exposure: Optional[float] = Field(
        default=None,
        description="Fraction of supply routes exposed to active chokepoints [0.0 – 1.0]",
    )


# ---------------------------------------------------------------------------
# Database read models
# ---------------------------------------------------------------------------

class TransitMetricRead(BaseModel):
    """Read model for a row in `transit_metrics`."""

    id: int
    index_name: str
    current_value: Optional[float] = None
    weekly_change_pct: Optional[float] = None
    daily_change_pct: Optional[float] = None
    chokepoint_status: Optional[Dict[str, Any]] = None
    alert_triggered: bool = False
    alert_reason: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SecondarySupplyRead(BaseModel):
    """Read model for a row in `secondary_supply`."""

    material_name: str
    scrap_price_usd: Optional[float] = None
    primary_price_usd: Optional[float] = None
    primary_secondary_spread: Optional[float] = None
    spread_pct: Optional[float] = None
    buy_signal: bool = False
    recycler_tickers: Optional[List[str]] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LaborDisputeRead(BaseModel):
    """
    Read model for a row in `labor_disputes`.
    Includes `is_early_warning` added in migration 0006.
    """

    id: str
    asset_ticker: Optional[str] = None
    facility_name: Optional[str] = None
    region: Optional[str] = None
    dispute_type: Optional[str] = None
    severity_level: int
    is_early_warning: bool = False
    description: Optional[str] = None
    source_url: Optional[str] = None
    is_active: bool
    triggered_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Agent I/O contracts
# ---------------------------------------------------------------------------

class BuyoutPrediction(BaseModel):
    """
    Output of the Sovereign M&A Predictor agent.
    The agent writes `buyout_probability_score` back to
    `supply_chain_nodes.buyout_probability_score`.
    """

    ticker: str
    buyout_probability_score: float = Field(..., ge=0.0, le=100.0)
    reasoning: Optional[str] = None
    geopolitical_context: Optional[str] = None
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class ChokepointAlert(BaseModel):
    """
    Output of the Chokepoint Oracle agent per index-spike event.
    The agent raises `geopolitical_friction_cost` on affected edges.
    """

    index_name: str
    current_value: float
    spike_pct: float = Field(..., description="Percentage change that triggered the alert")
    affected_edge_ids: List[str] = Field(
        default_factory=list,
        description="IDs of supply_chain_edges rows whose friction cost was raised",
    )
    friction_cost_delta: float = Field(
        default=0.0, description="Amount added to geopolitical_friction_cost"
    )
    alert_reason: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class SentimentEarlyWarning(BaseModel):
    """
    Output of the Local Sentiment Crawler agent for a single signal.
    Written to `labor_disputes` with `is_early_warning = TRUE`
    and `severity_level = 0` to distinguish from confirmed disputes.
    """

    asset_ticker: str
    facility_name: Optional[str] = None
    region: Optional[str] = None
    raw_signal: str = Field(..., description="Raw text excerpt that triggered the warning")
    language_detected: Optional[str] = None
    sentiment_score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Sentiment polarity: -1.0 = strongly negative, +1.0 = strongly positive",
    )
    is_early_warning: bool = True
    severity_level: int = Field(
        default=0,
        description="0 = Simmering/Rumor (early warning), 1-5 = confirmed escalation",
    )
    source_url: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)
