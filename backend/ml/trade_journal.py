"""
Mineral AI Tracker - Trade Journaling System (RLHF)
Version: 3.0
Description: Trade journaling for Reinforcement Learning from Human Feedback
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from loguru import logger
from dataclasses import dataclass, asdict
from enum import Enum

from ..quant.buffett_score import BuffettScoreCalculator, Recommendation
from ..quant.kelly_criterion import KellyCriterionCalculator


class UserDecision(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    IGNORE = "ignore"


class Outcome(str, Enum):
    PROFIT = "profit"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    PENDING = "pending"


@dataclass
class TradeJournalEntry:
    """Represents a single trade journal entry"""
    id: str
    user_id: str
    asset_id: str
    asset_ticker: str
    
    # AI Recommendation at time of decision
    ai_buffett_score: Decimal
    ai_confidence: Decimal
    ai_recommendation: str
    ai_kelly_position_size: Decimal
    
    # User Decision
    user_decision: str
    user_position_size: Optional[Decimal]
    user_reasoning: Optional[str]
    
    # Trade Execution
    entry_price: Optional[Decimal]
    exit_price: Optional[Decimal]
    entry_date: Optional[datetime]
    exit_date: Optional[datetime]
    
    # Outcome (evaluated after position closed or 3 months)
    actual_return_percentage: Optional[Decimal]
    outcome: str
    holding_period_days: Optional[int]
    
    # Learning Metrics
    ai_was_correct: Optional[bool]
    user_was_correct: Optional[bool]
    learning_weight_adjustment: Optional[Decimal]
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    notes: Optional[str]


class TradeJournal:
    """
    Trade Journal System - Records user decisions vs AI recommendations
    
    Enables RLHF by tracking:
    - AI recommendations at time of decision
    - User decisions and reasoning
    - Actual outcomes
    - Who was correct (AI or User)
    - Weight adjustments for future predictions
    """
    
    def __init__(self, buffett_calculator: BuffettScoreCalculator):
        """
        Initialize Trade Journal
        
        Args:
            buffett_calculator: BuffettScoreCalculator instance
        """
        self.buffett_calculator = buffett_calculator
        self.entries: List[TradeJournalEntry] = []
        logger.info("Trade Journal initialized")
    
    def create_entry(
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
        Create a new trade journal entry
        
        Args:
            user_id: User ID from Supabase auth
            asset_id: Asset ID
            asset_ticker: Asset ticker symbol
            asset_data: Asset data with scores
            user_decision: User's decision (buy/sell/hold/ignore)
            user_position_size: User's position size (if executed)
            user_reasoning: User's reasoning for decision
            entry_price: Entry price (if trade executed)
            notes: Additional notes
        
        Returns:
            TradeJournalEntry object
        """
        # Calculate AI recommendation
        buffett_result = self.buffett_calculator.calculate_from_asset_data(asset_data)
        
        # Generate entry ID
        entry_id = f"{user_id}_{asset_ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        entry = TradeJournalEntry(
            id=entry_id,
            user_id=user_id,
            asset_id=asset_id,
            asset_ticker=asset_ticker,
            ai_buffett_score=Decimal(str(buffett_result["buffett_score"])),
            ai_confidence=Decimal(str(buffett_result["confidence"])),
            ai_recommendation=buffett_result["recommendation"],
            ai_kelly_position_size=Decimal(str(asset_data.get("kelly_position_size", 0))),
            user_decision=user_decision.value,
            user_position_size=user_position_size,
            user_reasoning=user_reasoning,
            entry_price=entry_price,
            exit_price=None,
            entry_date=datetime.now() if entry_price else None,
            exit_date=None,
            actual_return_percentage=None,
            outcome=Outcome.PENDING.value,
            holding_period_days=None,
            ai_was_correct=None,
            user_was_correct=None,
            learning_weight_adjustment=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            notes=notes
        )
        
        self.entries.append(entry)
        
        logger.info(
            f"Journal entry created: {asset_ticker} | "
            f"AI: {buffett_result['recommendation']} ({buffett_result['buffett_score']:.4f}) | "
            f"User: {user_decision.value}"
        )
        
        return entry
    
    def evaluate_outcome(
        self,
        entry_id: str,
        exit_price: Decimal,
        exit_date: Optional[datetime] = None
    ) -> TradeJournalEntry:
        """
        Evaluate the outcome of a trade journal entry
        
        Args:
            entry_id: Entry ID to evaluate
            exit_price: Exit price
            exit_date: Exit date (defaults to now)
        
        Returns:
            Updated TradeJournalEntry
        """
        entry = self.get_entry(entry_id)
        if not entry:
            logger.error(f"Entry not found: {entry_id}")
            raise ValueError(f"Entry not found: {entry_id}")
        
        if entry.entry_price is None:
            logger.warning(f"Entry has no entry price: {entry_id}")
            return entry
        
        exit_date = exit_date or datetime.now()
        
        # Calculate return
        return_pct = ((exit_price - entry.entry_price) / entry.entry_price) * Decimal("100")
        
        # Determine outcome
        if return_pct > Decimal("0"):
            outcome = Outcome.PROFIT
        elif return_pct < Decimal("0"):
            outcome = Outcome.LOSS
        else:
            outcome = Outcome.BREAKEVEN
        
        # Calculate holding period
        if entry.entry_date:
            holding_period_days = (exit_date - entry.entry_date).days
        else:
            holding_period_days = 0
        
        # Update entry
        entry.exit_price = exit_price
        entry.exit_date = exit_date
        entry.actual_return_percentage = return_pct
        entry.outcome = outcome.value
        entry.holding_period_days = holding_period_days
        entry.updated_at = datetime.now()
        
        # Determine who was correct
        entry.ai_was_correct = self._evaluate_ai_correctness(entry)
        entry.user_was_correct = self._evaluate_user_correctness(entry)
        
        logger.info(
            f"Outcome evaluated: {entry.asset_ticker} | "
            f"Return: {return_pct:.2f}% | "
            f"AI Correct: {entry.ai_was_correct} | "
            f"User Correct: {entry.user_was_correct}"
        )
        
        return entry
    
    def _evaluate_ai_correctness(self, entry: TradeJournalEntry) -> bool:
        """
        Evaluate if AI recommendation was correct
        
        Rules:
        - If AI said BUY/STRONG_BUY and outcome was PROFIT → Correct
        - If AI said SELL/STRONG_SELL and outcome was LOSS → Correct
        - If AI said HOLD and outcome was BREAKEVEN → Correct
        - Otherwise → Incorrect
        """
        if entry.outcome == Outcome.PENDING.value:
            return None
        
        ai_is_buy = entry.ai_recommendation in [Recommendation.BUY.value, Recommendation.STRONG_BUY.value]
        ai_is_sell = entry.ai_recommendation in [Recommendation.SELL.value, Recommendation.STRONG_SELL.value]
        ai_is_hold = entry.ai_recommendation == Recommendation.HOLD.value
        
        if ai_is_buy and entry.outcome == Outcome.PROFIT.value:
            return True
        elif ai_is_sell and entry.outcome == Outcome.LOSS.value:
            return True
        elif ai_is_hold and entry.outcome == Outcome.BREAKEVEN.value:
            return True
        else:
            return False
    
    def _evaluate_user_correctness(self, entry: TradeJournalEntry) -> bool:
        """
        Evaluate if User decision was correct
        
        Rules:
        - If User said BUY and outcome was PROFIT → Correct
        - If User said SELL and outcome was LOSS → Correct
        - If User said HOLD/IGNORE and outcome was BREAKEVEN or small loss → Correct
        - If User went against AI and was right → Bonus correctness
        """
        if entry.outcome == Outcome.PENDING.value:
            return None
        
        user_is_buy = entry.user_decision == UserDecision.BUY.value
        user_is_sell = entry.user_decision == UserDecision.SELL.value
        user_is_hold = entry.user_decision in [UserDecision.HOLD.value, UserDecision.IGNORE.value]
        
        if user_is_buy and entry.outcome == Outcome.PROFIT.value:
            return True
        elif user_is_sell and entry.outcome == Outcome.LOSS.value:
            return True
        elif user_is_hold and entry.outcome in [Outcome.BREAKEVEN.value, Outcome.PROFIT.value]:
            return True
        else:
            return False
    
    def get_entry(self, entry_id: str) -> Optional[TradeJournalEntry]:
        """Get a journal entry by ID"""
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None
    
    def get_user_entries(self, user_id: str) -> List[TradeJournalEntry]:
        """Get all entries for a specific user"""
        return [e for e in self.entries if e.user_id == user_id]
    
    def get_asset_entries(self, asset_id: str) -> List[TradeJournalEntry]:
        """Get all entries for a specific asset"""
        return [e for e in self.entries if e.asset_id == asset_id]
    
    def get_pending_entries(self) -> List[TradeJournalEntry]:
        """Get all entries with pending outcomes"""
        return [e for e in self.entries if e.outcome == Outcome.PENDING.value]
    
    def get_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics from trade journal
        
        Args:
            user_id: Optional user ID to filter stats
        
        Returns:
            Dictionary with statistics
        """
        entries = self.get_user_entries(user_id) if user_id else self.entries
        
        if not entries:
            return {
                "total_entries": 0,
                "evaluated_entries": 0,
                "pending_entries": 0,
                "ai_correct_rate": 0.0,
                "user_correct_rate": 0.0,
                "ai_vs_user_wins": 0,
                "user_vs_ai_wins": 0
            }
        
        evaluated = [e for e in entries if e.outcome != Outcome.PENDING.value]
        pending = [e for e in entries if e.outcome == Outcome.PENDING.value]
        
        ai_correct = sum(1 for e in evaluated if e.ai_was_correct)
        user_correct = sum(1 for e in evaluated if e.user_was_correct)
        
        # Count times user beat AI
        ai_vs_user_wins = sum(1 for e in evaluated if e.ai_was_correct and not e.user_was_correct)
        user_vs_ai_wins = sum(1 for e in evaluated if e.user_was_correct and not e.ai_was_correct)
        
        return {
            "total_entries": len(entries),
            "evaluated_entries": len(evaluated),
            "pending_entries": len(pending),
            "ai_correct_rate": ai_correct / len(evaluated) if evaluated else 0.0,
            "user_correct_rate": user_correct / len(evaluated) if evaluated else 0.0,
            "ai_vs_user_wins": ai_vs_user_wins,
            "user_vs_ai_wins": user_vs_ai_wins,
            "average_return": float(
                sum(e.actual_return_percentage or Decimal("0") for e in evaluated) / len(evaluated)
            ) if evaluated else 0.0
        }
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert all entries to list of dictionaries"""
        return [asdict(entry) for entry in self.entries]
