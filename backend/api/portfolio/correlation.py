"""
Mineral AI Tracker - Portfolio Correlation API (PRD v9.0 Phase 2)
Version: 9.0
Description: API endpoints for correlation analysis and hedge recommendations
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from loguru import logger

from quant.correlation_matrix import (
    CorrelationMatrix,
    SectorExposureAnalyzer,
    MacroCorrelationAnalyzer,
)
from utils.database import get_db_connection
from api.deps import get_current_user

router = APIRouter(prefix="/api/portfolio/correlation", tags=["portfolio-correlation"])


# ============================================================================
# Pydantic Models
# ============================================================================

class CorrelationAnalysisRequest(BaseModel):
    """Request for correlation analysis"""
    tickers: List[str] = Field(..., description="List of tickers to analyze")
    period: str = Field("1y", description="Time period for historical data")


class HedgeRecommendationRequest(BaseModel):
    """Request for hedge recommendations"""
    portfolio_positions: Dict[str, Dict[str, Any]] = Field(..., description="Portfolio positions with sector, value, weight")


class CorrelationAnalysisResponse(BaseModel):
    """Response for correlation analysis"""
    systematic_risk: float
    risk_level: str
    correlation_matrix: Dict[str, Dict[str, float]]
    high_correlations: List[Dict[str, Any]]
    hedge_suggestions: List[Dict[str, Any]]
    analyzed_at: str


class SectorExposureResponse(BaseModel):
    """Response for sector exposure analysis"""
    exposures: List[Dict[str, Any]]
    concentration_risks: List[str]
    analyzed_at: str


class MacroCorrelationResponse(BaseModel):
    """Response for macro correlation analysis"""
    correlations: List[Dict[str, Any]]
    systematic_risks: List[str]
    analyzed_at: str


class HedgeRecommendationResponse(BaseModel):
    """Response for AI-powered hedge recommendations"""
    recommendations: List[Dict[str, Any]]
    confidence_score: float
    reasoning: str
    analyzed_at: str


# ============================================================================
# Database Helpers
# ============================================================================

# Critical Hotfix: Removed local get_db_connection with hardcoded credentials.
# Now using shared utils.database.get_db_connection (env-driven).


def get_portfolio_positions(user_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Get current portfolio positions from ShadowPortfolio for a specific user.
    
    Critical Hotfix: Added user_id parameter for application-level data isolation.
    
    Args:
        user_id: User ID to filter portfolio by
    
    Returns:
        Dictionary mapping tickers to position data
    """
    positions = {}
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Critical Hotfix: Add user_id filtering for application-level data isolation
                cur.execute("""
                    SELECT asset_ticker, asset_name, shares, price_per_share,
                           total_value, ai_recommendation, executed_at
                    FROM paper_trades
                    WHERE is_closed = false AND user_id = %s
                    ORDER BY executed_at DESC
                """, (user_id,))
                rows = cur.fetchall()
                
                for row in rows:
                    ticker = row['asset_ticker']
                    positions[ticker] = {
                        "ticker": ticker,
                        "name": row['asset_name'],
                        "shares": float(row['shares']),
                        "price": float(row['price_per_share']),
                        "value": float(row['total_value']),
                        "recommendation": row['ai_recommendation'],
                        "executed_at": row['executed_at'].isoformat(),
                    }
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to get portfolio positions: {e}")
    
    return positions


def get_historical_returns(tickers: List[str], period: str = "1y") -> Dict[str, List[float]]:
    """
    Get historical returns for correlation analysis
    
    Args:
        tickers: List of tickers
        period: Time period (1y, 6m, 3m)
    
    Returns:
        Dictionary mapping tickers to return series
    """
    returns = {}
    
    # In production, this would fetch from FMP, Yahoo Finance, or other data sources
    # For now, return mock data
    import random
    
    days = 252 if period == "1y" else 126 if period == "6m" else 63
    
    for ticker in tickers:
        # Generate mock returns (in production, fetch real data)
        base_return = random.gauss(0.0005, 0.02)  # Daily returns
        returns[ticker] = [base_return + random.gauss(0, 0.01) for _ in range(days)]
    
    return returns


def get_macro_returns(period: str = "1y") -> Dict[str, List[float]]:
    """
    Get macro indicator returns for correlation analysis
    
    Args:
        period: Time period
    
    Returns:
        Dictionary mapping indicators to return series
    """
    # In production, fetch real macro data from FRED, Bloomberg, etc.
    # For now, return mock data
    import random
    
    days = 252 if period == "1y" else 126 if period == "6m" else 63
    
    return {
        "DXY": [random.gauss(0.0001, 0.005) for _ in range(days)],
        "US10Y": [random.gauss(0.0002, 0.008) for _ in range(days)],
        "COPPER": [random.gauss(0.0003, 0.015) for _ in range(days)],
        "GOLD": [random.gauss(0.0002, 0.012) for _ in range(days)],
    }


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/analysis", response_model=CorrelationAnalysisResponse)
async def get_correlation_analysis(
    tickers: str = "",
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get full correlation analysis for portfolio
    
    Query param: tickers (comma-separated list, or empty to use portfolio)
    """
    try:
        user_id = current_user["id"]  # Critical Hotfix: Extract user_id from auth context
        # Get tickers from query param or portfolio
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        else:
            positions = get_portfolio_positions(user_id)
            ticker_list = list(positions.keys())
        
        if not ticker_list:
            raise HTTPException(status_code=400, detail="No tickers provided")
        
        # Get historical returns
        asset_returns = get_historical_returns(ticker_list)
        
        # Calculate portfolio weights
        positions = get_portfolio_positions(user_id)
        total_value = sum(p.get("value", 0) for p in positions.values())
        portfolio_weights = {
            ticker: positions.get(ticker, {}).get("value", 0) / total_value if total_value > 0 else 0
            for ticker in ticker_list
        }
        
        # Get asset info (sector, industry)
        asset_info = {}
        for ticker in ticker_list:
            try:
                from utils.fmp_client import fetch_fmp_fundamentals
                fmp_data = await fetch_fmp_fundamentals(ticker=ticker)
                if fmp_data:
                    asset_info[ticker] = {
                        "sector": fmp_data.get("industry"),
                        "industry": fmp_data.get("sector"),
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch FMP data for {ticker}: {e}")
        
        # Run correlation analysis
        correlation_matrix = CorrelationMatrix()
        analysis = correlation_matrix.analyze_portfolio_risk(
            asset_returns=asset_returns,
            portfolio_weights=portfolio_weights
        )
        
        # Enhance hedge suggestions with asset info
        high_correlations = [
            CorrelationResult(**r) for r in analysis.get("high_correlations", [])
        ]
        enhanced_hedges = correlation_matrix.suggest_hedge_positions(
            high_correlations,
            portfolio_weights,
            asset_info=asset_info
        )
        
        return CorrelationAnalysisResponse(
            systematic_risk=analysis["systematic_risk"],
            risk_level=analysis["risk_level"],
            correlation_matrix=analysis["correlation_matrix"],
            high_correlations=analysis["high_correlations"],
            hedge_suggestions=enhanced_hedges,
            analyzed_at=analysis["analyzed_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Correlation analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sector-exposure", response_model=SectorExposureResponse)
async def get_sector_exposure(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """Get sector exposure analysis for current portfolio"""
    try:
        user_id = current_user["id"]  # Critical Hotfix: Extract user_id from auth context
        positions = get_portfolio_positions(user_id)
        
        if not positions:
            raise HTTPException(status_code=404, detail="No portfolio positions found")
        
        # Add sector info to positions
        for ticker in list(positions.keys()):
            try:
                from utils.fmp_client import fetch_fmp_fundamentals
                fmp_data = await fetch_fmp_fundamentals(ticker=ticker)
                if fmp_data:
                    positions[ticker]["sector"] = fmp_data.get("industry", "Unknown")
                    positions[ticker]["industry"] = fmp_data.get("sector", "")
            except Exception as e:
                logger.warning(f"Failed to fetch sector info for {ticker}: {e}")
                positions[ticker]["sector"] = "Unknown"
        
        # Calculate sector exposure
        analyzer = SectorExposureAnalyzer(threshold_pct=30.0)
        exposures = analyzer.calculate_sector_exposure(positions)
        risks = analyzer.identify_concentration_risks(exposures)
        
        return SectorExposureResponse(
            exposures=[
                {
                    "sector": e.sector,
                    "exposure_pct": e.exposure_pct,
                    "risk_level": e.risk_level
                }
                for e in exposures
            ],
            concentration_risks=risks,
            analyzed_at=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sector exposure analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro-correlation", response_model=MacroCorrelationResponse)
async def get_macro_correlation(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """Get macro correlation analysis for current portfolio"""
    try:
        user_id = current_user["id"]  # Critical Hotfix: Extract user_id from auth context
        positions = get_portfolio_positions(user_id)
        tickers = list(positions.keys())
        
        if not tickers:
            raise HTTPException(status_code=404, detail="No portfolio positions found")
        
        # Get historical returns
        asset_returns = get_historical_returns(tickers)
        macro_returns = get_macro_returns()
        
        # Calculate macro correlations
        analyzer = MacroCorrelationAnalyzer()
        correlations = analyzer.calculate_macro_correlation(asset_returns, macro_returns)
        risks = analyzer.identify_systematic_risks(correlations)
        
        return MacroCorrelationResponse(
            correlations=[
                {
                    "asset": c.asset,
                    "macro_indicator": c.macro_indicator,
                    "indicator_name": analyzer.MACRO_INDICATORS.get(c.macro_indicator, c.macro_indicator),
                    "correlation": c.correlation,
                    "beta": c.beta
                }
                for c in correlations
            ],
            systematic_risks=risks,
            analyzed_at=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Macro correlation analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hedge-recommendation", response_model=HedgeRecommendationResponse)
async def get_hedge_recommendation(
    request: HedgeRecommendationRequest,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get AI-powered hedge recommendations using Llama-3
    
    This uses the HedgeOrchestrator to analyze correlation risks and
    generate hedge recommendations with reasoning.
    """
    try:
        # Get correlation analysis
        tickers = list(request.portfolio_positions.keys())
        asset_returns = get_historical_returns(tickers)
        
        # Calculate portfolio weights
        total_value = sum(p.get("value", 0) for p in request.portfolio_positions.values())
        portfolio_weights = {
            ticker: request.portfolio_positions.get(ticker, {}).get("value", 0) / total_value if total_value > 0 else 0
            for ticker in tickers
        }
        
        # Run correlation analysis
        correlation_matrix = CorrelationMatrix()
        analysis = correlation_matrix.analyze_portfolio_risk(
            asset_returns=asset_returns,
            portfolio_weights=portfolio_weights
        )
        
        # Use existing hedge suggestions as baseline
        high_correlations = [
            CorrelationResult(**r) for r in analysis.get("high_correlations", [])
        ]
        hedge_suggestions = correlation_matrix.suggest_hedge_positions(
            high_correlations,
            portfolio_weights,
            asset_info=request.portfolio_positions
        )
        
        # In production, this would use Llama-3 to generate AI-powered reasoning
        # For now, return the baseline recommendations
        reasoning = (
            f"Portfolio systematic risk: {analysis['risk_level']} ({analysis['systematic_risk']:.2f}). "
            f"Found {len(hedge_suggestions)} hedge opportunities to reduce concentration risk. "
            f"Recommend prioritizing critical and high-risk hedges first."
        )
        
        return HedgeRecommendationResponse(
            recommendations=hedge_suggestions,
            confidence_score=0.75,  # Baseline confidence
            reasoning=reasoning,
            analyzed_at=analysis["analyzed_at"]
        )
    except Exception as e:
        logger.error(f"Hedge recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]
