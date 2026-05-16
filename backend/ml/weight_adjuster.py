"""
Mineral AI Tracker - Automatic Weight Adjustment (RLHF)
Version: 3.0
Description: Automatic weight adjustment based on AI vs User correctness
"""

from decimal import Decimal, getcontext
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from dataclasses import dataclass

from .trade_journal import TradeJournal, TradeJournalEntry, Outcome
from ..quant.buffett_score import BuffettScoreCalculator

# Set high precision for calculations
getcontext().prec = 10


@dataclass
class ComponentPerformance:
    """Performance tracking for individual score components"""
    component: str  # macro, commodity, geo, insider, sentiment
    ai_correct_when_high: int  # Times AI was correct when this component was high
    ai_correct_when_low: int  # Times AI was correct when this component was low
    user_correct_when_high: int  # Times User was correct when this component was high
    user_correct_when_low: int  # Times User was correct when this component was low
    total_high: int  # Total times this component was high
    total_low: int  # Total times this component was low


class WeightAdjuster:
    """
    Weight Adjuster - Automatically adjusts Buffett Score weights based on RLHF
    
    Learning Logic:
    1. Track which components were predictive of success when AI was correct
    2. Track which components were predictive of success when User was correct
    3. If User consistently beats AI on specific component signals, increase weight for those components
    4. If AI consistently beats User, maintain or decrease weight adjustment
    """
    
    def __init__(
        self,
        buffett_calculator: BuffettScoreCalculator,
        learning_rate: Decimal = Decimal("0.05"),
        min_weight: Decimal = Decimal("0.05"),
        max_weight: Decimal = Decimal("0.50")
    ):
        """
        Initialize Weight Adjuster
        
        Args:
            buffett_calculator: BuffettScoreCalculator instance
            learning_rate: Rate at which weights are adjusted (0-1)
            min_weight: Minimum weight for any component
            max_weight: Maximum weight for any component
        """
        self.buffett_calculator = buffett_calculator
        self.learning_rate = learning_rate
        self.min_weight = min_weight
        self.max_weight = max_weight
        
        # Track component performance
        self.component_performance: Dict[str, ComponentPerformance] = {
            "macro": ComponentPerformance("macro", 0, 0, 0, 0, 0, 0),
            "commodity": ComponentPerformance("commodity", 0, 0, 0, 0, 0, 0),
            "geo": ComponentPerformance("geo", 0, 0, 0, 0, 0, 0),
            "insider": ComponentPerformance("insider", 0, 0, 0, 0, 0, 0),
            "sentiment": ComponentPerformance("sentiment", 0, 0, 0, 0, 0, 0)
        }
        
        # Track adjustment history
        self.adjustment_history: List[Dict[str, Any]] = []
        
        logger.info(f"Weight Adjuster initialized (learning_rate: {learning_rate})")
    
    def process_entry(self, entry: TradeJournalEntry, asset_scores: Dict[str, Decimal]):
        """
        Process a trade journal entry to learn from the outcome
        
        Args:
            entry: Trade journal entry
            asset_scores: Component scores at time of decision
        """
        if entry.outcome == Outcome.PENDING.value:
            logger.debug(f"Skipping pending entry: {entry.id}")
            return
        
        # Determine if component was "high" or "low"
        for component, score in asset_scores.items():
            if component not in self.component_performance:
                continue
            
            is_high = score >= Decimal("0.5")
            perf = self.component_performance[component]
            
            if is_high:
                perf.total_high += 1
                if entry.ai_was_correct:
                    perf.ai_correct_when_high += 1
                if entry.user_was_correct:
                    perf.user_correct_when_high += 1
            else:
                perf.total_low += 1
                if entry.ai_was_correct:
                    perf.ai_correct_when_low += 1
                if entry.user_was_correct:
                    perf.user_correct_when_low += 1
        
        logger.debug(f"Processed entry {entry.id} for learning")
    
    def calculate_adjustments(self, min_samples: int = 10) -> Dict[str, Decimal]:
        """
        Calculate weight adjustments based on component performance
        
        Args:
            min_samples: Minimum samples required before adjusting
        
        Returns:
            Dictionary of weight adjustments per component
        """
        current_weights = self.buffett_calculator.get_current_weights()
        adjustments = {}
        
        for component, perf in self.component_performance.items():
            total_samples = perf.total_high + perf.total_low
            
            if total_samples < min_samples:
                logger.debug(f"Insufficient samples for {component}: {total_samples} < {min_samples}")
                adjustments[component] = Decimal("0")
                continue
            
            # Calculate User advantage over AI
            user_advantage_high = self._calculate_advantage(
                perf.user_correct_when_high, perf.ai_correct_when_high, perf.total_high
            )
            user_advantage_low = self._calculate_advantage(
                perf.user_correct_when_low, perf.ai_correct_when_low, perf.total_low
            )
            
            # Average advantage
            avg_advantage = (user_advantage_high + user_advantage_low) / Decimal("2")
            
            # Calculate adjustment (proportional to advantage)
            current_weight = current_weights.get(component, Decimal("0.20"))
            adjustment = avg_advantage * self.learning_rate * current_weight
            
            adjustments[component] = adjustment
        
        return adjustments
    
    def _calculate_advantage(
        self,
        user_correct: int,
        ai_correct: int,
        total: int
    ) -> Decimal:
        """Calculate user advantage over AI (-1 to 1)"""
        if total == 0:
            return Decimal("0")
        
        user_rate = Decimal(user_correct) / Decimal(total)
        ai_rate = Decimal(ai_correct) / Decimal(total)
        
        return user_rate - ai_rate
    
    def apply_adjustments(self, adjustments: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """
        Apply weight adjustments to the calculator
        
        Args:
            adjustments: Dictionary of adjustments per component
        
        Returns:
            New weights after adjustment
        """
        current_weights = self.buffett_calculator.get_current_weights()
        new_weights = current_weights.copy()
        
        # Apply adjustments
        for component, adjustment in adjustments.items():
            new_weights[component] = new_weights[component] + adjustment
        
        # Enforce min/max bounds
        for component in new_weights:
            new_weights[component] = max(self.min_weight, min(self.max_weight, new_weights[component]))
        
        # Normalize to sum to 1.0
        total = sum(new_weights.values())
        if total > 0:
            for component in new_weights:
                new_weights[component] = new_weights[component] / total
        
        # Apply to calculator
        self.buffett_calculator.update_weights(new_weights)
        
        # Record history
        self.adjustment_history.append({
            "timestamp": datetime.now().isoformat(),
            "old_weights": {k: float(v) for k, v in current_weights.items()},
            "adjustments": {k: float(v) for k, v in adjustments.items()},
            "new_weights": {k: float(v) for k, v in new_weights.items()}
        })
        
        logger.info(f"Applied weight adjustments: {adjustments}")
        logger.info(f"New weights: {new_weights}")
        
        return new_weights
    
    def auto_adjust(self, trade_journal: TradeJournal, asset_scores_map: Dict[str, Dict[str, Decimal]]):
        """
        Automatically adjust weights based on trade journal history
        
        Args:
            trade_journal: TradeJournal instance
            asset_scores_map: Map of entry_id to asset scores
        """
        logger.info("Starting automatic weight adjustment...")
        
        # Process all evaluated entries
        evaluated_entries = [e for e in trade_journal.entries if e.outcome != Outcome.PENDING.value]
        
        for entry in evaluated_entries:
            asset_scores = asset_scores_map.get(entry.id, {})
            self.process_entry(entry, asset_scores)
        
        # Calculate adjustments
        adjustments = self.calculate_adjustments(min_samples=5)
        
        # Apply adjustments
        if any(abs(adj) > Decimal("0.01") for adj in adjustments.values()):
            new_weights = self.apply_adjustments(adjustments)
            logger.info(f"Auto-adjustment complete. New weights: {new_weights}")
        else:
            logger.info("No significant adjustments needed")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get detailed performance report for all components"""
        report = {}
        
        for component, perf in self.component_performance.items():
            total = perf.total_high + perf.total_low
            
            ai_correct_total = perf.ai_correct_when_high + perf.ai_correct_when_low
            user_correct_total = perf.user_correct_when_high + perf.user_correct_when_low
            
            ai_rate = ai_correct_total / total if total > 0 else Decimal("0")
            user_rate = user_correct_total / total if total > 0 else Decimal("0")
            
            report[component] = {
                "total_samples": total,
                "ai_correct_rate": float(ai_rate),
                "user_correct_rate": float(user_rate),
                "user_advantage": float(user_rate - ai_rate),
                "high_samples": perf.total_high,
                "low_samples": perf.total_low,
                "ai_correct_when_high": perf.ai_correct_when_high,
                "user_correct_when_high": perf.user_correct_when_high,
                "ai_correct_when_low": perf.ai_correct_when_low,
                "user_correct_when_low": perf.user_correct_when_low
            }
        
        return report
    
    def reset_performance_tracking(self):
        """Reset all performance tracking data"""
        for perf in self.component_performance.values():
            perf.ai_correct_when_high = 0
            perf.ai_correct_when_low = 0
            perf.user_correct_when_high = 0
            perf.user_correct_when_low = 0
            perf.total_high = 0
            perf.total_low = 0
        
        logger.info("Performance tracking reset")


class AdaptiveLearningRate:
    """
    Adaptive Learning Rate - Adjusts learning rate based on convergence
    
    Decreases learning rate as the system converges on optimal weights
    """
    
    def __init__(
        self,
        initial_rate: Decimal = Decimal("0.05"),
        min_rate: Decimal = Decimal("0.01"),
        decay_factor: Decimal = Decimal("0.95"),
        stability_threshold: Decimal = Decimal("0.01")
    ):
        """
        Initialize adaptive learning rate
        
        Args:
            initial_rate: Initial learning rate
            min_rate: Minimum learning rate
            decay_factor: Decay factor when stable
            stability_threshold: Threshold for considering weights stable
        """
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.decay_factor = decay_factor
        self.stability_threshold = stability_threshold
        
        self.weight_history: List[Dict[str, Decimal]] = []
        self.stable_count = 0
    
    def update_learning_rate(self, current_weights: Dict[str, Decimal]) -> Decimal:
        """
        Update learning rate based on weight stability
        
        Args:
            current_weights: Current weight dictionary
        
        Returns:
            Updated learning rate
        """
        self.weight_history.append(current_weights.copy())
        
        # Keep only last 10 weight sets
        if len(self.weight_history) > 10:
            self.weight_history.pop(0)
        
        # Check stability if we have enough history
        if len(self.weight_history) >= 3:
            is_stable = self._check_stability()
            
            if is_stable:
                self.stable_count += 1
            else:
                self.stable_count = 0
            
            # Decay learning rate if stable for 3 consecutive checks
            if self.stable_count >= 3:
                self.current_rate = max(self.min_rate, self.current_rate * self.decay_factor)
                logger.info(f"Weights stable, decaying learning rate to {self.current_rate}")
                self.stable_count = 0
        
        return self.current_rate
    
    def _check_stability(self) -> bool:
        """Check if weights have stabilized"""
        if len(self.weight_history) < 3:
            return False
        
        # Calculate variance across recent weights
        recent = self.weight_history[-3:]
        
        for component in recent[0].keys():
            values = [w[component] for w in recent]
            variance = max(values) - min(values)
            
            if variance > self.stability_threshold:
                return False
        
        return True
