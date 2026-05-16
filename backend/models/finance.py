"""
Mineral AI Tracker - Finance Models (PRD v8.0)
Version: 8.0
Description: Pydantic V2 models for financial data validation with strict field validators
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class SystemSettings(BaseModel):
    """Global system settings and thresholds for investment protection"""
    
    max_pe_ratio: float = Field(
        default=25.0,
        description="Maximalt tillåtet Forward P/E ratio",
        ge=0.0,
        le=200.0
    )
    
    min_market_cap_m: float = Field(
        default=10.0,
        description="Min market cap i miljoner USD",
        ge=1.0,
        le=1000000.0
    )
    
    min_daily_volume_k: float = Field(
        default=500.0,
        description="Min handelsvolym per dag i tusental USD",
        ge=10.0,
        le=10000000.0
    )
    
    min_confidence_score: int = Field(
        default=85,
        description="Tröskel för AI-larm (0-100)",
        ge=0,
        le=100
    )
    
    max_geological_grade_copper: float = Field(
        default=15.0,
        description="Maximalt tillåtet kopparhalt i % (fysisk brandvägg mot hallucinationer)",
        ge=0.0,
        le=100.0
    )

    # PRD v8.7 Phase 9 (API Credential Vault, forward-compat).
    # When set in the DB this overrides the FMP_API_KEY env var so admins
    # can rotate keys without redeploying. Optional for local-dev runs.
    fmp_api_key: Optional[str] = Field(
        default=None,
        description="Financial Modeling Prep API key (vault-backed override of FMP_API_KEY env var)"
    )


class CompanyFinancials(BaseModel):
    """Company financial data with strict validation"""
    
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    
    pe_ratio: Optional[float] = Field(
        None,
        description="Forward P/E ratio",
        ge=0.0,
        le=500.0
    )
    
    market_cap_m: float = Field(
        ...,
        gt=0,
        description="Market cap i miljoner USD"
    )
    
    avg_daily_volume_k: float = Field(
        ...,
        gt=0,
        description="Genomsnittlig daglig handelsvolym i tusental USD"
    )
    
    current_price: float = Field(
        ...,
        gt=0,
        description="Aktuell aktiekurs"
    )
    
    revenue_m: Optional[float] = Field(
        None,
        ge=0,
        description="Omsättning i miljoner USD"
    )
    
    ebitda_m: Optional[float] = Field(
        None,
        ge=0,
        description="EBITDA i miljoner USD"
    )
    
    debt_to_equity: Optional[float] = Field(
        None,
        ge=0,
        le=1000,
        description="Skuld/equity ratio"
    )
    
    @field_validator('pe_ratio')
    @classmethod
    def validate_pe(cls, v: Optional[float]) -> Optional[float]:
        """Validate P/E ratio to detect data errors or extreme bubbles"""
        if v is not None and v > 150.0:
            raise ValueError(
                f"Orimligt P/E-tal ({v}). Förmodligen datafel eller extrem bubbla. "
                f"Max tillåtet är 150."
            )
        return v
    
    @field_validator('market_cap_m')
    @classmethod
    def validate_market_cap(cls, v: float) -> float:
        """Hard barrier against penny stocks and fraud risks"""
        if v < 1.0:
            raise ValueError(
                "Market Cap är under 1 miljon USD. Extrem bedrägeririsk. Ignoreras."
            )
        return v
    
    @field_validator('avg_daily_volume_k')
    @classmethod
    def validate_volume(cls, v: float) -> float:
        """Validate liquidity to prevent illiquid traps"""
        if v < 10.0:
            raise ValueError(
                "Handelsvolym är under 10k USD per dag. Extrem illikviditetsrisk. Ignoreras."
            )
        return v


class AssetScore(BaseModel):
    """Calculated scores for an asset"""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    
    buffett_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Buffett Score (0-100)"
    )
    
    lassonde_score: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Lassonde Curve Score (0-100)"
    )
    
    soros_score: Optional[float] = Field(
        None,
        ge=-100,
        le=100,
        description="Soros Macro Score (-100 to 100, negative = short signal)"
    )
    
    lynch_score: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Peter Lynch GARP Score (0-100)"
    )
    
    institutional_alpha: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Institutional Alpha Score (0-100)"
    )
    
    confidence_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Overall AI Confidence Score (0-100)"
    )
    
    recommendation: str = Field(
        ...,
        description="Investment recommendation: BUY, HOLD, SELL, SHORT"
    )
    
    position_size_pct: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Recommended position size as % of portfolio (Kelly Criterion)"
    )


class TradeJournalEntry(BaseModel):
    """Trade journal entry for RLHF (Reinforcement Learning from Human Feedback)"""
    
    id: str = Field(..., description="Unique entry ID")
    
    ticker: str = Field(..., description="Stock ticker symbol")
    
    ai_recommendation: str = Field(..., description="AI recommendation at time of decision")
    
    user_decision: str = Field(..., description="User decision: BUY, SELL, HOLD, IGNORE")
    
    ai_confidence: int = Field(..., ge=0, le=100, description="AI confidence at time of decision")
    
    entry_price: float = Field(..., gt=0, description="Entry price")
    
    entry_date: str = Field(..., description="Entry date (ISO 8601)")
    
    exit_price: Optional[float] = Field(None, gt=0, description="Exit price (if closed)")
    
    exit_date: Optional[str] = Field(None, description="Exit date (ISO 8601, if closed)")
    
    outcome_pct: Optional[float] = Field(None, description="Outcome in % (if closed)")
    
    user_beat_ai: Optional[bool] = Field(None, description="Did user beat AI recommendation?")
    
    feedback_notes: Optional[str] = Field(None, max_length=2000, description="User feedback notes")
