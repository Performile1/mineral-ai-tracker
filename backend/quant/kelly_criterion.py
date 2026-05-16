"""
Mineral AI Tracker - Kelly Criterion Position Sizing
Version: 3.0
Description: Kelly Criterion for optimal position sizing
"""

from decimal import Decimal, getcontext
from typing import Dict, Any, Optional, Tuple
from loguru import logger
from enum import Enum

# Set high precision for financial calculations
getcontext().prec = 10


class PositionSizeInterpretation(str, Enum):
    AGGRESSIVE = "aggressive"
    MODERATE = "moderate"
    CONSERVATIVE = "conservative"
    NO_POSITION = "no_position"
    REDUCE = "reduce_exposure"


class KellyCriterionCalculator:
    """
    Kelly Criterion Calculator - Optimal position sizing
    
    Formula:
    f* = (p * b - q) / b
    
    Where:
    - f*: Fraction of portfolio to invest (position size)
    - p: Probability of winning
    - q: Probability of losing (1 - p)
    - b: Risk/reward ratio (Target price / Stop-Loss)
    
    Half-Kelly (more conservative):
    f*_half = f* / 2
    
    Quarter-Kelly (very conservative):
    f*_quarter = f* / 4
    """
    
    def __init__(self, use_half_kelly: bool = True, max_position_size: Decimal = Decimal("0.25")):
        """
        Initialize Kelly Criterion calculator
        
        Args:
            use_half_kelly: Whether to use half-Kelly (more conservative)
            max_position_size: Maximum position size as fraction of portfolio (default 25%)
        """
        self.use_half_kelly = use_half_kelly
        self.max_position_size = max_position_size
        logger.info(f"Kelly Calculator initialized (half-kelly: {use_half_kelly}, max: {max_position_size})")
    
    def calculate_position_size(
        self,
        win_probability: Decimal,
        risk_reward_ratio: Decimal,
        use_half_kelly: Optional[bool] = None,
        max_position_size: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Calculate optimal position size using Kelly Criterion
        
        Args:
            win_probability: Probability of winning (0-1)
            risk_reward_ratio: Risk/reward ratio (target_price / stop_loss)
            use_half_kelly: Override default half-kelly setting
            max_position_size: Override default max position size
        
        Returns:
            Dictionary with position size, interpretation, and breakdown
        """
        # Validate inputs
        self._validate_inputs(win_probability, risk_reward_ratio)
        
        # Calculate losing probability
        lose_probability = Decimal("1") - win_probability
        
        # Calculate Kelly fraction
        kelly_fraction = self._calculate_kelly_fraction(
            win_probability,
            lose_probability,
            risk_reward_ratio
        )
        
        # Apply half-kelly if configured
        half_kelly = use_half_kelly if use_half_kelly is not None else self.use_half_kelly
        if half_kelly:
            kelly_fraction = kelly_fraction / Decimal("2")
        
        # Apply max position size cap
        max_size = max_position_size if max_position_size is not None else self.max_position_size
        kelly_fraction = min(kelly_fraction, max_size)
        
        # Ensure non-negative
        kelly_fraction = max(Decimal("0"), kelly_fraction)
        
        # Generate interpretation
        interpretation = self._interpret_position_size(kelly_fraction, win_probability, risk_reward_ratio)
        
        # Calculate expected value
        expected_value = self._calculate_expected_value(
            win_probability,
            lose_probability,
            risk_reward_ratio
        )
        
        result = {
            "kelly_position_size": float(kelly_fraction),
            "percentage": float(kelly_fraction * Decimal("100")),
            "win_probability": float(win_probability),
            "lose_probability": float(lose_probability),
            "risk_reward_ratio": float(risk_reward_ratio),
            "expected_value": float(expected_value),
            "interpretation": interpretation.value,
            "half_kelly_used": half_kelly,
            "max_position_cap_applied": kelly_fraction >= max_size,
            "breakdown": {
                "raw_kelly_fraction": float(self._calculate_kelly_fraction(
                    win_probability, lose_probability, risk_reward_ratio
                )),
                "after_half_kelly": float(kelly_fraction * Decimal("2") if half_kelly else float(kelly_fraction)),
                "max_cap": float(max_size)
            }
        }
        
        logger.debug(
            f"Kelly: p={win_probability:.4f}, b={risk_reward_ratio:.4f} -> "
            f"f*={kelly_fraction:.4f} ({kelly_fraction*100:.2f}%) -> {interpretation.value}"
        )
        
        return result
    
    def calculate_from_asset_data(
        self,
        asset_data: Dict[str, Any],
        confidence: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Calculate position size from asset data
        
        Args:
            asset_data: Dictionary containing asset information
            confidence: Optional confidence score (used as win probability if not provided)
        
        Returns:
            Dictionary with position size and interpretation
        """
        # Extract or calculate win probability
        win_probability = Decimal(str(asset_data.get("win_probability", 0.5)))
        if confidence is not None:
            win_probability = confidence
        
        # Calculate risk/reward ratio from target and stop-loss
        target_price = Decimal(str(asset_data.get("target_price", 0)))
        stop_loss = Decimal(str(asset_data.get("stop_loss", 0)))
        
        if stop_loss > 0:
            risk_reward_ratio = target_price / stop_loss
        else:
            risk_reward_ratio = Decimal("1.0")
        
        return self.calculate_position_size(win_probability, risk_reward_ratio)
    
    def _calculate_kelly_fraction(
        self,
        win_probability: Decimal,
        lose_probability: Decimal,
        risk_reward_ratio: Decimal
    ) -> Decimal:
        """Calculate raw Kelly fraction"""
        return (win_probability * risk_reward_ratio - lose_probability) / risk_reward_ratio
    
    def _calculate_expected_value(
        self,
        win_probability: Decimal,
        lose_probability: Decimal,
        risk_reward_ratio: Decimal
    ) -> Decimal:
        """
        Calculate expected value per unit risk
        
        EV = (p * b) - q
        """
        return (win_probability * risk_reward_ratio) - lose_probability
    
    def _interpret_position_size(
        self,
        kelly_fraction: Decimal,
        win_probability: Decimal,
        risk_reward_ratio: Decimal
    ) -> PositionSizeInterpretation:
        """
        Interpret the calculated position size
        
        Interpretation rules:
        - f* <= 0: No position (negative expected value)
        - 0 < f* < 0.02: Reduce exposure / Very small position
        - 0.02 <= f* < 0.05: Conservative position
        - 0.05 <= f* < 0.10: Moderate position
        - f* >= 0.10: Aggressive position (but capped by max_position_size)
        """
        if kelly_fraction <= Decimal("0"):
            return PositionSizeInterpretation.NO_POSITION
        elif kelly_fraction < Decimal("0.02"):
            return PositionSizeInterpretation.REDUCE
        elif kelly_fraction < Decimal("0.05"):
            return PositionSizeInterpretation.CONSERVATIVE
        elif kelly_fraction < Decimal("0.10"):
            return PositionSizeInterpretation.MODERATE
        else:
            return PositionSizeInterpretation.AGGRESSIVE
    
    def _validate_inputs(self, win_probability: Decimal, risk_reward_ratio: Decimal):
        """Validate input parameters"""
        if win_probability < Decimal("0") or win_probability > Decimal("1"):
            raise ValueError(f"Win probability must be between 0 and 1, got {win_probability}")
        
        if risk_reward_ratio <= Decimal("0"):
            raise ValueError(f"Risk/reward ratio must be positive, got {risk_reward_ratio}")
    
    def calculate_optimal_portfolio_allocation(
        self,
        opportunities: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate optimal portfolio allocation across multiple opportunities
        
        Args:
            opportunities: List of opportunity dictionaries with win_probability and risk_reward_ratio
        
        Returns:
            Dictionary with allocation percentages and total allocation
        """
        individual_kellys = []
        
        for i, opp in enumerate(opportunities):
            try:
                result = self.calculate_position_size(
                    win_probability=Decimal(str(opp.get("win_probability", 0.5))),
                    risk_reward_ratio=Decimal(str(opp.get("risk_reward_ratio", 1.0)))
                )
                individual_kellys.append({
                    "index": i,
                    "kelly_fraction": Decimal(str(result["kelly_position_size"])),
                    "expected_value": Decimal(str(result["expected_value"]))
                })
            except Exception as e:
                logger.warning(f"Error calculating Kelly for opportunity {i}: {e}")
        
        # Sort by expected value (descending)
        individual_kellys.sort(key=lambda x: x["expected_value"], reverse=True)
        
        # Calculate allocation (simple approach: normalize positive Kelly fractions)
        positive_kellys = [k for k in individual_kellys if k["kelly_fraction"] > 0]
        
        if not positive_kellys:
            return {
                "allocations": {},
                "total_allocation": 0.0,
                "message": "No positive expected value opportunities"
            }
        
        total_kelly = sum(k["kelly_fraction"] for k in positive_kellys)
        
        # Normalize to ensure total doesn't exceed 100%
        if total_kelly > Decimal("1"):
            scale_factor = Decimal("1") / total_kelly
            for k in positive_kellys:
                k["kelly_fraction"] = k["kelly_fraction"] * scale_factor
        
        # Build allocation dictionary
        allocations = {}
        for k in positive_kellys:
            allocations[f"opportunity_{k['index']}"] = {
                "percentage": float(k["kelly_fraction"] * Decimal("100")),
                "expected_value": float(k["expected_value"])
            }
        
        total_allocation = sum(k["kelly_fraction"] for k in positive_kellys)
        
        return {
            "allocations": allocations,
            "total_allocation": float(total_allocation * Decimal("100")),
            "opportunities_analyzed": len(opportunities),
            "positive_ev_opportunities": len(positive_kellys)
        }


class RiskAdjustedKelly(KellyCriterionCalculator):
    """
    Risk-Adjusted Kelly Criterion
    
    Adjusts Kelly fraction based on additional risk factors:
    - Volatility
    - Correlation with existing positions
    - Maximum drawdown tolerance
    """
    
    def __init__(
        self,
        use_half_kelly: bool = True,
        max_position_size: Decimal = Decimal("0.25"),
        volatility_adjustment: bool = True,
        correlation_adjustment: bool = True
    ):
        super().__init__(use_half_kelly, max_position_size)
        self.volatility_adjustment = volatility_adjustment
        self.correlation_adjustment = correlation_adjustment
    
    def calculate_position_size_with_risk_adjustment(
        self,
        win_probability: Decimal,
        risk_reward_ratio: Decimal,
        volatility: Optional[Decimal] = None,
        correlation: Optional[Decimal] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Calculate position size with risk adjustments
        
        Args:
            win_probability: Probability of winning (0-1)
            risk_reward_ratio: Risk/reward ratio
            volatility: Asset volatility (optional, for adjustment)
            correlation: Correlation with existing portfolio (optional)
            **kwargs: Additional arguments for base calculation
        
        Returns:
            Dictionary with adjusted position size
        """
        # Calculate base Kelly
        result = self.calculate_position_size(
            win_probability,
            risk_reward_ratio,
            **kwargs
        )
        
        base_kelly = Decimal(str(result["kelly_position_size"]))
        
        # Apply volatility adjustment
        if self.volatility_adjustment and volatility is not None:
            volatility_factor = self._calculate_volatility_adjustment(volatility)
            base_kelly = base_kelly * volatility_factor
            result["volatility_adjustment_factor"] = float(volatility_factor)
        
        # Apply correlation adjustment
        if self.correlation_adjustment and correlation is not None:
            correlation_factor = self._calculate_correlation_adjustment(correlation)
            base_kelly = base_kelly * correlation_factor
            result["correlation_adjustment_factor"] = float(correlation_factor)
        
        # Re-apply max cap
        base_kelly = min(base_kelly, self.max_position_size)
        
        # Update result
        result["kelly_position_size"] = float(base_kelly)
        result["percentage"] = float(base_kelly * Decimal("100"))
        result["risk_adjusted"] = True
        
        # Re-interpret
        result["interpretation"] = self._interpret_position_size(
            base_kelly,
            win_probability,
            risk_reward_ratio
        ).value
        
        return result
    
    def _calculate_volatility_adjustment(self, volatility: Decimal) -> Decimal:
        """
        Calculate volatility adjustment factor
        
        Higher volatility = smaller position
        
        Formula:
        factor = 1 / (1 + volatility * 2)
        """
        # Normalize volatility (assume typical range 0-1)
        return Decimal("1") / (Decimal("1") + volatility * Decimal("2"))
    
    def _calculate_correlation_adjustment(self, correlation: Decimal) -> Decimal:
        """
        Calculate correlation adjustment factor
        
        Higher correlation with existing portfolio = smaller position
        
        Formula:
        factor = 1 - abs(correlation) * 0.5
        """
        return Decimal("1") - abs(correlation) * Decimal("0.5")
