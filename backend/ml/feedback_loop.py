"""
Mineral AI Tracker - Feedback Loop for RLHF
Version: 3.0
Description: Complete feedback loop for learning from user intuition
"""

import asyncio
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from .trade_journal import TradeJournal, TradeJournalEntry, UserDecision, Outcome
from .weight_adjuster import WeightAdjuster, AdaptiveLearningRate
from ..quant.buffett_score import BuffettScoreCalculator


class FeedbackLoop:
    """
    Complete Feedback Loop System for RLHF
    
    Integrates:
    - Trade Journal: Records decisions and outcomes
    - Weight Adjuster: Learns from AI vs User correctness
    - Adaptive Learning Rate: Adjusts learning rate based on convergence
    
    Workflow:
    1. User makes decision vs AI recommendation
    2. System records in Trade Journal
    3. After trade closes, outcome is evaluated
    4. Weight Adjuster processes outcome
    5. Weights are adjusted based on learning
    6. Future recommendations use updated weights
    """
    
    def __init__(
        self,
        buffett_calculator: BuffettScoreCalculator,
        learning_rate: Decimal = Decimal("0.05"),
        auto_adjust_interval_hours: int = 24,
        min_samples_for_adjustment: int = 10
    ):
        """
        Initialize Feedback Loop
        
        Args:
            buffett_calculator: BuffettScoreCalculator instance
            learning_rate: Initial learning rate
            auto_adjust_interval_hours: Hours between automatic adjustments
            min_samples_for_adjustment: Min samples before adjusting weights
        """
        self.buffett_calculator = buffett_calculator
        self.min_samples_for_adjustment = min_samples_for_adjustment
        self.auto_adjust_interval = timedelta(hours=auto_adjust_interval_hours)
        
        # Initialize components
        self.trade_journal = TradeJournal(buffett_calculator)
        self.weight_adjuster = WeightAdjuster(
            buffett_calculator,
            learning_rate=learning_rate
        )
        self.adaptive_lr = AdaptiveLearningRate(initial_rate=learning_rate)
        
        # Track asset scores for each entry
        self.asset_scores_map: Dict[str, Dict[str, Decimal]] = {}
        
        # Track last adjustment time
        self.last_adjustment_time: Optional[datetime] = None
        
        # Enable/disable auto-adjustment
        self.auto_adjust_enabled = True
        
        logger.info("Feedback Loop initialized")
    
    def record_decision(
        self,
        user_id: str,
        asset_id: str,
        asset_ticker: str,
        asset_data: Dict[str, Any],
        user_decision: UserDecision,
        user_position_size: Optional[Decimal] = None,
        user_reasoning: Optional[str] = None,
        entry_price: Optional[Decimal] = None,
        notes: Optional[str] = None
    ) -> TradeJournalEntry:
        """
        Record a user decision vs AI recommendation
        
        Args:
            user_id: User ID
            asset_id: Asset ID
            asset_ticker: Asset ticker
            asset_data: Asset data with scores
            user_decision: User's decision
            user_position_size: User's position size
            user_reasoning: User's reasoning
            entry_price: Entry price
            notes: Additional notes
        
        Returns:
            TradeJournalEntry
        """
        # Store asset scores for later learning
        asset_scores = {
            "macro": Decimal(str(asset_data.get("macro_score", 0.5))),
            "commodity": Decimal(str(asset_data.get("commodity_aisc_score", 0.5))),
            "geo": Decimal(str(asset_data.get("geo_policy_score", 0.5))),
            "insider": Decimal(str(asset_data.get("insider_score", 0.5))),
            "sentiment": Decimal(str(asset_data.get("trader_sentiment_score", 0.5)))
        }
        
        # Create journal entry
        entry = self.trade_journal.create_entry(
            user_id=user_id,
            asset_id=asset_id,
            asset_ticker=asset_ticker,
            asset_data=asset_data,
            user_decision=user_decision,
            user_position_size=user_position_size,
            user_reasoning=user_reasoning,
            entry_price=entry_price,
            notes=notes
        )
        
        # Store asset scores
        self.asset_scores_map[entry.id] = asset_scores
        
        logger.info(
            f"Decision recorded: {asset_ticker} | "
            f"AI: {entry.ai_recommendation} | "
            f"User: {user_decision.value}"
        )
        
        return entry
    
    def record_outcome(
        self,
        entry_id: str,
        exit_price: Decimal,
        exit_date: Optional[datetime] = None
    ) -> TradeJournalEntry:
        """
        Record the outcome of a trade
        
        Args:
            entry_id: Entry ID
            exit_price: Exit price
            exit_date: Exit date
        
        Returns:
            Updated TradeJournalEntry
        """
        entry = self.trade_journal.evaluate_outcome(entry_id, exit_price, exit_date)
        
        logger.info(
            f"Outcome recorded: {entry.asset_ticker} | "
            f"Return: {entry.actual_return_percentage:.2f}% | "
            f"AI Correct: {entry.ai_was_correct} | "
            f"User Correct: {entry.user_was_correct}"
        )
        
        # Trigger auto-adjustment if enabled and conditions met
        if self.auto_adjust_enabled:
            self._check_and_trigger_auto_adjust()
        
        return entry
    
    def _check_and_trigger_auto_adjust(self):
        """Check if conditions are met for auto-adjustment and trigger if so"""
        now = datetime.now()
        
        # Check if enough time has passed since last adjustment
        if self.last_adjustment_time:
            time_since_adjustment = now - self.last_adjustment_time
            if time_since_adjustment < self.auto_adjust_interval:
                logger.debug("Auto-adjustment interval not yet reached")
                return
        
        # Check if we have enough samples
        evaluated_count = len([e for e in self.trade_journal.entries if e.outcome != Outcome.PENDING.value])
        
        if evaluated_count < self.min_samples_for_adjustment:
            logger.debug(f"Insufficient samples for auto-adjustment: {evaluated_count} < {self.min_samples_for_adjustment}")
            return
        
        # Trigger auto-adjustment
        logger.info("Triggering automatic weight adjustment")
        self.auto_adjust_weights()
    
    def auto_adjust_weights(self):
        """Automatically adjust weights based on accumulated learning"""
        # Update adaptive learning rate
        current_weights = self.buffett_calculator.get_current_weights()
        new_lr = self.adaptive_lr.update_learning_rate(current_weights)
        
        # Update weight adjuster learning rate
        self.weight_adjuster.learning_rate = new_lr
        
        # Perform auto-adjustment
        self.weight_adjuster.auto_adjust(self.trade_journal, self.asset_scores_map)
        
        # Update last adjustment time
        self.last_adjustment_time = datetime.now()
    
    def manual_adjust_weights(self) -> Dict[str, Decimal]:
        """
        Manually trigger weight adjustment
        
        Returns:
            New weights after adjustment
        """
        logger.info("Manually triggering weight adjustment")
        return self.auto_adjust_weights()
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive learning summary
        
        Returns:
            Dictionary with learning statistics and performance
        """
        journal_stats = self.trade_journal.get_statistics()
        performance_report = self.weight_adjuster.get_performance_report()
        current_weights = self.buffett_calculator.get_current_weights()
        
        return {
            "journal_statistics": journal_stats,
            "component_performance": performance_report,
            "current_weights": {k: float(v) for k, v in current_weights.items()},
            "learning_rate": float(self.weight_adjuster.learning_rate),
            "adaptive_learning_rate": float(self.adaptive_lr.current_rate),
            "auto_adjust_enabled": self.auto_adjust_enabled,
            "last_adjustment_time": self.last_adjustment_time.isoformat() if self.last_adjustment_time else None,
            "adjustment_history": self.weight_adjuster.adjustment_history[-10:]  # Last 10 adjustments
        }
    
    def get_user_learning_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get learning profile for a specific user
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary with user-specific learning data
        """
        user_entries = self.trade_journal.get_user_entries(user_id)
        user_stats = self.trade_journal.get_statistics(user_id)
        
        # Analyze user patterns
        buy_decisions = [e for e in user_entries if e.user_decision == UserDecision.BUY.value]
        sell_decisions = [e for e in user_entries if e.user_decision == UserDecision.SELL.value]
        
        # Calculate user's accuracy vs AI
        evaluated = [e for e in user_entries if e.outcome != Outcome.PENDING.value]
        user_beats_ai = sum(1 for e in evaluated if e.user_was_correct and not e.ai_was_correct)
        ai_beats_user = sum(1 for e in evaluated if e.ai_was_correct and not e.user_was_correct)
        
        return {
            "user_id": user_id,
            "total_decisions": len(user_entries),
            "evaluated_decisions": len(evaluated),
            "statistics": user_stats,
            "decision_patterns": {
                "buy_decisions": len(buy_decisions),
                "sell_decisions": len(sell_decisions),
                "hold_decisions": len(user_entries) - len(buy_decisions) - len(sell_decisions)
            },
            "vs_ai_performance": {
                "user_beats_ai": user_beats_ai,
                "ai_beats_user": ai_beats_user,
                "both_correct": sum(1 for e in evaluated if e.user_was_correct and e.ai_was_correct),
                "both_wrong": sum(1 for e in evaluated if not e.user_was_correct and not e.ai_was_correct)
            },
            "average_return": float(
                sum(e.actual_return_percentage or Decimal("0") for e in evaluated) / len(evaluated)
            ) if evaluated else 0.0
        }
    
    def export_learning_data(self) -> Dict[str, Any]:
        """
        Export all learning data for backup or analysis
        
        Returns:
            Dictionary with all learning data
        """
        return {
            "export_timestamp": datetime.now().isoformat(),
            "journal_entries": self.trade_journal.to_dict_list(),
            "asset_scores_map": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in self.asset_scores_map.items()},
            "component_performance": self.weight_adjuster.get_performance_report(),
            "adjustment_history": self.weight_adjuster.adjustment_history,
            "current_weights": {k: float(v) for k, v in self.buffett_calculator.get_current_weights().items()},
            "adaptive_lr_history": self.adaptive_lr.weight_history
        }
    
    def import_learning_data(self, data: Dict[str, Any]):
        """
        Import learning data from backup
        
        Args:
            data: Learning data dictionary from export
        """
        logger.info("Importing learning data...")
        
        # Import journal entries (simplified - would need full reconstruction)
        logger.info(f"Skipping journal entry import (requires full reconstruction)")
        
        # Import asset scores
        self.asset_scores_map = {
            k: {kk: Decimal(str(vv)) for kk, vv in v.items()}
            for k, v in data.get("asset_scores_map", {}).items()
        }
        
        # Import adjustment history
        self.weight_adjuster.adjustment_history = data.get("adjustment_history", [])
        
        # Import adaptive LR history
        self.adaptive_lr.weight_history = [
            {k: Decimal(str(v)) for k, v in w.items()}
            for w in data.get("adaptive_lr_history", [])
        ]
        
        logger.info("Learning data import complete")
    
    def reset_learning(self, keep_journal: bool = False):
        """
        Reset all learning data
        
        Args:
            keep_journal: If True, keep journal entries but reset performance tracking
        """
        if keep_journal:
            self.weight_adjuster.reset_performance_tracking()
            logger.info("Reset performance tracking (journal preserved)")
        else:
            self.trade_journal.entries = []
            self.asset_scores_map = {}
            self.weight_adjuster.reset_performance_tracking()
            self.weight_adjuster.adjustment_history = []
            self.adaptive_lr.weight_history = []
            self.last_adjustment_time = None
            logger.info("Reset all learning data")
    
    def enable_auto_adjust(self):
        """Enable automatic weight adjustment"""
        self.auto_adjust_enabled = True
        logger.info("Auto-adjustment enabled")
    
    def disable_auto_adjust(self):
        """Disable automatic weight adjustment"""
        self.auto_adjust_enabled = False
        logger.info("Auto-adjustment disabled")


class FeedbackLoopManager:
    """
    Manager for multiple user feedback loops
    
    Handles separate learning profiles for different users
    """
    
    def __init__(self, buffett_calculator: BuffettScoreCalculator):
        """
        Initialize Feedback Loop Manager
        
        Args:
            buffett_calculator: Shared BuffettScoreCalculator instance
        """
        self.buffett_calculator = buffett_calculator
        self.user_feedback_loops: Dict[str, FeedbackLoop] = {}
        
        logger.info("Feedback Loop Manager initialized")
    
    def get_or_create_user_loop(self, user_id: str) -> FeedbackLoop:
        """
        Get or create feedback loop for a user
        
        Args:
            user_id: User ID
        
        Returns:
            FeedbackLoop instance for the user
        """
        if user_id not in self.user_feedback_loops:
            self.user_feedback_loops[user_id] = FeedbackLoop(self.buffett_calculator)
            logger.info(f"Created feedback loop for user: {user_id}")
        
        return self.user_feedback_loops[user_id]
    
    def get_global_learning_summary(self) -> Dict[str, Any]:
        """
        Get aggregated learning summary across all users
        
        Returns:
            Dictionary with aggregated statistics
        """
        all_entries = []
        all_performance = {}
        
        for user_id, loop in self.user_feedback_loops.items():
            all_entries.extend(loop.trade_journal.entries)
            user_perf = loop.weight_adjuster.get_performance_report()
            
            for component, stats in user_perf.items():
                if component not in all_performance:
                    all_performance[component] = {
                        "total_samples": 0,
                        "ai_correct_total": 0,
                        "user_correct_total": 0
                    }
                
                all_performance[component]["total_samples"] += stats["total_samples"]
                all_performance[component]["ai_correct_total"] += int(
                    stats["ai_correct_when_high"] + stats["ai_correct_when_low"]
                )
                all_performance[component]["user_correct_total"] += int(
                    stats["user_correct_when_high"] + stats["user_correct_when_low"]
                )
        
        # Calculate aggregate rates
        for component in all_performance:
            total = all_performance[component]["total_samples"]
            if total > 0:
                all_performance[component]["ai_correct_rate"] = (
                    all_performance[component]["ai_correct_total"] / total
                )
                all_performance[component]["user_correct_rate"] = (
                    all_performance[component]["user_correct_total"] / total
                )
                all_performance[component]["user_advantage"] = (
                    all_performance[component]["user_correct_rate"] -
                    all_performance[component]["ai_correct_rate"]
                )
        
        return {
            "total_users": len(self.user_feedback_loops),
            "total_entries": len(all_entries),
            "aggregated_performance": all_performance,
            "current_weights": {k: float(v) for k, v in self.buffett_calculator.get_current_weights().items()}
        }
    
    def apply_user_weights_to_global(self, user_id: str):
        """
        Apply a user's learned weights to the global calculator
        
        Args:
            user_id: User ID to apply weights from
        """
        if user_id not in self.user_feedback_loops:
            logger.warning(f"User loop not found: {user_id}")
            return
        
        loop = self.user_feedback_loops[user_id]
        current_weights = self.buffett_calculator.get_current_weights()
        
        # Apply the user's current weights (which may have been adjusted)
        self.buffett_calculator.update_weights(current_weights)
        
        logger.info(f"Applied user {user_id} weights to global calculator")
