"""
Mineral AI Tracker - Quant Logic Tests (PRD v9.0 Phase 9.9)
Version: 9.0
Description: Stone-hard tests for Kelly Criterion and Tax Calculator
"""

import pytest
from decimal import Decimal
from quant.kelly_criterion import KellyCriterionCalculator
from engines.tax_calculator import TaxCalculator


class TestKellyCriterion:
    """Test suite for Kelly Criterion calculator"""
    
    def test_kelly_position_size_bounds(self):
        """
        Test that Kelly calculator never returns position size > 100% or < 0%
        """
        calculator = KellyCriterionCalculator(use_half_kelly=True, max_position_size=Decimal("0.25"))
        
        # Test edge cases
        test_cases = [
            {"win_probability": 0.0, "risk_reward_ratio": 2.0},  # 0% win prob
            {"win_probability": 1.0, "risk_reward_ratio": 2.0},  # 100% win prob
            {"win_probability": 0.5, "risk_reward_ratio": 0.1},  # Poor R:R
            {"win_probability": 0.5, "risk_reward_ratio": 10.0},  # Excellent R:R
            {"win_probability": 0.9, "risk_reward_ratio": 5.0},  # High confidence
            {"win_probability": 0.1, "risk_reward_ratio": 0.5},  # Low confidence
        ]
        
        for case in test_cases:
            result = calculator.calculate_position_size(
                win_probability=Decimal(str(case["win_probability"])),
                risk_reward_ratio=Decimal(str(case["risk_reward_ratio"]))
            )
            
            position_size = result["kelly_position_size"]
            
            # Assert position size is between 0 and 1 (0% to 100%)
            assert 0 <= position_size <= 1, f"Position size {position_size} out of bounds for case {case}"
            
            # Assert position size respects max_position_size
            assert position_size <= 0.25, f"Position size {position_size} exceeds max_position_size"
    
    def test_kelly_half_kelly_reduces_position(self):
        """Test that half-Kelly reduces position size"""
        full_kelly = KellyCriterionCalculator(use_half_kelly=False, max_position_size=Decimal("0.5"))
        half_kelly = KellyCriterionCalculator(use_half_kelly=True, max_position_size=Decimal("0.5"))
        
        result_full = full_kelly.calculate_position_size(
            win_probability=Decimal("0.6"),
            risk_reward_ratio=Decimal("2.0")
        )
        
        result_half = half_kelly.calculate_position_size(
            win_probability=Decimal("0.6"),
            risk_reward_ratio=Decimal("2.0")
        )
        
        # Half-Kelly should produce smaller position size
        assert result_half["kelly_position_size"] < result_full["kelly_position_size"]
    
    def test_kelly_negative_expected_value(self):
        """Test that Kelly returns 0 for negative expected value"""
        calculator = KellyCriterionCalculator(use_half_kelly=True, max_position_size=Decimal("0.25"))
        
        # Negative expected value: win probability < 50% with 1:1 R:R
        result = calculator.calculate_position_size(
            win_probability=Decimal("0.4"),
            risk_reward_ratio=Decimal("1.0")
        )
        
        # Should return 0 position size
        assert result["kelly_position_size"] == 0


class TestTaxCalculator:
    """Test suite for Tax Calculator (ISK tax)"""
    
    def test_isk_tax_calculation_accuracy(self):
        """
        Test that ISK tax is calculated correctly according to Swedish government bond rate
        """
        calculator = TaxCalculator()
        
        # Test with a fixed amount
        profit = Decimal("100000")  # 100,000 SEK profit
        
        # Swedish government bond rate (approximate for testing)
        government_rate = Decimal("0.02")  # 2%
        
        result = calculator.calculate_isk_tax(
            profit=profit,
            government_rate=government_rate
        )
        
        # ISK tax formula: profit * government_rate
        expected_tax = profit * government_rate
        
        assert result["tax_amount"] == expected_tax
        assert result["tax_rate"] == government_rate
    
    def test_isk_tax_zero_profit(self):
        """Test that ISK tax is zero for zero profit"""
        calculator = TaxCalculator()
        
        result = calculator.calculate_isk_tax(
            profit=Decimal("0"),
            government_rate=Decimal("0.02")
        )
        
        assert result["tax_amount"] == Decimal("0")
    
    def test_isk_tax_negative_profit(self):
        """Test that ISK tax handles negative profit (loss)"""
        calculator = TaxCalculator()
        
        result = calculator.calculate_isk_tax(
            profit=Decimal("-50000"),  # 50,000 SEK loss
            government_rate=Decimal("0.02")
        )
        
        # Tax should be zero for losses
        assert result["tax_amount"] == Decimal("0")
    
    def test_isk_tax_different_rates(self):
        """Test ISK tax with different government rates"""
        calculator = TaxCalculator()
        
        profit = Decimal("100000")
        
        rates = [
            Decimal("0.01"),  # 1%
            Decimal("0.02"),  # 2%
            Decimal("0.03"),  # 3%
            Decimal("0.05"),  # 5%
        ]
        
        for rate in rates:
            result = calculator.calculate_isk_tax(
                profit=profit,
                government_rate=rate
            )
            
            expected_tax = profit * rate
            assert result["tax_amount"] == expected_tax, f"Tax calculation incorrect for rate {rate}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
