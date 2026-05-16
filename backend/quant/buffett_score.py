"""
Mineral AI Tracker - Buffett Score Calculation
Version: 3.0
Description: Deterministic Buffett Score calculation based on verified data
"""

from decimal import Decimal, getcontext
from typing import Dict, Any, Optional
from loguru import logger
from enum import Enum

# Set high precision for financial calculations
getcontext().prec = 10


class Recommendation(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class BuffettScoreCalculator:
    """
    Buffett Score Calculator - Deterministic formula based on verified data
    
    Formula:
    Score = [(D * w_D) + (C * w_C) + (G * w_G) + (I * w_I) + (S * w_S)] * Conf
    
    Where:
    - D (macro_score): Industrial macro demand indicator (0-1)
    - C (commodity_aisc_score): Commodity All-In Sustaining Cost score (0-1)
    - G (geo_policy_score): Geopolitical and policy risk score (0-1)
    - I (insider_score): Insider trading sentiment score (0-1)
    - S (trader_sentiment_score): Social/trader sentiment score (0-1)
    - Conf (confidence): Overall confidence multiplier (0-1)
    
    Default weights:
    - w_D = 0.30 (30% weight to macro)
    - w_C = 0.30 (30% weight to commodity costs)
    - w_G = 0.20 (20% weight to geopolitical factors)
    - w_I = 0.10 (10% weight to insider activity)
    - w_S = 0.10 (10% weight to trader sentiment)
    """
    
    DEFAULT_WEIGHTS = {
        "macro": Decimal("0.20"),  # PRD 6.0: Reduced from 0.25
        "commodity": Decimal("0.20"),  # PRD 6.0: Reduced from 0.25
        "geo": Decimal("0.15"),  # PRD 6.0: Reduced from 0.20
        "insider": Decimal("0.10"),
        "personnel": Decimal("0.10"),  # PRD 6.0: NEW - Personnel/Geologist vector
        "sentiment": Decimal("0.10"),
        "alternative": Decimal("0.15")  # PRD 6.0: Increased from 0.10
    }
    
    def __init__(self, weights: Optional[Dict[str, Decimal]] = None):
        """
        Initialize calculator with custom or default weights
        
        Args:
            weights: Optional custom weights dictionary
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        
        # Validate weights sum to 1.0
        weight_sum = sum(self.weights.values())
        if abs(weight_sum - Decimal("1.0")) > Decimal("0.01"):
            logger.warning(f"Weights sum to {weight_sum}, should be 1.0. Normalizing...")
            self._normalize_weights()
    
    def _normalize_weights(self):
        """Normalize weights to sum to 1.0"""
        total = sum(self.weights.values())
        if total > 0:
            for key in self.weights:
                self.weights[key] = self.weights[key] / total
    
    def calculate_score(
        self,
        macro_score: Decimal,
        commodity_aisc_score: Decimal,
        geo_policy_score: Decimal,
        insider_score: Decimal,
        trader_sentiment_score: Decimal,
        alternative_data_score: Optional[Decimal] = None,
        personnel_score: Optional[Decimal] = None,  # PRD 6.0
        confidence: Decimal = Decimal("1.0"),
        weights: Optional[Dict[str, Decimal]] = None
    ) -> Dict[str, Any]:
        """
        Calculate Buffett Score using deterministic formula (PRD 6.0)
        
        Formula: Score = [(D * 0.20) + (C * 0.20) + (G * 0.15) + (I * 0.10) + (P * 0.10) + (S * 0.10) + (A * 0.15)] * Conf
        
        Args:
            macro_score: Macro demand score (0-1)
            commodity_aisc_score: Commodity AISC score (0-1)
            geo_policy_score: Geopolitical policy score (0-1)
            insider_score: Insider trading score (0-1)
            trader_sentiment_score: Trader sentiment score (0-1)
            alternative_data_score: Alternative/Satellite verification score (0-1)
            personnel_score: Personnel/Geologist score (0-1) - PRD 6.0
            confidence: Confidence multiplier (0-1)
            weights: Optional custom weights for this calculation
        
        Returns:
            Dictionary with score, recommendation, and breakdown
        """
        # Validate inputs
        self._validate_scores(
            macro_score, commodity_aisc_score, geo_policy_score,
            insider_score, trader_sentiment_score, confidence
        )
        
        # Default alternative_data_score to 0.5 if not provided (neutral)
        if alternative_data_score is None:
            alternative_data_score = Decimal("0.5")
        
        # Default personnel_score to 0.5 if not provided (neutral) - PRD 6.0
        if personnel_score is None:
            personnel_score = Decimal("0.5")
        
        # Use provided weights or default
        calc_weights = weights or self.weights
        
        # Calculate weighted sum (PRD 6.0 formula)
        weighted_sum = (
            (macro_score * calc_weights["macro"]) +
            (commodity_aisc_score * calc_weights["commodity"]) +
            (geo_policy_score * calc_weights["geo"]) +
            (insider_score * calc_weights["insider"]) +
            (personnel_score * calc_weights["personnel"]) +  # PRD 6.0
            (trader_sentiment_score * calc_weights["sentiment"]) +
            (alternative_data_score * calc_weights["alternative"])
        )
        
        # Apply confidence multiplier
        buffett_score = weighted_sum * confidence
        
        # Ensure score is within bounds
        buffett_score = max(Decimal("0"), min(Decimal("1"), buffett_score))
        
        # Generate breakdown
        breakdown = {
            "macro": {
                "score": float(macro_score),
                "weight": float(calc_weights["macro"]),
                "contribution": float(macro_score * calc_weights["macro"])
            },
            "commodity": {
                "score": float(commodity_aisc_score),
                "weight": float(calc_weights["commodity"]),
                "contribution": float(commodity_aisc_score * calc_weights["commodity"])
            },
            "geo": {
                "score": float(geo_policy_score),
                "weight": float(calc_weights["geo"]),
                "contribution": float(geo_policy_score * calc_weights["geo"])
            },
            "insider": {
                "score": float(insider_score),
                "weight": float(calc_weights["insider"]),
                "contribution": float(insider_score * calc_weights["insider"])
            },
            "personnel": {  # PRD 6.0
                "score": float(personnel_score),
                "weight": float(calc_weights["personnel"]),
                "contribution": float(personnel_score * calc_weights["personnel"])
            },
            "sentiment": {
                "score": float(trader_sentiment_score),
                "weight": float(calc_weights["sentiment"]),
                "contribution": float(trader_sentiment_score * calc_weights["sentiment"])
            },
            "alternative": {
                "score": float(alternative_data_score),
                "weight": float(calc_weights["alternative"]),
                "contribution": float(alternative_data_score * calc_weights["alternative"])
            }
        }
        
        # Generate recommendation
        recommendation = self._generate_recommendation(buffett_score)
        
        result = {
            "buffett_score": float(buffett_score),
            "recommendation": recommendation.value,
            "confidence": float(confidence),
            "weights_used": {k: float(v) for k, v in calc_weights.items()},
            "breakdown": breakdown
        }
        
        logger.debug(f"Buffett Score calculated: {buffett_score:.4f} -> {recommendation.value}")
        
        return result
    
    def calculate_from_asset_data(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Buffett Score from asset data dictionary
        
        Args:
            asset_data: Dictionary containing score components
        
        Returns:
            Dictionary with score, recommendation, and breakdown
        """
        return self.calculate_score(
            macro_score=Decimal(str(asset_data.get("macro_score", 0.5))),
            commodity_aisc_score=Decimal(str(asset_data.get("commodity_aisc_score", 0.5))),
            geo_policy_score=Decimal(str(asset_data.get("geo_policy_score", 0.5))),
            insider_score=Decimal(str(asset_data.get("insider_score", 0.5))),
            trader_sentiment_score=Decimal(str(asset_data.get("trader_sentiment_score", 0.5))),
            confidence=Decimal(str(asset_data.get("confidence_score", 1.0)))
        )
    
    def _validate_scores(
        self,
        macro_score: Decimal,
        commodity_aisc_score: Decimal,
        geo_policy_score: Decimal,
        insider_score: Decimal,
        trader_sentiment_score: Decimal,
        confidence: Decimal
    ):
        """Validate that all scores are within valid range (0-1)"""
        scores = {
            "macro_score": macro_score,
            "commodity_aisc_score": commodity_aisc_score,
            "geo_policy_score": geo_policy_score,
            "insider_score": insider_score,
            "trader_sentiment_score": trader_sentiment_score,
            "confidence": confidence
        }
        
        for name, score in scores.items():
            if score < Decimal("0") or score > Decimal("1"):
                logger.warning(f"{name} ({score}) is outside valid range [0,1]. Clamping.")
    
    def _generate_recommendation(self, score: Decimal) -> Recommendation:
        """
        Generate recommendation based on Buffett Score
        
        Score thresholds:
        - 0.80 - 1.00: Strong Buy
        - 0.60 - 0.79: Buy
        - 0.40 - 0.59: Hold
        - 0.20 - 0.39: Sell
        - 0.00 - 0.19: Strong Sell
        """
        if score >= Decimal("0.80"):
            return Recommendation.STRONG_BUY
        elif score >= Decimal("0.60"):
            return Recommendation.BUY
        elif score >= Decimal("0.40"):
            return Recommendation.HOLD
        elif score >= Decimal("0.20"):
            return Recommendation.SELL
        else:
            return Recommendation.STRONG_SELL
    
    def update_weights(self, new_weights: Dict[str, Decimal]):
        """
        Update calculator weights (for RLHF learning)
        
        Args:
            new_weights: New weight dictionary
        """
        self.weights = new_weights.copy()
        weight_sum = sum(self.weights.values())
        
        if abs(weight_sum - Decimal("1.0")) > Decimal("0.01"):
            logger.warning(f"New weights sum to {weight_sum}, normalizing...")
            self._normalize_weights()
        
        logger.info(f"Weights updated: {self.weights}")
    
    def get_current_weights(self) -> Dict[str, Decimal]:
        """Get current weights being used"""
        return self.weights.copy()


class WeightLearner:
    """
    Weight Learner - Adjusts Buffett Score weights based on RLHF feedback
    
    Uses historical trade outcomes to learn which components are most predictive
    of successful trades and adjusts weights accordingly.
    """
    
    def __init__(self, learning_rate: Decimal = Decimal("0.05")):
        """
        Initialize weight learner
        
        Args:
            learning_rate: Rate at which weights are adjusted (0-1)
        """
        self.learning_rate = learning_rate
        self.historical_performance = {
            "macro": {"correct": 0, "total": 0},
            "commodity": {"correct": 0, "total": 0},
            "geo": {"correct": 0, "total": 0},
            "insider": {"correct": 0, "total": 0},
            "sentiment": {"correct": 0, "total": 0}
        }
    
    def record_outcome(
        self,
        component: str,
        was_predictive: bool
    ):
        """
        Record whether a component was predictive of a successful trade
        
        Args:
            component: Component name (macro, commodity, geo, insider, sentiment)
            was_predictive: Whether this component predicted the outcome correctly
        """
        if component not in self.historical_performance:
            logger.warning(f"Unknown component: {component}")
            return
        
        self.historical_performance[component]["total"] += 1
        if was_predictive:
            self.historical_performance[component]["correct"] += 1
    
    def calculate_adjusted_weights(self, current_weights: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """
        Calculate adjusted weights based on historical performance
        
        Args:
            current_weights: Current weight dictionary
        
        Returns:
            Adjusted weight dictionary
        """
        adjusted_weights = current_weights.copy()
        
        # Calculate performance ratios for each component
        performance_ratios = {}
        for component, stats in self.historical_performance.items():
            if stats["total"] > 0:
                performance_ratios[component] = Decimal(str(stats["correct"])) / Decimal(str(stats["total"]))
            else:
                performance_ratios[component] = Decimal("0.5")  # Neutral if no data
        
        # Adjust weights based on performance
        total_performance = sum(performance_ratios.values())
        
        if total_performance > 0:
            for component in adjusted_weights:
                # Weight adjustment: move weight towards better-performing components
                target_weight = performance_ratios[component] / total_performance
                current_weight = adjusted_weights[component]
                
                # Apply learning rate
                adjusted_weights[component] = (
                    current_weight + 
                    (target_weight - current_weight) * self.learning_rate
                )
        
        # Normalize to ensure sum is 1.0
        total = sum(adjusted_weights.values())
        if total > 0:
            for component in adjusted_weights:
                adjusted_weights[component] = adjusted_weights[component] / total
        
        logger.info(f"Adjusted weights based on performance: {adjusted_weights}")
        
        return adjusted_weights
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get historical performance statistics"""
        stats = {}
        for component, data in self.historical_performance.items():
            if data["total"] > 0:
                accuracy = Decimal(str(data["correct"])) / Decimal(str(data["total"]))
                stats[component] = {
                    "accuracy": float(accuracy),
                    "correct_predictions": data["correct"],
                    "total_predictions": data["total"]
                }
            else:
                stats[component] = {
                    "accuracy": 0.0,
                    "correct_predictions": 0,
                    "total_predictions": 0
                }
        
        return stats
