"""
Mineral AI Tracker - Correlation Matrix (PRD 6.0)
Version: 9.0
Description: Correlation analysis for portfolio risk management
PRD v9.0: Added sector exposure and macro correlation analysis for The Correlation Shield
"""

from decimal import Decimal, getcontext
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import numpy as np
from dataclasses import dataclass

# Set high precision for financial calculations
getcontext().prec = 10


@dataclass
class CorrelationResult:
    """Result of correlation analysis between two assets"""
    asset1: str
    asset2: str
    correlation: float
    p_value: float
    risk_level: str  # "low", "medium", "high", "critical"


@dataclass
class SectorExposure:
    """Sector exposure result"""
    sector: str
    exposure_pct: float
    risk_level: str  # "low", "medium", "high"


@dataclass
class MacroCorrelation:
    """Macro correlation result"""
    asset: str
    macro_indicator: str  # "DXY", "US10Y", "COPPER", "GOLD"
    correlation: float
    beta: float  # Sensitivity to macro factor


class CorrelationMatrix:
    """
    Correlation Matrix Calculator - Portfolio risk analysis
    
    Warns about over-correlated holdings and suggests hedge positions
    to reduce portfolio's systematic risk.
    """
    
    def __init__(self, correlation_threshold: float = 0.7):
        """
        Initialize correlation matrix calculator
        
        Args:
            correlation_threshold: Threshold for warning about high correlation (default 0.7)
        """
        self.correlation_threshold = correlation_threshold
        logger.info(f"Correlation Matrix initialized (threshold: {correlation_threshold})")
    
    def calculate_correlation(
        self,
        returns1: List[float],
        returns2: List[float]
    ) -> float:
        """
        Calculate Pearson correlation coefficient between two return series
        
        Args:
            returns1: Returns for asset 1
            returns2: Returns for asset 2
        
        Returns:
            Correlation coefficient (-1 to 1)
        """
        if len(returns1) != len(returns2) or len(returns1) < 2:
            return 0.0
        
        try:
            # Convert to numpy arrays
            arr1 = np.array(returns1)
            arr2 = np.array(returns2)
            
            # Calculate correlation
            correlation = np.corrcoef(arr1, arr2)[0, 1]
            
            # Handle NaN
            if np.isnan(correlation):
                return 0.0
            
            return float(correlation)
        
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.0
    
    def calculate_portfolio_correlation_matrix(
        self,
        asset_returns: Dict[str, List[float]]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate full correlation matrix for portfolio
        
        Args:
            asset_returns: Dictionary mapping asset tickers to return series
        
        Returns:
            Dictionary of dictionaries with correlation coefficients
        """
        assets = list(asset_returns.keys())
        correlation_matrix = {}
        
        for asset1 in assets:
            correlation_matrix[asset1] = {}
            for asset2 in assets:
                if asset1 == asset2:
                    correlation_matrix[asset1][asset2] = 1.0
                else:
                    correlation = self.calculate_correlation(
                        asset_returns[asset1],
                        asset_returns[asset2]
                    )
                    correlation_matrix[asset1][asset2] = correlation
        
        logger.info(f"Calculated correlation matrix for {len(assets)} assets")
        return correlation_matrix
    
    def identify_high_correlations(
        self,
        correlation_matrix: Dict[str, Dict[str, float]]
    ) -> List[CorrelationResult]:
        """
        Identify pairs with high correlation (above threshold)
        
        Args:
            correlation_matrix: Correlation matrix
        
        Returns:
            List of high correlation results
        """
        high_correlations = []
        assets = list(correlation_matrix.keys())
        
        for i, asset1 in enumerate(assets):
            for asset2 in assets[i+1:]:  # Avoid duplicates and self-comparison
                correlation = correlation_matrix[asset1][asset2]
                
                if abs(correlation) >= self.correlation_threshold:
                    # Determine risk level
                    if abs(correlation) >= 0.9:
                        risk_level = "critical"
                    elif abs(correlation) >= 0.8:
                        risk_level = "high"
                    else:
                        risk_level = "medium"
                    
                    high_correlations.append(CorrelationResult(
                        asset1=asset1,
                        asset2=asset2,
                        correlation=correlation,
                        p_value=0.0,  # Would calculate in production
                        risk_level=risk_level
                    ))
        
        logger.info(f"Found {len(high_correlations)} high correlation pairs")
        return high_correlations
    
    def calculate_systematic_risk(
        self,
        correlation_matrix: Dict[str, Dict[str, float]],
        portfolio_weights: Dict[str, float]
    ) -> float:
        """
        Calculate portfolio's systematic risk based on correlation matrix
        
        Args:
            correlation_matrix: Correlation matrix
            portfolio_weights: Portfolio weights (sum to 1.0)
        
        Returns:
            Systematic risk score (0-1, higher = more risk)
        """
        assets = list(portfolio_weights.keys())
        systematic_risk = 0.0
        
        for i, asset1 in enumerate(assets):
            for j, asset2 in enumerate(assets):
                if i != j:
                    weight1 = portfolio_weights[asset1]
                    weight2 = portfolio_weights[asset2]
                    correlation = correlation_matrix[asset1][asset2]
                    
                    systematic_risk += weight1 * weight2 * abs(correlation)
        
        # Normalize
        systematic_risk = systematic_risk / (len(assets) * (len(assets) - 1))
        
        return min(1.0, systematic_risk)
    
    def suggest_hedge_positions(
        self,
        high_correlations: List[CorrelationResult],
        portfolio_weights: Dict[str, float],
        asset_info: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest hedge positions to reduce correlation risk (PRD v9.0 enhanced)
        
        Args:
            high_correlations: List of high correlation pairs
            portfolio_weights: Current portfolio weights
            asset_info: Additional asset info (sector, industry, type) for better hedge suggestions
        
        Returns:
            List of hedge suggestions with specific instruments and ratios
        """
        suggestions = []
        
        for result in high_correlations:
            # Determine which asset to hedge (the one with larger position)
            weight1 = portfolio_weights.get(result.asset1, 0)
            weight2 = portfolio_weights.get(result.asset2, 0)
            
            if weight1 > weight2:
                asset_to_hedge = result.asset1
                hedge_against = result.asset2
                position_weight = weight1
            else:
                asset_to_hedge = result.asset2
                hedge_against = result.asset1
                position_weight = weight2
            
            # Determine hedge instrument based on risk level and asset type
            hedge_instrument = self._determine_hedge_instrument(
                asset_to_hedge,
                result.risk_level,
                asset_info.get(asset_to_hedge, {}) if asset_info else {}
            )
            
            # Calculate hedge ratio (typically 50-100% of position)
            hedge_ratio = 0.5 if result.risk_level == "medium" else 0.7
            if result.risk_level == "critical":
                hedge_ratio = 1.0
            
            # Estimate hedge cost (simplified - in production would use actual option prices)
            hedge_cost_pct = 0.02  # 2% annual cost for options
            
            suggestions.append({
                "risk_type": "over_correlation",
                "risk_level": result.risk_level,
                "correlation": result.correlation,
                "asset1": result.asset1,
                "asset2": result.asset2,
                "asset_to_hedge": asset_to_hedge,
                "position_weight_pct": position_weight * 100,
                "hedge_instrument": hedge_instrument,
                "hedge_ratio": hedge_ratio,
                "hedge_size_pct": position_weight * hedge_ratio * 100,
                "estimated_cost_pct": hedge_cost_pct * 100,
                "suggestion": f"Hedge {hedge_ratio*100:.0f}% of {asset_to_hedge} position with {hedge_instrument}",
                "rationale": self._get_hedge_rationale(result, asset_to_hedge, hedge_instrument)
            })
        
        return suggestions
    
    def _determine_hedge_instrument(
        self,
        asset: str,
        risk_level: str,
        asset_info: Dict[str, Any]
    ) -> str:
        """
        Determine appropriate hedge instrument based on asset and risk level
        
        Args:
            asset: Ticker to hedge
            risk_level: Risk level of correlation
            asset_info: Additional asset information
        
        Returns:
            Hedge instrument recommendation
        """
        sector = asset_info.get("sector", "Unknown").lower()
        industry = asset_info.get("industry", "").lower()
        
        # Sector-specific hedge recommendations
        if "technology" in sector or "semiconductor" in industry:
            if risk_level == "critical":
                return "QQQ Put Options (Nasdaq 100)"
            else:
                return "XLK Short (Technology Sector ETF)"
        
        if "energy" in sector or "oil" in industry:
            if risk_level == "critical":
                return "USO Put Options (Oil ETF)"
            else:
                return "XLE Short (Energy Sector ETF)"
        
        if "materials" in sector or "mining" in industry:
            if risk_level == "critical":
                return "GLD (Gold ETF) - Commodity Hedge"
            else:
                return "XME Short (Materials Sector ETF)"
        
        # Default hedges based on risk level
        if risk_level == "critical":
            return "SPY Put Options (S&P 500) - Market Hedge"
        elif risk_level == "high":
            return "VIX Futures - Volatility Hedge"
        else:
            return "Cash (Reduce Position)"
    
    def _get_hedge_rationale(
        self,
        result: CorrelationResult,
        asset: str,
        hedge_instrument: str
    ) -> str:
        """
        Generate rationale for hedge recommendation
        
        Args:
            result: Correlation result
            asset: Asset being hedged
            hedge_instrument: Recommended hedge instrument
        
        Returns:
            Rationale string
        """
        if result.risk_level == "critical":
            return (
                f"CRITICAL: {asset} has {result.correlation:.2f} correlation with {result.asset2}. "
                f"This creates significant concentration risk. {hedge_instrument} provides "
                f"immediate downside protection."
            )
        elif result.risk_level == "high":
            return (
                f"HIGH: {asset} shows {result.correlation:.2f} correlation with {result.asset2}. "
                f"Consider {hedge_instrument} to reduce systematic risk."
            )
        else:
            return (
                f"MODERATE: {asset} has {result.correlation:.2f} correlation with {result.asset2}. "
                f"{hedge_instrument} provides modest risk reduction."
            )
    
    def analyze_portfolio_risk(
        self,
        asset_returns: Dict[str, List[float]],
        portfolio_weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Full portfolio risk analysis
        
        Args:
            asset_returns: Dictionary mapping tickers to return series
            portfolio_weights: Portfolio weights
        
        Returns:
            Complete risk analysis
        """
        # Calculate correlation matrix
        correlation_matrix = self.calculate_portfolio_correlation_matrix(asset_returns)
        
        # Identify high correlations
        high_correlations = self.identify_high_correlations(correlation_matrix)
        
        # Calculate systematic risk
        systematic_risk = self.calculate_systematic_risk(correlation_matrix, portfolio_weights)
        
        # Suggest hedge positions
        hedge_suggestions = self.suggest_hedge_positions(high_correlations, portfolio_weights)
        
        # Determine overall risk level
        if systematic_risk >= 0.8:
            overall_risk = "critical"
        elif systematic_risk >= 0.6:
            overall_risk = "high"
        elif systematic_risk >= 0.4:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        return {
            "systematic_risk": systematic_risk,
            "risk_level": overall_risk,
            "correlation_matrix": correlation_matrix,
            "high_correlations": [
                {
                    "asset1": r.asset1,
                    "asset2": r.asset2,
                    "correlation": r.correlation,
                    "risk_level": r.risk_level
                }
                for r in high_correlations
            ],
            "hedge_suggestions": hedge_suggestions,
            "analyzed_at": datetime.now().isoformat()
        }


class SectorExposureAnalyzer:
    """
    Analyzes portfolio sector concentration to identify over-exposure risks
    """
    
    def __init__(self, threshold_pct: float = 30.0):
        """
        Initialize sector exposure analyzer
        
        Args:
            threshold_pct: Warning threshold for sector concentration (default 30%)
        """
        self.threshold_pct = threshold_pct
        logger.info(f"Sector Exposure Analyzer initialized (threshold: {threshold_pct}%)")
    
    def calculate_sector_exposure(
        self,
        portfolio_positions: Dict[str, Dict[str, Any]]
    ) -> List[SectorExposure]:
        """
        Calculate sector exposure from portfolio positions
        
        Args:
            portfolio_positions: Dictionary mapping tickers to position data
                                  (must include sector, value, weight)
        
        Returns:
            List of sector exposures with risk levels
        """
        sector_values: Dict[str, float] = {}
        total_value = 0.0
        
        # Aggregate values by sector
        for ticker, position in portfolio_positions.items():
            sector = position.get("sector", "Unknown")
            value = position.get("value", 0)
            weight = position.get("weight", 0)
            
            if value > 0:
                sector_values[sector] = sector_values.get(sector, 0) + value
                total_value += value
        
        # Calculate percentages
        exposures = []
        for sector, value in sector_values.items():
            exposure_pct = (value / total_value * 100) if total_value > 0 else 0
            
            # Determine risk level
            if exposure_pct >= self.threshold_pct:
                risk_level = "high"
            elif exposure_pct >= self.threshold_pct * 0.7:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            exposures.append(SectorExposure(
                sector=sector,
                exposure_pct=exposure_pct,
                risk_level=risk_level
            ))
        
        # Sort by exposure (highest first)
        exposures.sort(key=lambda x: x.exposure_pct, reverse=True)
        
        logger.info(f"Calculated sector exposure for {len(exposures)} sectors")
        return exposures
    
    def identify_concentration_risks(
        self,
        exposures: List[SectorExposure]
    ) -> List[str]:
        """
        Identify sectors with concerning concentration
        
        Args:
            exposures: List of sector exposures
        
        Returns:
            List of risk warnings
        """
        risks = []
        
        for exposure in exposures:
            if exposure.risk_level == "high":
                risks.append(
                    f"CRITICAL: {exposure.sector} concentration at {exposure.exposure_pct:.1f}% "
                    f"exceeds threshold of {self.threshold_pct}%"
                )
            elif exposure.risk_level == "medium":
                risks.append(
                    f"WARNING: {exposure.sector} concentration at {exposure.exposure_pct:.1f}% "
                    f"is approaching threshold"
                )
        
        return risks


class MacroCorrelationAnalyzer:
    """
    Analyzes portfolio correlation against macro indicators (DXY, US10Y, commodities)
    """
    
    MACRO_INDICATORS = {
        "DXY": "US Dollar Index",
        "US10Y": "US 10-Year Treasury Yield",
        "COPPER": "Copper Index",
        "GOLD": "Gold Price",
    }
    
    def __init__(self):
        """Initialize macro correlation analyzer"""
        logger.info("Macro Correlation Analyzer initialized")
    
    def calculate_macro_correlation(
        self,
        asset_returns: Dict[str, List[float]],
        macro_returns: Dict[str, List[float]]
    ) -> List[MacroCorrelation]:
        """
        Calculate correlation between assets and macro indicators
        
        Args:
            asset_returns: Dictionary mapping tickers to return series
            macro_returns: Dictionary mapping macro indicators to return series
        
        Returns:
            List of macro correlations with beta values
        """
        correlations = []
        
        for asset, returns in asset_returns.items():
            for macro, macro_ret in macro_returns.items():
                if macro not in self.MACRO_INDICATORS:
                    continue
                
                if len(returns) != len(macro_ret) or len(returns) < 20:
                    continue
                
                try:
                    # Calculate correlation
                    corr = np.corrcoef(returns, macro_ret)[0, 1]
                    
                    # Calculate beta (sensitivity)
                    # Beta = Cov(asset, macro) / Var(macro)
                    if np.var(macro_ret) > 0:
                        beta = np.cov(returns, macro_ret)[0, 1] / np.var(macro_ret)
                    else:
                        beta = 0.0
                    
                    correlations.append(MacroCorrelation(
                        asset=asset,
                        macro_indicator=macro,
                        correlation=float(corr) if not np.isnan(corr) else 0.0,
                        beta=float(beta) if not np.isnan(beta) else 0.0
                    ))
                except Exception as e:
                    logger.warning(f"Failed to calculate macro correlation for {asset} vs {macro}: {e}")
        
        logger.info(f"Calculated {len(correlations)} macro correlations")
        return correlations
    
    def identify_systematic_risks(
        self,
        correlations: List[MacroCorrelation]
    ) -> List[str]:
        """
        Identify systematic risks from macro correlations
        
        Args:
            correlations: List of macro correlations
        
        Returns:
            List of risk warnings
        """
        risks = []
        
        for corr in correlations:
            macro_name = self.MACRO_INDICATORS.get(corr.macro_indicator, corr.macro_indicator)
            
            # High positive correlation with DXY is bad for commodities
            if corr.macro_indicator == "DXY" and abs(corr.correlation) > 0.7:
                risks.append(
                    f"WARNING: {corr.asset} has high correlation ({corr.correlation:.2f}) "
                    f"with {macro_name} - commodities typically move inversely"
                )
            
            # High sensitivity to interest rates
            if corr.macro_indicator == "US10Y" and abs(corr.beta) > 1.5:
                direction = "benefits from" if corr.beta > 0 else "hurt by"
                risks.append(
                    f"WARNING: {corr.asset} has high beta ({corr.beta:.2f}) to {macro_name} - "
                    f"portfolio {direction} rate changes"
                )
            
            # Commodity concentration risk
            if corr.macro_indicator in ["COPPER", "GOLD"] and abs(corr.correlation) > 0.8:
                risks.append(
                    f"WARNING: {corr.asset} has high correlation ({corr.correlation:.2f}) "
                    f"with {macro_name} - commodity concentration risk"
                )
        
        return risks
