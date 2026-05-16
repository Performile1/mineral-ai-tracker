"""
Mineral AI Tracker - Geology Models (PRD v8.0)
Version: 8.0
Description: Pydantic V2 models for geological data validation with strict field validators
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class GeologicalData(BaseModel):
    """Geological data with strict validation to prevent AI hallucinations"""
    
    discovery_id: str = Field(..., description="Unique discovery identifier")
    
    ticker: Optional[str] = Field(None, description="Associated company ticker")
    
    commodity_type: str = Field(
        ...,
        description="Commodity type (e.g., copper, gold, lithium, nickel)"
    )
    
    copper_grade: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Kopparhalt i %"
    )
    
    gold_grade_g_t: Optional[float] = Field(
        None,
        ge=0.0,
        le=1000.0,
        description="Guldhalt i g/ton"
    )
    
    lithium_grade_ppm: Optional[float] = Field(
        None,
        ge=0.0,
        le=100000.0,
        description="Lithiumhalt i ppm"
    )
    
    nickel_grade_pct: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Nickelhalt i %"
    )
    
    tonnage: float = Field(
        ...,
        gt=0,
        description="Tonnage i miljoner ton"
    )
    
    resource_category: str = Field(
        ...,
        description="Resource category: Inferred, Indicated, Measured, Reserve"
    )
    
    depth_m: Optional[float] = Field(
        None,
        ge=0,
        description="Drill depth i meter"
    )
    
    country_code: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Landkod (ISO 3166-1 alpha-2)"
    )
    
    region: Optional[str] = Field(None, description="Region/område")
    
    discovery_date: str = Field(..., description="Datum för upptäckt (ISO 8601)")
    
    source: str = Field(..., description="Data source (e.g., SGU, NGU, GTK)")
    
    confidence_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score for geological data (0-100)"
    )
    
    @field_validator('copper_grade')
    @classmethod
    def validate_copper_grade(cls, v: Optional[float]) -> Optional[float]:
        """Hard physical barrier against AI hallucinations for copper grades"""
        if v is not None and v > 15.0:
            raise ValueError(
                f"Orimlig kopparhalt ({v}%). Max tillåtet är 15% för ekonomiskt "
                f"genomförbara projekt. Förmodligen datafel eller hallucination."
            )
        return v
    
    @field_validator('gold_grade_g_t')
    @classmethod
    def validate_gold_grade(cls, v: Optional[float]) -> Optional[float]:
        """Validate gold grade to prevent unrealistic values"""
        if v is not None and v > 100.0:
            raise ValueError(
                f"Orimlig guldhalt ({v} g/ton). Max tillåtet är 100 g/ton för "
                f"ekonomiskt genomförbara projekt."
            )
        return v
    
    @field_validator('tonnage')
    @classmethod
    def validate_tonnage(cls, v: float) -> float:
        """Validate tonnage to prevent unrealistic values"""
        if v < 0.001:
            raise ValueError("Tonnage är under 1,000 ton. Inte kommersiellt relevant.")
        return v
    
    @field_validator('resource_category')
    @classmethod
    def validate_resource_category(cls, v: str) -> str:
        """Validate resource category against standard definitions"""
        valid_categories = ['inferred', 'indicated', 'measured', 'reserve', 'probable', 'proven']
        if v.lower() not in valid_categories:
            raise ValueError(
                f"Ogiltig resource category: {v}. Måste vara en av: {', '.join(valid_categories)}"
            )
        return v


class MacroDeficitData(BaseModel):
    """Macro demand deficit data for future industries"""
    
    industry: str = Field(..., description="Industri (e.g., Solceller, Försvar, Robotik)")
    
    commodity: str = Field(..., description="Råvara (e.g., koppar, litium, nickel)")
    
    deficit_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Deficit score (0-100, högre = större brist)"
    )
    
    current_demand_m_ton: float = Field(
        ...,
        gt=0,
        description="Nuvarande efterfrågan i miljoner ton"
    )
    
    projected_demand_2030_m_ton: float = Field(
        ...,
        gt=0,
        description="Projicerad efterfrågan 2030 i miljoner ton"
    )
    
    supply_gap_m_ton: float = Field(
        ...,
        ge=0,
        description="Utbudsgap i miljoner ton"
    )
    
    price_impact_pct: Optional[float] = Field(
        None,
        ge=-100,
        le=500,
        description="Förväntat pris påverkan i %"
    )
    
    criticality_level: str = Field(
        ...,
        description="Criticality level: LOW, MEDIUM, HIGH, CRITICAL"
    )
    
    data_source: str = Field(..., description="Data source (e.g., IEA, Eurostat)")
    
    last_updated: str = Field(..., description="Senast uppdaterad (ISO 8601)")


class GeoEvent(BaseModel):
    """Geopolitical and policy events affecting mineral markets"""
    
    event_id: str = Field(..., description="Unique event identifier")
    
    event_type: str = Field(
        ...,
        description="Event type: POLICY, TRADE_WAR, SANCTION, DISCOVERY, M&A"
    )
    
    title: str = Field(..., max_length=500, description="Event title")
    
    description: str = Field(..., max_length=5000, description="Event description")
    
    affected_commodities: List[str] = Field(..., description="Lista av påverkade råvaror")
    
    affected_countries: List[str] = Field(..., description="Lista av påverkade länder")
    
    impact_score: int = Field(
        ...,
        ge=-100,
        le=100,
        description="Impact score (-100 to 100, negativ = negativ påverkan)"
    )
    
    event_date: str = Field(..., description="Datum för händelse (ISO 8601)")
    
    source: str = Field(..., description="Data source")
    
    url: Optional[str] = Field(None, description="Länk till originalkälla")
    
    embedding: Optional[List[float]] = Field(None, description="pgvector embedding för RAG")


class PersonnelEvent(BaseModel):
    """Key personnel events for insider tracking"""
    
    event_id: str = Field(..., description="Unique event identifier")
    
    person_name: str = Field(..., description="Personens namn")
    
    person_role: str = Field(..., description="Roll (e.g., VD, Geolog, CFO)")
    
    company_ticker: str = Field(..., description="Företagets ticker")
    
    event_type: str = Field(
        ...,
        description="Event type: HIRED, RESIGNED, PROMOTED, STOCK_PURCHASE, STOCK_SALE"
    )
    
    event_date: str = Field(..., description="Datum för händelse (ISO 8601)")
    
    previous_company: Optional[str] = Field(None, description="Tidigare företag (om byte)")
    
    insider_signal: Optional[str] = Field(
        None,
        description="Insider signal: BULLISH, BEARISH, NEUTRAL"
    )
    
    confidence_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score for signal (0-100)"
    )
    
    source: str = Field(..., description="Data source")
