"""
Mineral AI Tracker - Assets API (PRD v3.1)
Version: 3.1
Description: API endpoint for adding assets with yfinance backfill
PRD v8.8: Added asset profile endpoint for deep dive view
Critical Hotfix: Added authentication dependency to enforce JWT validation
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio
import os
import httpx
from loguru import logger

# Import database connection (using local PostgreSQL)
import psycopg2
from psycopg2.extras import RealDictCursor

# Import vault for FMP API key decryption
from utils.vault import decrypt
from api.deps import get_current_user


# ============================================================================
# Pydantic Models
# ============================================================================

class AssetAddRequest(BaseModel):
    """Request model for adding a new asset"""
    ticker: str = Field(..., min_length=1, max_length=20, description="Stock ticker symbol")
    name: Optional[str] = Field(None, max_length=255, description="Company name (optional, will be fetched)")
    isin: Optional[str] = Field(None, max_length=20, description="ISIN code (optional)")
    
    @validator('ticker')
    def ticker_uppercase(cls, v):
        return v.upper()


class AssetAddResponse(BaseModel):
    """Response model for asset addition"""
    success: bool
    asset_id: Optional[str] = None
    message: str
    buffett_score: Optional[float] = None
    confidence: Optional[float] = None
    backfill_status: str


class AssetProfileResponse(BaseModel):
    """Response model for asset deep dive profile (PRD v8.8)"""
    ticker: str
    name: Optional[str] = None
    description: Optional[str] = None
    ceo: Optional[str] = None
    industry: Optional[str] = None
    sector: Optional[str] = None
    market_cap: Optional[float] = None
    price: Optional[float] = None
    pe_ratio: Optional[float] = None
    ev_ebit: Optional[float] = None
    roe: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    eps: Optional[float] = None
    next_earnings_date: Optional[str] = None
    upcoming_earnings: List[Dict[str, Any]] = []
    currency: Optional[str] = None
    exchange: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    employees: Optional[int] = None


# ============================================================================
# Database Helper Functions
# ============================================================================

def get_db_connection():
    """Get database connection"""
    # Use keyword parameters to avoid DSN parsing issues
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="mineral_ai_tracker",
        user="mineral_user",
        password="mineralpass123",
        cursor_factory=RealDictCursor
    )


def check_asset_exists(ticker: str) -> bool:
    """Check if asset already exists"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM assets WHERE ticker = %s", (ticker,))
            return cur.fetchone() is not None
    finally:
        conn.close()


def insert_asset(asset_data: dict) -> str:
    """Insert new asset into database"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO assets (
                    ticker, name, asset_type, country_code, exchange,
                    isin, status, discovery_source, created_at
                ) VALUES (
                    %(ticker)s, %(name)s, %(asset_type)s, %(country_code)s,
                    %(exchange)s, %(isin)s, %(status)s, %(discovery_source)s, NOW()
                ) RETURNING id
            """, asset_data)
            conn.commit()
            return str(cur.fetchone()['id'])
    finally:
        conn.close()


# ============================================================================
# yfinance Backfill (Simplified)
# ============================================================================

async def backfill_asset_data(asset_id: str, ticker: str):
    """
    Backfill historical data for newly added asset
    In production, this would use yfinance to fetch 5 years of data
    
    Args:
        asset_id: Asset UUID
        ticker: Stock ticker
    """
    logger.info(f"Starting backfill for {ticker} (asset_id: {asset_id})")
    
    try:
        # In production, use yfinance:
        # import yfinance as yf
        # ticker_obj = yf.Ticker(ticker)
        # hist = ticker_obj.history(period="5y")
        # info = ticker_obj.info
        
        # For now, simulate backfill with placeholder data
        await asyncio.sleep(2)  # Simulate API call
        
        # Update asset with fetched data (placeholder)
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Update with placeholder financial data
                cur.execute("""
                    UPDATE assets SET
                        current_price = 100.00,
                        market_cap_million = 500.0,
                        pe_ratio = 15.5,
                        buffett_score = 0.65,
                        confidence_score = 0.70,
                        last_price_update = NOW(),
                        last_score_update = NOW()
                    WHERE id = %s
                """, (asset_id,))
                conn.commit()
                
                # Add placeholder tags
                cur.execute("""
                    INSERT INTO asset_tags (asset_id, tag_name, tag_category, auto_generated, confidence)
                    VALUES 
                        (%s, 'Copper', 'commodity', TRUE, 0.80),
                        (%s, 'Exploration', 'stage', TRUE, 0.75)
                """, (asset_id, asset_id))
                conn.commit()
                
        finally:
            conn.close()
        
        logger.info(f"Backfill complete for {ticker}")
        
    except Exception as e:
        logger.error(f"Error backfilling data for {ticker}: {e}")


# ============================================================================
# Rate Limiting (In-Memory)
# ============================================================================

class RateLimiter:
    """Simple in-memory rate limiter"""
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if request is allowed"""
        now = datetime.now()
        
        # Clean old requests
        if user_id in self.requests:
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if now - req_time < timedelta(seconds=self.window_seconds)
            ]
        else:
            self.requests[user_id] = []
        
        # Check if under limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Add request
        self.requests[user_id].append(now)
        return True


# Global rate limiter instance (max 5 assets per minute)
rate_limiter = RateLimiter(max_requests=5, window_seconds=60)


# ============================================================================
# FMP API Helpers (PRD v8.8)
# ============================================================================

FMP_BASE = "https://financialmodelingprep.com/api/v3"
FMP_TIMEOUT = 8.0


def _get_fmp_api_key() -> Optional[str]:
    """Resolve FMP API key from vault or env var"""
    # Try environment variable first
    key = os.environ.get("FMP_API_KEY")
    if key:
        return key

    # Try loading from database (vault)
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT fmp_api_key FROM system_settings LIMIT 1")
                row = cur.fetchone()
                if row and row.get("fmp_api_key"):
                    encrypted = row["fmp_api_key"]
                    decrypted = decrypt(encrypted)
                    if decrypted:
                        return decrypted
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"Failed to load FMP key from vault: {e}")

    return None


async def _fetch_fmp_profile(ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch company profile from FMP"""
    api_key = _get_fmp_api_key()
    if not api_key:
        logger.warning("FMP API key not configured")
        return None

    try:
        async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
            resp = await client.get(
                f"{FMP_BASE}/profile/{ticker}",
                params={"apikey": api_key}
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0]
            return None
    except Exception as e:
        logger.warning(f"FMP profile fetch failed for {ticker}: {e}")
        return None


async def _fetch_fmp_ratios(ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch financial ratios from FMP"""
    api_key = _get_fmp_api_key()
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
            resp = await client.get(
                f"{FMP_BASE}/ratios-ttm/{ticker}",
                params={"apikey": api_key}
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0]
            return None
    except Exception as e:
        logger.warning(f"FMP ratios fetch failed for {ticker}: {e}")
        return None


async def _fetch_fmp_earnings(ticker: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch earnings calendar from FMP"""
    api_key = _get_fmp_api_key()
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
            resp = await client.get(
                f"{FMP_BASE}/historical/earning_calendar/{ticker}",
                params={"apikey": api_key}
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                # Sort by date and return next 3 upcoming earnings
                sorted_data = sorted(
                    [e for e in data if e.get("date")],
                    key=lambda x: x["date"]
                )
                return sorted_data[:3]
            return None
    except Exception as e:
        logger.warning(f"FMP earnings fetch failed for {ticker}: {e}")
        return None


# ============================================================================
# API Router
# ============================================================================

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.post("/add", response_model=AssetAddResponse)
async def add_asset(
    request: AssetAddRequest,
    background_tasks: BackgroundTasks,
    user_id: str = "anonymous",  # In production, get from auth
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Add a new asset with automatic backfill
    
    - Validates ticker
    - Checks if asset already exists
    - Inserts asset with status 'user_added'
    - Triggers async backfill job
    - Returns initial Buffett Score within 10 seconds
    """
    
    # Rate limiting check
    if not rate_limiter.is_allowed(user_id):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: Max 5 assets per minute"
        )
    
    logger.info(f"Adding asset: {request.ticker}")
    
    # Check if asset already exists
    if check_asset_exists(request.ticker):
        raise HTTPException(
            status_code=409,
            detail=f"Asset with ticker {request.ticker} already exists"
        )
    
    try:
        # Insert asset with user_added status
        asset_data = {
            "ticker": request.ticker,
            "name": request.name or request.ticker,  # Use ticker as fallback
            "asset_type": "stock",
            "country_code": "SE",  # Default, would be fetched from yfinance
            "exchange": "OMX",  # Default, would be fetched from yfinance
            "isin": request.isin,
            "status": "user_added",
            "discovery_source": "manual_user_add"
        }
        
        asset_id = insert_asset(asset_data)
        
        # Trigger backfill in background
        background_tasks.add_task(backfill_asset_data, asset_id, request.ticker)
        
        # Return immediate response with placeholder score
        # Real score will be available after backfill completes
        return AssetAddResponse(
            success=True,
            asset_id=asset_id,
            message=f"Asset {request.ticker} added successfully. Backfill in progress.",
            buffett_score=None,  # Will be available after backfill
            confidence=None,
            backfill_status="in_progress"
        )
        
    except Exception as e:
        logger.error(f"Error adding asset: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error adding asset: {str(e)}"
        )


@router.get("/")
async def get_all_assets(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get all assets with full details
    Used by frontend assets page
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    id, ticker, name, asset_type, country_code, exchange,
                    current_price, buffett_score, confidence_score,
                    price_change_30d, created_at
                FROM assets
                ORDER BY buffett_score DESC
            """)
            assets = cur.fetchall()
            
            result = []
            for asset in assets:
                # Add placeholder fields for frontend compatibility
                result.append({
                    "id": str(asset['id']),
                    "ticker": asset['ticker'],
                    "name": asset['name'],
                    "asset_type": asset['asset_type'],
                    "commodity_type": "copper",  # Placeholder, would be from tags
                    "country_code": asset['country_code'],
                    "exchange": asset['exchange'],
                    "buffett_score": float(asset['buffett_score'] or 0),
                    "confidence_score": float(asset['confidence_score'] or 0),
                    "current_price": float(asset['current_price'] or 0),
                    "price_change_30d": float(asset['price_change_30d'] or 0),
                    "trading_url": f"https://www.avanza.se/aktier/om-aktien.html/{asset['ticker']}",
                    "avanza_verified": True,  # Placeholder, would be from verification check
                    "avanza_url": f"https://www.avanza.se/aktier/om-aktien.html/{asset['ticker']}"
                })
            
            return {"assets": result, "count": len(result)}
            
    finally:
        conn.close()


@router.get("/scouted")
async def get_scouted_assets(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get all assets with status 'scouted'
    These are assets discovered by AI Scout
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, ticker, name, status, discovery_source, created_at
                FROM assets
                WHERE status = 'scouted'
                ORDER BY created_at DESC
            """)
            assets = cur.fetchall()
            
            # Get tags for each asset
            result = []
            for asset in assets:
                cur.execute("""
                    SELECT tag_name, tag_category, confidence
                    FROM asset_tags
                    WHERE asset_id = %s
                """, (asset['id'],))
                tags = cur.fetchall()
                
                result.append({
                    **asset,
                    "tags": tags
                })
            
            return {"assets": result, "count": len(result)}
            
    finally:
        conn.close()


@router.get("/{ticker}")
async def get_asset(
    ticker: str,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """Get asset details by ticker"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM assets WHERE ticker = %s
            """, (ticker.upper(),))
            asset = cur.fetchone()

            if not asset:
                raise HTTPException(
                    status_code=404,
                    detail=f"Asset {ticker} not found"
                )

            # Get tags
            cur.execute("""
                SELECT tag_name, tag_category, confidence
                FROM asset_tags
                WHERE asset_id = %s
            """, (asset['id'],))
            tags = cur.fetchall()

            return {**asset, "tags": tags}

    finally:
        conn.close()


@router.get("/profile/{ticker}", response_model=AssetProfileResponse)
async def get_asset_profile(
    ticker: str,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get comprehensive asset profile for deep dive view (PRD v8.8)

    Aggregates data from FMP:
    - Company profile (CEO, description, industry)
    - Financial ratios (P/E, ROE, margins, EV/EBIT)
    - Earnings calendar (next 3 report dates)
    """
    ticker = ticker.upper()

    # Fetch all data in parallel
    profile_data, ratios_data, earnings_data = await asyncio.gather(
        _fetch_fmp_profile(ticker),
        _fetch_fmp_ratios(ticker),
        _fetch_fmp_earnings(ticker),
        return_exceptions=True
    )

    # Handle exceptions
    if isinstance(profile_data, Exception):
        logger.warning(f"FMP profile error: {profile_data}")
        profile_data = None
    if isinstance(ratios_data, Exception):
        logger.warning(f"FMP ratios error: {ratios_data}")
        ratios_data = None
    if isinstance(earnings_data, Exception):
        logger.warning(f"FMP earnings error: {earnings_data}")
        earnings_data = None

    # Build response
    response = AssetProfileResponse(
        ticker=ticker,
        name=profile_data.get("companyName") if profile_data else None,
        description=profile_data.get("description") if profile_data else None,
        ceo=profile_data.get("ceo") if profile_data else None,
        industry=profile_data.get("industry") if profile_data else None,
        sector=profile_data.get("sector") if profile_data else None,
        market_cap=profile_data.get("mktCap") if profile_data else None,
        price=profile_data.get("price") if profile_data else None,
        currency=profile_data.get("currency") if profile_data else None,
        exchange=profile_data.get("exchange") if profile_data else None,
        country=profile_data.get("country") if profile_data else None,
        website=profile_data.get("website") if profile_data else None,
        employees=profile_data.get("fullTimeEmployees") if profile_data else None,
        pe_ratio=ratios_data.get("peRatioTTM") if ratios_data else None,
        ev_ebit=ratios_data.get("enterpriseValueMultipleTTM") if ratios_data else None,
        roe=ratios_data.get("roeTTM") if ratios_data else None,
        gross_margin=ratios_data.get("grossProfitMarginTTM") if ratios_data else None,
        operating_margin=ratios_data.get("operatingProfitMarginTTM") if ratios_data else None,
        net_margin=ratios_data.get("netProfitMarginTTM") if ratios_data else None,
        debt_to_equity=ratios_data.get("debtEquityRatioTTM") if ratios_data else None,
        current_ratio=ratios_data.get("currentRatioTTM") if ratios_data else None,
        eps=ratios_data.get("epsTTM") if ratios_data else None,
        next_earnings_date=earnings_data[0].get("date") if earnings_data else None,
        upcoming_earnings=earnings_data or []
    )

    return response
