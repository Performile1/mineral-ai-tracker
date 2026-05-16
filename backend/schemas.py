"""
Mineral AI Tracker - Pydantic Schemas
Version: 3.0
Description: Data validation schemas for backend API using Pydantic
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class AssetType(str, Enum):
    STOCK = "stock"
    COMMODITY = "commodity"
    ETF = "etf"


class CommodityType(str, Enum):
    LITHIUM = "lithium"
    COBALT = "cobalt"
    NICKEL = "nickel"
    COPPER = "copper"
    RARE_EARTH = "rare_earth"
    URANIUM = "uranium"
    GOLD = "gold"
    OTHER = "other"


class Stage(str, Enum):
    PROSPECTING = "prospecting"
    EXPLORATION = "exploration"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class MacroSource(str, Enum):
    IEA = "IEA"
    EUROSTAT = "Eurostat"
    LME = "LME"
    BENCHMARK = "Benchmark"
    OTHER = "other"


class EventType(str, Enum):
    POLICY = "policy"
    REGULATION = "regulation"
    GEOPOLITICAL = "geopolitical"
    TRADE_WAR = "trade_war"
    SANCTION = "sanction"
    BLACK_SWAN = "black_swan"


class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SourcePlatform(str, Enum):
    PLACERA = "placera"
    REDDIT = "reddit"
    ETORO = "etoro"
    TRADER_BLOG = "trader_blog"
    OTHER = "other"


class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class ActualOutcome(str, Enum):
    PROFIT = "profit"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    PENDING = "pending"


class AIRecommendation(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class UserDecision(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    IGNORE = "ignore"


class Outcome(str, Enum):
    PROFIT = "profit"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    PENDING = "pending"


class AlertType(str, Enum):
    STOP_LOSS = "stop_loss"
    TARGET_PRICE = "target_price"
    BUFFETT_SCORE = "buffett_score"
    GEO_EVENT = "geo_event"
    PRICE_CHANGE = "price_change"


class ComparisonOperator(str, Enum):
    ABOVE = "above"
    BELOW = "below"
    EQUAL = "equal"


class SMSStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


# ============================================================================
# ASSET SCHEMAS
# ============================================================================

class AssetBase(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20, description="Stock/commodity ticker symbol")
    name: str = Field(..., min_length=1, max_length=255, description="Asset name")
    asset_type: AssetType
    commodity_type: Optional[CommodityType] = None
    country_code: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")
    exchange: str = Field(..., min_length=1, max_length=50, description="Exchange name")
    isin: Optional[str] = Field(None, max_length=20, description="ISIN identifier")
    sector: Optional[str] = Field(None, max_length=100, description="Sector classification")
    stage: Optional[Stage] = None
    production_capacity_tonnes: Optional[Decimal] = Field(None, ge=0, description="Annual production capacity in tonnes")
    reserve_estimate_tonnes: Optional[Decimal] = Field(None, ge=0, description="Estimated reserves in tonnes")


class AssetFinancial(BaseModel):
    current_price: Optional[Decimal] = Field(None, ge=0, description="Current market price")
    market_cap_million: Optional[Decimal] = Field(None, ge=0, description="Market cap in millions")
    pe_ratio: Optional[Decimal] = Field(None, ge=0, description="Price-to-earnings ratio")
    dividend_yield: Optional[Decimal] = Field(None, ge=0, le=1, description="Dividend yield as decimal")


class AssetScores(BaseModel):
    macro_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Macro demand score (0-1)")
    commodity_aisc_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Commodity AISC score (0-1)")
    geo_policy_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Geopolitical policy score (0-1)")
    insider_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Insider trading score (0-1)")
    trader_sentiment_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Trader sentiment score (0-1)")
    buffett_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Composite Buffett score (0-1)")
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Confidence score (0-1)")


class AssetRiskManagement(BaseModel):
    target_price: Optional[Decimal] = Field(None, ge=0, description="Target price for exit")
    stop_loss: Optional[Decimal] = Field(None, ge=0, description="Stop-loss price")
    kelly_position_size: Optional[Decimal] = Field(None, ge=0, le=1, description="Kelly criterion position size (0-1)")
    risk_reward_ratio: Optional[Decimal] = Field(None, ge=0, description="Risk/reward ratio")


class AssetMetadata(BaseModel):
    logo_url: Optional[str] = None
    avanza_url: Optional[str] = None
    nordnet_url: Optional[str] = None
    last_price_update: Optional[datetime] = None
    last_score_update: Optional[datetime] = None


class AssetCreate(AssetBase, AssetFinancial, AssetScores, AssetRiskManagement, AssetMetadata):
    pass


class AssetUpdate(BaseModel):
    current_price: Optional[Decimal] = Field(None, ge=0)
    market_cap_million: Optional[Decimal] = Field(None, ge=0)
    pe_ratio: Optional[Decimal] = Field(None, ge=0)
    dividend_yield: Optional[Decimal] = Field(None, ge=0, le=1)
    macro_score: Optional[Decimal] = Field(None, ge=0, le=1)
    commodity_aisc_score: Optional[Decimal] = Field(None, ge=0, le=1)
    geo_policy_score: Optional[Decimal] = Field(None, ge=0, le=1)
    insider_score: Optional[Decimal] = Field(None, ge=0, le=1)
    trader_sentiment_score: Optional[Decimal] = Field(None, ge=0, le=1)
    buffett_score: Optional[Decimal] = Field(None, ge=0, le=1)
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    target_price: Optional[Decimal] = Field(None, ge=0)
    stop_loss: Optional[Decimal] = Field(None, ge=0)
    kelly_position_size: Optional[Decimal] = Field(None, ge=0, le=1)
    risk_reward_ratio: Optional[Decimal] = Field(None, ge=0)
    last_price_update: Optional[datetime] = None
    last_score_update: Optional[datetime] = None


class Asset(AssetCreate):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MACRO DEMAND SCHEMAS
# ============================================================================

class MacroDemandBase(BaseModel):
    asset_id: str
    source: MacroSource
    indicator_type: str = Field(..., min_length=1, max_length=100)
    indicator_value: Optional[Decimal] = None
    unit: Optional[str] = Field(None, max_length=50)
    period_start: date
    period_end: date
    data_quality_score: Optional[Decimal] = Field(None, ge=0, le=1)
    notes: Optional[str] = None


class MacroDemandCreate(MacroDemandBase):
    pass


class MacroDemandUpdate(BaseModel):
    indicator_value: Optional[Decimal] = None
    data_quality_score: Optional[Decimal] = Field(None, ge=0, le=1)
    notes: Optional[str] = None


class MacroDemand(MacroDemandBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# GEO EVENTS SCHEMAS
# ============================================================================

class GeoEventBase(BaseModel):
    event_type: EventType
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    country_code: Optional[str] = Field(None, max_length=2)
    region: Optional[str] = Field(None, max_length=100)
    affected_commodities: Optional[List[CommodityType]] = None
    impact_level: ImpactLevel
    sentiment_score: Optional[Decimal] = Field(None, ge=-1, le=1)
    event_date: date
    is_ongoing: bool = False
    end_date: Optional[date] = None
    source: str = Field(..., min_length=1, max_length=100)
    source_url: Optional[str] = None


class GeoEventCreate(GeoEventBase):
    pass


class GeoEventUpdate(BaseModel):
    impact_level: Optional[ImpactLevel] = None
    sentiment_score: Optional[Decimal] = Field(None, ge=-1, le=1)
    is_ongoing: Optional[bool] = None
    end_date: Optional[date] = None
    description: Optional[str] = None


class GeoEvent(GeoEventBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# TRADER SENTIMENT SCHEMAS
# ============================================================================

class TraderSentimentBase(BaseModel):
    asset_id: str
    source_platform: SourcePlatform
    source_url: str = Field(..., min_length=1)
    author_handle: Optional[str] = Field(None, max_length=255)
    post_title: Optional[str] = Field(None, max_length=500)
    post_content: Optional[str] = None
    sentiment_score: Optional[Decimal] = Field(None, ge=-1, le=1)
    confidence: Optional[Decimal] = Field(None, ge=0, le=1)
    trader_success_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    trader_followers_count: Optional[int] = Field(None, ge=0)
    is_verified_trader: bool = False
    trade_direction: Optional[TradeDirection] = None
    trade_timeframe: Optional[str] = Field(None, max_length=20)
    entry_price: Optional[Decimal] = Field(None, ge=0)
    target_price: Optional[Decimal] = Field(None, ge=0)
    actual_outcome: Optional[ActualOutcome] = None
    outcome_percentage: Optional[Decimal] = None
    outcome_date: Optional[date] = None
    post_date: datetime


class TraderSentimentCreate(TraderSentimentBase):
    pass


class TraderSentimentUpdate(BaseModel):
    sentiment_score: Optional[Decimal] = Field(None, ge=-1, le=1)
    confidence: Optional[Decimal] = Field(None, ge=0, le=1)
    actual_outcome: Optional[ActualOutcome] = None
    outcome_percentage: Optional[Decimal] = None
    outcome_date: Optional[date] = None


class TraderSentiment(TraderSentimentBase):
    id: str
    scraped_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# TRADE JOURNAL SCHEMAS (RLHF)
# ============================================================================

class TradeJournalBase(BaseModel):
    user_id: str
    asset_id: str
    ai_buffett_score: Optional[Decimal] = Field(None, ge=0, le=1)
    ai_confidence: Optional[Decimal] = Field(None, ge=0, le=1)
    ai_recommendation: Optional[AIRecommendation] = None
    ai_kelly_position_size: Optional[Decimal] = Field(None, ge=0, le=1)
    user_decision: UserDecision
    user_position_size: Optional[Decimal] = Field(None, ge=0)
    user_reasoning: Optional[str] = None
    entry_price: Optional[Decimal] = Field(None, ge=0)
    exit_price: Optional[Decimal] = Field(None, ge=0)
    entry_date: Optional[datetime] = None
    exit_date: Optional[datetime] = None
    actual_return_percentage: Optional[Decimal] = None
    outcome: Optional[Outcome] = None
    holding_period_days: Optional[int] = Field(None, ge=0)
    ai_was_correct: Optional[bool] = None
    user_was_correct: Optional[bool] = None
    learning_weight_adjustment: Optional[Decimal] = None
    notes: Optional[str] = None


class TradeJournalCreate(TradeJournalBase):
    pass


class TradeJournalUpdate(BaseModel):
    exit_price: Optional[Decimal] = Field(None, ge=0)
    exit_date: Optional[datetime] = None
    actual_return_percentage: Optional[Decimal] = None
    outcome: Optional[Outcome] = None
    holding_period_days: Optional[int] = Field(None, ge=0)
    ai_was_correct: Optional[bool] = None
    user_was_correct: Optional[bool] = None
    learning_weight_adjustment: Optional[Decimal] = None
    notes: Optional[str] = None


class TradeJournal(TradeJournalBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# USER PORTFOLIO SCHEMAS
# ============================================================================

class UserPortfolioBase(BaseModel):
    user_id: str
    asset_id: str
    shares_held: Decimal = Field(..., ge=0)
    average_cost: Decimal = Field(..., ge=0)
    current_value: Optional[Decimal] = Field(None, ge=0)
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_percentage: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = Field(None, ge=0)
    target_price: Optional[Decimal] = Field(None, ge=0)
    is_stop_loss_active: bool = False


class UserPortfolioCreate(UserPortfolioBase):
    pass


class UserPortfolioUpdate(BaseModel):
    shares_held: Optional[Decimal] = Field(None, ge=0)
    average_cost: Optional[Decimal] = Field(None, ge=0)
    current_value: Optional[Decimal] = Field(None, ge=0)
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_percentage: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = Field(None, ge=0)
    target_price: Optional[Decimal] = Field(None, ge=0)
    is_stop_loss_active: Optional[bool] = None


class UserPortfolio(UserPortfolioBase):
    id: str
    purchased_at: datetime
    last_updated: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ALERTS SCHEMAS
# ============================================================================

class AlertBase(BaseModel):
    user_id: str
    asset_id: str
    alert_type: AlertType
    threshold_value: Optional[Decimal] = None
    comparison_operator: Optional[ComparisonOperator] = None
    is_active: bool = True
    message_template: Optional[str] = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    threshold_value: Optional[Decimal] = None
    comparison_operator: Optional[ComparisonOperator] = None
    is_active: Optional[bool] = None
    message_template: Optional[str] = None


class Alert(AlertBase):
    id: str
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0
    sms_sent: bool = False
    sms_sent_at: Optional[datetime] = None
    sms_status: Optional[SMSStatus] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# BACKTESTING RESULTS SCHEMAS
# ============================================================================

class BacktestingResultsBase(BaseModel):
    user_id: str
    strategy_name: str = Field(..., min_length=1, max_length=100)
    start_date: date
    end_date: date
    initial_capital: Decimal = Field(..., gt=0)
    weight_macro: Decimal = Field(..., ge=0, le=1)
    weight_commodity: Decimal = Field(..., ge=0, le=1)
    weight_geo: Decimal = Field(..., ge=0, le=1)
    weight_insider: Decimal = Field(..., ge=0, le=1)
    weight_sentiment: Decimal = Field(..., ge=0, le=1)
    final_capital: Optional[Decimal] = Field(None, ge=0)
    total_return_percentage: Optional[Decimal] = None
    annualized_return: Optional[Decimal] = None
    max_drawdown_percentage: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    win_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    total_trades: Optional[int] = Field(None, ge=0)
    winning_trades: Optional[int] = Field(None, ge=0)
    losing_trades: Optional[int] = Field(None, ge=0)
    benchmark_return_percentage: Optional[Decimal] = None
    alpha: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    notes: Optional[str] = None

    @validator('weight_macro', 'weight_commodity', 'weight_geo', 'weight_insider', 'weight_sentiment')
    def validate_weights_sum(cls, v, values):
        # Note: This is a simplified validation. In production, you'd validate the sum
        # of all weights equals 1.0 in a separate method.
        return v


class BacktestingResultsCreate(BacktestingResultsBase):
    pass


class BacktestingResultsUpdate(BaseModel):
    final_capital: Optional[Decimal] = Field(None, ge=0)
    total_return_percentage: Optional[Decimal] = None
    annualized_return: Optional[Decimal] = None
    max_drawdown_percentage: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    win_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    total_trades: Optional[int] = Field(None, ge=0)
    winning_trades: Optional[int] = Field(None, ge=0)
    losing_trades: Optional[int] = Field(None, ge=0)
    benchmark_return_percentage: Optional[Decimal] = None
    alpha: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    notes: Optional[str] = None


class BacktestingResults(BacktestingResultsBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# BUFFETT SCORE CALCULATION SCHEMAS
# ============================================================================

class BuffettScoreInput(BaseModel):
    macro_score: Decimal = Field(..., ge=0, le=1, description="Macro demand score (D)")
    commodity_aisc_score: Decimal = Field(..., ge=0, le=1, description="Commodity AISC score (C)")
    geo_policy_score: Decimal = Field(..., ge=0, le=1, description="Geopolitical policy score (G)")
    insider_score: Decimal = Field(..., ge=0, le=1, description="Insider trading score (I)")
    trader_sentiment_score: Decimal = Field(..., ge=0, le=1, description="Trader sentiment score (S)")
    confidence: Decimal = Field(..., ge=0, le=1, description="Confidence multiplier (Conf)")
    weight_macro: Decimal = Field(default=Decimal("0.30"), ge=0, le=1)
    weight_commodity: Decimal = Field(default=Decimal("0.30"), ge=0, le=1)
    weight_geo: Decimal = Field(default=Decimal("0.20"), ge=0, le=1)
    weight_insider: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)
    weight_sentiment: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)

    @validator('weight_macro', 'weight_commodity', 'weight_geo', 'weight_insider', 'weight_sentiment')
    def validate_weights(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Weights must be between 0 and 1")
        return v


class BuffettScoreOutput(BaseModel):
    buffett_score: Decimal = Field(..., ge=0, le=1, description="Composite Buffett score")
    recommendation: str = Field(..., description="Buy/Sell/Hold recommendation")
    confidence: Decimal = Field(..., ge=0, le=1, description="Confidence level")


# ============================================================================
# KELLY CRITERION SCHEMAS
# ============================================================================

class KellyCriterionInput(BaseModel):
    win_probability: Decimal = Field(..., ge=0, le=1, description="Probability of winning (p)")
    risk_reward_ratio: Decimal = Field(..., gt=0, description="Risk/reward ratio (b)")

    @validator('win_probability')
    def validate_probability(cls, v):
        if v <= 0 or v >= 1:
            raise ValueError("Win probability must be between 0 and 1 (exclusive)")
        return v


class KellyCriterionOutput(BaseModel):
    kelly_position_size: Decimal = Field(..., ge=0, le=1, description="Recommended position size as percentage of portfolio")
    recommendation: str = Field(..., description="Interpretation of Kelly criterion")
    warning: Optional[str] = Field(None, description="Warning if position size is too aggressive")


# ============================================================================
# API RESPONSE SCHEMAS
# ============================================================================

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int
