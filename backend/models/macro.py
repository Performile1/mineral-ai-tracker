"""
Mineral AI Tracker - Macro Demand Models
Description: Pydantic schemas for manufacturing industry mineral demand signals
"""

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class IndustrySector(str, Enum):
    """Manufacturing industry sectors requiring critical minerals"""
    SOLAR = "Solar_Perovskite"
    GRID_STORAGE = "Grid_Storage_BESS"
    DEFENSE = "Defense_Aerospace"
    ROBOTICS = "Advanced_Robotics"
    HVAC = "HVAC_Cooling"
    SPACE = "Space_LEO"
    WATER = "Water_Desalination"
    HYDROGEN = "Hydrogen_GreenSteel"


class MineralDemandSignal(BaseModel):
    """
    Mineral demand signal from manufacturing sector analysis
    
    Used to identify supply-demand imbalances and catalyst events
    that may impact asset prices.
    """
    mineral: str = Field(..., description="e.g., Vanadium, Antimony, Neodymium")
    sector: IndustrySector
    supply_deficit_score: float = Field(..., ge=0, le=100, description="100 means extreme shortage")
    catalyst_event: str
    source_url: str
    confidence: float = Field(..., ge=0, le=1.0)
    logged_at: datetime = Field(default_factory=datetime.now)
