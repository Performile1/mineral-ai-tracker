"""
Mineral AI Tracker - Black Swan Scenario Engine (PRD 6.0)
Version: 6.0
Description: Stress testing engine for extreme event simulation
"""

from decimal import Decimal, getcontext
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from dataclasses import dataclass

# Set high precision for financial calculations
getcontext().prec = 10


@dataclass
class ScenarioImpact:
    """Impact of a scenario on a specific asset"""
    asset_id: str
    asset_ticker: str
    current_price: Decimal
    simulated_price: Decimal
    price_impact_percentage: Decimal
    value_before: Decimal
    value_after: Decimal
    value_impact_percentage: Decimal


@dataclass
class ScenarioResult:
    """Result of running a scenario on a portfolio"""
    scenario_id: str
    scenario_name: str
    portfolio_value_before: Decimal
    portfolio_value_after: Decimal
    portfolio_impact_percentage: Decimal
    asset_impacts: List[ScenarioImpact]
    simulated_at: datetime


class ScenarioEngine:
    """
    Black Swan Scenario Engine - Stress testing for extreme events
    
    Simulates extreme events (e.g., "China blocks graphite export", "Copper drops 30%")
    and calculates portfolio impact based on historical correlations.
    """
    
    def __init__(self):
        """Initialize scenario engine"""
        logger.info("Black Swan Scenario Engine initialized")
    
    def calculate_asset_impact(
        self,
        current_price: Decimal,
        price_impact_percentage: Decimal,
        historical_correlation: Decimal
    ) -> ScenarioImpact:
        """
        Calculate impact of scenario on a single asset
        
        Args:
            current_price: Current asset price
            price_impact_percentage: Scenario's price impact (e.g., -30 for 30% drop)
            historical_correlation: Historical correlation with affected commodity
        
        Returns:
            Scenario impact for the asset
        """
        # Apply correlation to determine actual impact
        # High correlation = closer to scenario impact
        # Low correlation = muted impact
        adjusted_impact = price_impact_percentage * historical_correlation
        
        # Calculate simulated price
        price_change = current_price * (adjusted_impact / Decimal("100"))
        simulated_price = current_price + price_change
        
        # Ensure price doesn't go negative
        simulated_price = max(Decimal("0.01"), simulated_price)
        
        return ScenarioImpact(
            asset_id="",
            asset_ticker="",
            current_price=current_price,
            simulated_price=simulated_price,
            price_impact_percentage=adjusted_impact,
            value_before=Decimal("0"),
            value_after=Decimal("0"),
            value_impact_percentage=Decimal("0")
        )
    
    def run_scenario(
        self,
        portfolio: List[Dict[str, Any]],
        scenario: Dict[str, Any]
    ) -> ScenarioResult:
        """
        Run a scenario on a portfolio
        
        Args:
            portfolio: List of portfolio positions with asset data
            scenario: Scenario configuration
        
        Returns:
            Scenario result with portfolio impact
        """
        logger.info(f"Running scenario: {scenario['name']}")
        
        scenario_id = scenario.get("id", "")
        scenario_name = scenario.get("name", "Unknown")
        affected_commodity = scenario.get("affected_commodity", "")
        price_impact_percentage = Decimal(str(scenario.get("price_impact_percentage", 0)))
        historical_correlation = Decimal(str(scenario.get("historical_correlation", 0.5)))
        
        portfolio_value_before = Decimal("0")
        portfolio_value_after = Decimal("0")
        asset_impacts = []
        
        for position in portfolio:
            asset_id = position.get("asset_id", "")
            asset_ticker = position.get("ticker", "")
            shares = Decimal(str(position.get("shares", 0)))
            current_price = Decimal(str(position.get("current_price", 0)))
            
            # Check if asset is affected by scenario
            asset_commodity = position.get("commodity_type", "")
            
            # If asset's commodity matches scenario's affected commodity
            if asset_commodity.lower() == affected_commodity.lower():
                correlation = historical_correlation
            else:
                # Lower correlation for different commodities
                correlation = Decimal("0.2")
            
            # Calculate impact
            impact = self.calculate_asset_impact(
                current_price,
                price_impact_percentage,
                correlation
            )
            
            impact.asset_id = asset_id
            impact.asset_ticker = asset_ticker
            
            # Calculate position values
            value_before = shares * current_price
            value_after = shares * impact.simulated_price
            value_impact = ((value_after - value_before) / value_before) * Decimal("100")
            
            impact.value_before = value_before
            impact.value_after = value_after
            impact.value_impact_percentage = value_impact
            
            portfolio_value_before += value_before
            portfolio_value_after += value_after
            
            asset_impacts.append(impact)
        
        # Calculate portfolio impact
        if portfolio_value_before > 0:
            portfolio_impact = ((portfolio_value_after - portfolio_value_before) / portfolio_value_before) * Decimal("100")
        else:
            portfolio_impact = Decimal("0")
        
        result = ScenarioResult(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            portfolio_value_before=portfolio_value_before,
            portfolio_value_after=portfolio_value_after,
            portfolio_impact_percentage=portfolio_impact,
            asset_impacts=asset_impacts,
            simulated_at=datetime.now()
        )
        
        logger.info(f"Scenario complete: Portfolio impact {portfolio_impact:.2f}%")
        return result
    
    def run_all_scenarios(
        self,
        portfolio: List[Dict[str, Any]],
        scenarios: List[Dict[str, Any]]
    ) -> List[ScenarioResult]:
        """
        Run all scenarios on a portfolio
        
        Args:
            portfolio: Portfolio positions
            scenarios: List of scenario configurations
        
        Returns:
            List of scenario results
        """
        logger.info(f"Running {len(scenarios)} scenarios on portfolio")
        
        results = []
        
        for scenario in scenarios:
            try:
                result = self.run_scenario(portfolio, scenario)
                results.append(result)
            except Exception as e:
                logger.error(f"Error running scenario {scenario.get('name')}: {e}")
        
        logger.info(f"Completed {len(results)} scenario simulations")
        return results
    
    def get_worst_case_scenario(
        self,
        results: List[ScenarioResult]
    ) -> Optional[ScenarioResult]:
        """
        Get the worst case scenario (maximum portfolio loss)
        
        Args:
            results: List of scenario results
        
        Returns:
            Worst case scenario result
        """
        if not results:
            return None
        
        # Sort by portfolio impact (most negative first)
        sorted_results = sorted(results, key=lambda r: r.portfolio_impact_percentage)
        
        return sorted_results[0]
    
    def get_best_case_scenario(
        self,
        results: List[ScenarioResult]
    ) -> Optional[ScenarioResult]:
        """
        Get the best case scenario (maximum portfolio gain)
        
        Args:
            results: List of scenario results
        
        Returns:
            Best case scenario result
        """
        if not results:
            return None
        
        # Sort by portfolio impact (most positive first)
        sorted_results = sorted(results, key=lambda r: r.portfolio_impact_percentage, reverse=True)
        
        return sorted_results[0]
    
    def generate_scenario_report(
        self,
        results: List[ScenarioResult]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive scenario analysis report
        
        Args:
            results: List of scenario results
        
        Returns:
            Analysis report
        """
        if not results:
            return {"error": "No scenario results to analyze"}
        
        worst_case = self.get_worst_case_scenario(results)
        best_case = self.get_best_case_scenario(results)
        
        # Calculate average impact
        avg_impact = sum(r.portfolio_impact_percentage for r in results) / len(results)
        
        # Count critical scenarios (>20% loss)
        critical_scenarios = [r for r in results if r.portfolio_impact_percentage <= -20]
        
        return {
            "total_scenarios": len(results),
            "average_impact_percentage": float(avg_impact),
            "worst_case": {
                "scenario_name": worst_case.scenario_name if worst_case else None,
                "portfolio_impact_percentage": float(worst_case.portfolio_impact_percentage) if worst_case else None
            },
            "best_case": {
                "scenario_name": best_case.scenario_name if best_case else None,
                "portfolio_impact_percentage": float(best_case.portfolio_impact_percentage) if best_case else None
            },
            "critical_scenarios_count": len(critical_scenarios),
            "critical_scenarios": [
                {
                    "scenario_name": r.scenario_name,
                    "portfolio_impact_percentage": float(r.portfolio_impact_percentage)
                }
                for r in critical_scenarios
            ],
            "generated_at": datetime.now().isoformat()
        }
