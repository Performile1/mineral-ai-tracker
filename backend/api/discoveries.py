"""
Mineral AI Tracker - Discoveries API
Version: 6.0
Description: API endpoint for mineral discoveries
"""

from fastapi import APIRouter, HTTPException, Depends

from api.deps import get_current_user
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from loguru import logger

import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings


# ============================================================================
# Pydantic Models
# ============================================================================

class DiscoveryResponse(BaseModel):
    """Response model for discoveries"""
    id: str
    name: str
    latitude: float
    longitude: float
    commodity: str
    discovery_date: str
    status: str


class NearbyCompany(BaseModel):
    """Response model for nearby companies"""
    id: str
    name: str
    ticker: Optional[str]
    asset_type: str
    distance_km: float
    buffett_score: float
    trading_url: str


class DiscoveryDetailResponse(BaseModel):
    """Response model for discovery details with nearby companies"""
    discovery: DiscoveryResponse
    nearby_companies: List[NearbyCompany]


# ============================================================================
# Database Helper Functions
# ============================================================================

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB,
        cursor_factory=RealDictCursor
    )


# ============================================================================
# API Router
# ============================================================================

router = APIRouter(prefix="/api/discoveries", tags=["discoveries"])


@router.get("/")
async def get_all_discoveries(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get all mineral discoveries
    Used by frontend DiscoveryHeatmap component
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    id, name, latitude, longitude, commodity,
                    discovery_date, status
                FROM geo_events
                WHERE event_type = 'discovery'
                ORDER BY discovery_date DESC
            """)
            discoveries = cur.fetchall()
            
            result = []
            for discovery in discoveries:
                result.append({
                    "id": str(discovery['id']),
                    "name": discovery['name'],
                    "latitude": float(discovery['latitude']),
                    "longitude": float(discovery['longitude']),
                    "commodity": discovery['commodity'],
                    "discovery_date": discovery['discovery_date'].isoformat() if discovery['discovery_date'] else "",
                    "status": discovery['status']
                })
            
            return {"discoveries": result, "count": len(result)}
            
    finally:
        conn.close()


@router.get("/{discovery_id}/nearby")
async def get_nearby_companies(
    discovery_id: str,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get nearby companies for a specific discovery
    Used by frontend DiscoveryHeatmap component
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get discovery details
            cur.execute("""
                SELECT latitude, longitude, commodity
                FROM geo_events
                WHERE id = %s AND event_type = 'discovery'
            """, (discovery_id,))
            discovery = cur.fetchone()
            
            if not discovery:
                raise HTTPException(
                    status_code=404,
                    detail=f"Discovery {discovery_id} not found"
                )
            
            # Get nearby companies (simple distance calculation)
            # In production, use PostGIS for proper geospatial queries
            cur.execute("""
                SELECT 
                    a.id, a.name, a.ticker, a.asset_type,
                    a.buffett_score, a.current_price
                FROM assets a
                WHERE a.commodity_type = %s
                ORDER BY a.buffett_score DESC
                LIMIT 5
            """, (discovery['commodity'],))
            companies = cur.fetchall()
            
            result = []
            for company in companies:
                # Placeholder distance calculation
                distance_km = 50.0  # In production, calculate actual distance
                
                result.append({
                    "id": str(company['id']),
                    "name": company['name'],
                    "ticker": company['ticker'],
                    "asset_type": company['asset_type'],
                    "distance_km": distance_km,
                    "buffett_score": float(company['buffett_score'] or 0),
                    "trading_url": f"https://www.avanza.se/aktier/om-aktien.html/{company['ticker']}"
                })
            
            return {"nearby_companies": result, "count": len(result)}
            
    finally:
        conn.close()


@router.get("/heatmap")
async def get_discoveries_heatmap(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get discoveries formatted for heatmap visualization
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    id, name, latitude, longitude, commodity,
                    discovery_date, status
                FROM geo_events
                WHERE event_type = 'discovery'
                ORDER BY discovery_date DESC
            """)
            discoveries = cur.fetchall()
            
            result = []
            for discovery in discoveries:
                result.append({
                    "id": str(discovery['id']),
                    "name": discovery['name'],
                    "latitude": float(discovery['latitude']),
                    "longitude": float(discovery['longitude']),
                    "commodity": discovery['commodity'],
                    "discovery_date": discovery['discovery_date'].isoformat() if discovery['discovery_date'] else "",
                    "status": discovery['status']
                })
            
            return result
            
    finally:
        conn.close()
