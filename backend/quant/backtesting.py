"""
Mineral AI Tracker - Backtesting CLI Tool
Version: 10.6
Description: CLI tool for backtesting strategies on historical data (2018-2025)
PRD v9.0: Added HistoricalSnapshotter and PerformanceAuditor for The Time Machine
PRD v10.0 Phase 10.6: Added real historical data integration with yfinance
"""

import asyncio
from decimal import Decimal, getcontext
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from dataclasses import dataclass
from loguru import logger
import json
import sys
from pathlib import Path

# Set high precision for financial calculations
getcontext().prec = 10

from .buffett_score import BuffettScoreCalculator, Recommendation
from .kelly_criterion import KellyCriterionCalculator
from .historical_data import get_historical_data_fetcher


@dataclass
class Trade:
    """Represents a single trade in backtesting"""
    entry_date: date
    exit_date: date
    ticker: str
    entry_price: Decimal
    exit_price: Decimal
    shares: Decimal
    position_size: Decimal
    buffett_score: Decimal
    recommendation: str
    win: bool
    return_pct: Decimal


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    strategy_name: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    weight_macro: Decimal
    weight_commodity: Decimal
    weight_geo: Decimal
    weight_insider: Decimal
    weight_sentiment: Decimal
    use_half_kelly: bool
    max_position_size: Decimal
    commission_per_trade: Decimal = Decimal("0.001")  # 0.1% per trade
    slippage: Decimal = Decimal("0.0005")  # 0.05% slippage


class Backtester:
    """
    Backtesting Engine - Tests strategy performance on historical data
    
    Simulates trading using the Buffett Score and Kelly Criterion
    on historical price and indicator data.
    """
    
    def __init__(self, config: BacktestConfig):
        """
        Initialize backtester with configuration
        
        Args:
            config: BacktestConfig object
        """
        self.config = config
        
        # Initialize calculators
        weights = {
            "macro": config.weight_macro,
            "commodity": config.weight_commodity,
            "geo": config.weight_geo,
            "insider": config.weight_insider,
            "sentiment": config.weight_sentiment
        }
        
        self.buffett_calculator = BuffettScoreCalculator(weights=weights)
        self.kelly_calculator = KellyCriterionCalculator(
            use_half_kelly=config.use_half_kelly,
            max_position_size=config.max_position_size
        )
        
        # Trading state
        self.current_capital = config.initial_capital
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict[str, Any]] = []
        
        logger.info(f"Backtester initialized: {config.strategy_name}")
        logger.info(f"Period: {config.start_date} to {config.end_date}")
        logger.info(f"Initial Capital: ${config.initial_capital}")
    
    async def run_backtest(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run backtesting on historical data
        
        Args:
            historical_data: List of historical data points (daily/weekly)
        
        Returns:
            Dictionary with backtesting results
        """
        logger.info("Starting backtest...")
        
        # Reset state
        self.current_capital = self.config.initial_capital
        self.trades = []
        self.equity_curve = []
        
        # Sort data by date
        sorted_data = sorted(historical_data, key=lambda x: x["date"])
        
        # Track open positions
        open_positions: Dict[str, Dict[str, Any]] = {}
        
        # Simulate trading
        for i, data_point in enumerate(sorted_data):
            current_date = data_point["date"]
            
            # Record equity
            self.equity_curve.append({
                "date": current_date.isoformat(),
                "capital": float(self.current_capital),
                "open_positions": len(open_positions)
            })
            
            # Check for exit signals (close positions)
            await self._check_exit_signals(open_positions, data_point)
            
            # Check for entry signals (open new positions)
            await self._check_entry_signals(open_positions, data_point)
            
            logger.debug(f"Day {i+1}/{len(sorted_data)}: ${self.current_capital:.2f}, {len(open_positions)} positions")
        
        # Close any remaining positions at end
        await self._close_all_positions(open_positions, sorted_data[-1])
        
        # Calculate final statistics
        results = self._calculate_results()
        
        logger.info("Backtest completed")
        logger.info(f"Final Capital: ${self.current_capital:.2f}")
        logger.info(f"Total Return: {results['total_return_percentage']:.2f}%")
        logger.info(f"Win Rate: {results['win_rate']:.2%}")
        logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        
        return results
    
    async def _check_entry_signals(
        self,
        open_positions: Dict[str, Dict[str, Any]],
        data_point: Dict[str, Any]
    ):
        """Check for entry signals and open positions"""
        ticker = data_point.get("ticker")
        
        if not ticker or ticker in open_positions:
            return
        
        # Calculate Buffett Score
        buffett_result = self.buffett_calculator.calculate_from_asset_data(data_point)
        buffett_score = Decimal(str(buffett_result["buffett_score"]))
        recommendation = buffett_result["recommendation"]
        
        # Only enter on BUY or STRONG_BUY signals
        if recommendation not in [Recommendation.BUY.value, Recommendation.STRONG_BUY.value]:
            return
        
        # Calculate position size using Kelly Criterion
        confidence = Decimal(str(data_point.get("confidence_score", buffett_score)))
        target_price = Decimal(str(data_point.get("target_price", data_point.get("price", 0))))
        stop_loss = Decimal(str(data_point.get("stop_loss", data_point.get("price", 0))))
        
        if stop_loss > 0:
            risk_reward_ratio = target_price / stop_loss
        else:
            risk_reward_ratio = Decimal("1.0")
        
        kelly_result = self.kelly_calculator.calculate_position_size(
            win_probability=confidence,
            risk_reward_ratio=risk_reward_ratio
        )
        
        position_size = Decimal(str(kelly_result["kelly_position_size"]))
        
        # Skip if position size is too small
        if position_size < Decimal("0.01"):
            return
        
        # Calculate position value
        position_value = self.current_capital * position_size
        entry_price = Decimal(str(data_point.get("price", 0)))
        
        # Apply commission and slippage
        position_value = position_value * (Decimal("1") - self.config.commission_per_trade)
        entry_price = entry_price * (Decimal("1") + self.config.slippage)
        
        # Calculate shares
        shares = position_value / entry_price
        
        # Check if we have enough capital
        if position_value > self.current_capital:
            logger.warning(f"Insufficient capital for {ticker} position")
            return
        
        # Open position
        open_positions[ticker] = {
            "entry_date": data_point["date"],
            "entry_price": entry_price,
            "shares": shares,
            "position_size": position_size,
            "buffett_score": buffett_score,
            "recommendation": recommendation,
            "target_price": target_price,
            "stop_loss": stop_loss
        }
        
        # Deduct capital
        self.current_capital -= position_value
        
        logger.info(
            f"OPEN {ticker}: ${entry_price:.2f}, "
            f"{shares:.2f} shares, "
            f"{position_size*100:.2f}% of portfolio, "
            f"Score: {buffett_score:.4f}"
        )
    
    async def _check_exit_signals(
        self,
        open_positions: Dict[str, Dict[str, Any]],
        data_point: Dict[str, Any]
    ):
        """Check for exit signals and close positions"""
        tickers_to_close = []
        
        for ticker, position in open_positions.items():
            current_price = Decimal(str(data_point.get("price", position["entry_price"])))
            
            # Exit conditions
            should_close = False
            exit_reason = ""
            
            # 1. Target price hit
            if current_price >= position["target_price"]:
                should_close = True
                exit_reason = "target_hit"
            
            # 2. Stop loss hit
            elif current_price <= position["stop_loss"]:
                should_close = True
                exit_reason = "stop_loss"
            
            # 3. Recommendation changed to SELL
            elif data_point.get("recommendation") in [Recommendation.SELL.value, Recommendation.STRONG_SELL.value]:
                should_close = True
                exit_reason = "signal_change"
            
            # 4. Holding period too long (e.g., 90 days)
            elif (data_point["date"] - position["entry_date"]).days > 90:
                should_close = True
                exit_reason = "timeout"
            
            if should_close:
                await self._close_position(ticker, position, current_price, data_point["date"], exit_reason)
                tickers_to_close.append(ticker)
        
        # Remove closed positions
        for ticker in tickers_to_close:
            del open_positions[ticker]
    
    async def _close_position(
        self,
        ticker: str,
        position: Dict[str, Any],
        exit_price: Decimal,
        exit_date: date,
        reason: str
    ):
        """Close a position and record the trade"""
        # Apply slippage
        exit_price = exit_price * (Decimal("1") - self.config.slippage)
        
        # Calculate proceeds
        proceeds = position["shares"] * exit_price
        proceeds = proceeds * (Decimal("1") - self.config.commission_per_trade)
        
        # Calculate return
        entry_value = position["shares"] * position["entry_price"]
        return_pct = ((proceeds - entry_value) / entry_value) * Decimal("100")
        
        # Add back to capital
        self.current_capital += proceeds
        
        # Determine win/loss
        win = return_pct > 0
        
        # Record trade
        trade = Trade(
            entry_date=position["entry_date"],
            exit_date=exit_date,
            ticker=ticker,
            entry_price=position["entry_price"],
            exit_price=exit_price,
            shares=position["shares"],
            position_size=position["position_size"],
            buffett_score=position["buffett_score"],
            recommendation=position["recommendation"],
            win=win,
            return_pct=return_pct
        )
        
        self.trades.append(trade)
        
        logger.info(
            f"CLOSE {ticker}: ${exit_price:.2f}, "
            f"Return: {return_pct:.2f}%, "
            f"Reason: {reason}, "
            f"Capital: ${self.current_capital:.2f}"
        )
    
    async def _close_all_positions(
        self,
        open_positions: Dict[str, Dict[str, Any]],
        last_data_point: Dict[str, Any]
    ):
        """Close all remaining positions at end of backtest"""
        for ticker, position in open_positions.items():
            current_price = Decimal(str(last_data_point.get("price", position["entry_price"])))
            await self._close_position(ticker, position, current_price, last_data_point["date"], "end_of_backtest")
    
    def _calculate_results(self) -> Dict[str, Any]:
        """Calculate backtesting results and statistics"""
        if not self.trades:
            return {
                "strategy_name": self.config.strategy_name,
                "initial_capital": float(self.config.initial_capital),
                "final_capital": float(self.current_capital),
                "total_return_percentage": 0.0,
                "annualized_return": 0.0,
                "max_drawdown_percentage": 0.0,
                "sharpe_ratio": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "average_return_per_trade": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "equity_curve": self.equity_curve,
                "trades": []
            }
        
        # Calculate basic statistics
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.win)
        losing_trades = total_trades - winning_trades
        win_rate = Decimal(winning_trades) / Decimal(total_trades) if total_trades > 0 else Decimal("0")
        
        # Calculate returns
        total_return = (self.current_capital - self.config.initial_capital) / self.config.initial_capital
        total_return_percentage = total_return * Decimal("100")
        
        # Calculate annualized return
        days = (self.config.end_date - self.config.start_date).days
        if days > 0:
            years = Decimal(days) / Decimal("365.25")
            annualized_return = ((Decimal("1") + total_return) ** (Decimal("1") / years) - Decimal("1")) * Decimal("100")
        else:
            annualized_return = Decimal("0")
        
        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown()
        
        # Calculate Sharpe ratio (assuming 3% risk-free rate)
        avg_return = sum(t.return_pct for t in self.trades) / Decimal(total_trades) if total_trades > 0 else Decimal("0")
        std_return = self._calculate_std_dev([t.return_pct for t in self.trades])
        if std_return > 0:
            sharpe_ratio = (avg_return - Decimal("3")) / std_return
        else:
            sharpe_ratio = Decimal("0")
        
        # Best and worst trades
        returns = [t.return_pct for t in self.trades]
        best_trade = max(returns) if returns else Decimal("0")
        worst_trade = min(returns) if returns else Decimal("0")
        
        return {
            "strategy_name": self.config.strategy_name,
            "initial_capital": float(self.config.initial_capital),
            "final_capital": float(self.current_capital),
            "total_return_percentage": float(total_return_percentage),
            "annualized_return": float(annualized_return),
            "max_drawdown_percentage": float(max_drawdown),
            "sharpe_ratio": float(sharpe_ratio),
            "win_rate": float(win_rate),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "average_return_per_trade": float(avg_return),
            "best_trade": float(best_trade),
            "worst_trade": float(worst_trade),
            "equity_curve": self.equity_curve,
            "trades": [
                {
                    "ticker": t.ticker,
                    "entry_date": t.entry_date.isoformat(),
                    "exit_date": t.exit_date.isoformat(),
                    "entry_price": float(t.entry_price),
                    "exit_price": float(t.exit_price),
                    "shares": float(t.shares),
                    "position_size": float(t.position_size),
                    "buffett_score": float(t.buffett_score),
                    "recommendation": t.recommendation,
                    "win": t.win,
                    "return_pct": float(t.return_pct)
                }
                for t in self.trades
            ]
        }
    
    def _calculate_max_drawdown(self) -> Decimal:
        """Calculate maximum drawdown from equity curve"""
        if not self.equity_curve:
            return Decimal("0")
        
        peak = Decimal(str(self.equity_curve[0]["capital"]))
        max_drawdown = Decimal("0")
        
        for point in self.equity_curve:
            capital = Decimal(str(point["capital"]))
            
            if capital > peak:
                peak = capital
            
            drawdown = (peak - capital) / peak if peak > 0 else Decimal("0")
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown * Decimal("100")
    
    def _calculate_std_dev(self, values: List[Decimal]) -> Decimal:
        """Calculate standard deviation of values"""
        if not values:
            return Decimal("0")
        
        mean = sum(values) / Decimal(len(values))
        variance = sum((v - mean) ** 2 for v in values) / Decimal(len(values))
        return variance.sqrt()


class BacktestingCLI:
    """CLI interface for backtesting"""
    
    def __init__(self):
        self.logger = logger
    
    def print_results(self, results: Dict[str, Any]):
        """Print backtesting results in a formatted way"""
        print("\n" + "=" * 60)
        print(f"BACKTEST RESULTS: {results['strategy_name']}")
        print("=" * 60)
        print(f"Initial Capital:     ${results['initial_capital']:,.2f}")
        print(f"Final Capital:       ${results['final_capital']:,.2f}")
        print(f"Total Return:        {results['total_return_percentage']:.2f}%")
        print(f"Annualized Return:   {results['annualized_return']:.2f}%")
        print(f"Max Drawdown:        {results['max_drawdown_percentage']:.2f}%")
        print(f"Sharpe Ratio:        {results['sharpe_ratio']:.2f}")
        print("-" * 60)
        print(f"Total Trades:        {results['total_trades']}")
        print(f"Winning Trades:      {results['winning_trades']}")
        print(f"Losing Trades:       {results['losing_trades']}")
        print(f"Win Rate:            {results['win_rate']:.2%}")
        print(f"Avg Return/Trade:    {results['average_return_per_trade']:.2f}%")
        print(f"Best Trade:          {results['best_trade']:.2f}%")
        print(f"Worst Trade:         {results['worst_trade']:.2f}%")
        print("=" * 60 + "\n")
    
    def save_results(self, results: Dict[str, Any], output_file: str):
        """Save backtesting results to JSON file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Results saved to {output_path}")
    
    async def run_from_config_file(self, config_file: str, data_file: str):
        """Run backtest from configuration and data files"""
        # Load configuration
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        config = BacktestConfig(
            strategy_name=config_data["strategy_name"],
            start_date=date.fromisoformat(config_data["start_date"]),
            end_date=date.fromisoformat(config_data["end_date"]),
            initial_capital=Decimal(str(config_data["initial_capital"])),
            weight_macro=Decimal(str(config_data["weight_macro"])),
            weight_commodity=Decimal(str(config_data["weight_commodity"])),
            weight_geo=Decimal(str(config_data["weight_geo"])),
            weight_insider=Decimal(str(config_data["weight_insider"])),
            weight_sentiment=Decimal(str(config_data["weight_sentiment"])),
            use_half_kelly=config_data.get("use_half_kelly", True),
            max_position_size=Decimal(str(config_data.get("max_position_size", "0.25")))
        )
        
        # Load historical data
        with open(data_file, 'r') as f:
            historical_data = json.load(f)
        
        # Convert date strings to date objects
        for point in historical_data:
            point["date"] = date.fromisoformat(point["date"])
        
        # Run backtest
        backtester = Backtester(config)
        results = await backtester.run_backtest(historical_data)
        
        # Print and save results
        self.print_results(results)
        
        output_file = f"backtest_results_{config.strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.save_results(results, output_file)
        
        return results


async def main():
    """Main entry point for CLI"""
    if len(sys.argv) < 3:
        print("Usage: python backtesting.py <config_file> <data_file>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    data_file = sys.argv[2]
    
    cli = BacktestingCLI()
    await cli.run_from_config_file(config_file, data_file)


if __name__ == "__main__":
    asyncio.run(main())


# ============================================================================
# PRD v9.0: The Time Machine - Historical Simulation
# ============================================================================

class HistoricalSnapshotter:
    """
    Historical Snapshotter for The Time Machine (PRD v9.0)
    
    Iterates over historical time periods and simulates AI debate runs
    as if "now" was that historical date.
    """
    
    def __init__(self, slm_orchestrator):
        """
        Initialize historical snapshotter
        
        Args:
            slm_orchestrator: SLMOrchestrator instance for running debate protocol
        """
        self.orchestrator = slm_orchestrator
        logger.info("Historical Snapshotter initialized")
    
    def generate_time_snapshots(
        self,
        start_date: date,
        end_date: date,
        interval_days: int = 7
    ) -> List[date]:
        """
        Generate list of historical snapshot dates
        
        Args:
            start_date: Start date for simulation
            end_date: End date for simulation
            interval_days: Days between snapshots (default weekly)
        
        Returns:
            List of snapshot dates
        """
        snapshots = []
        current = start_date
        
        while current <= end_date:
            snapshots.append(current)
            current = date.fromordinal(current.toordinal() + interval_days)
        
        logger.info(f"Generated {len(snapshots)} historical snapshots from {start_date} to {end_date}")
        return snapshots
    
    async def run_historical_simulation(
        self,
        snapshot_date: date,
        historical_news: str,
        ticker: str,
        system_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run debate protocol as if "now" was the historical snapshot date
        
        Args:
            snapshot_date: Historical date to simulate
            historical_news: News text from that date
            ticker: Stock ticker
            system_settings: System settings for the debate
        
        Returns:
            Debate result with historical context
        """
        logger.info(f"Running historical simulation for {ticker} on {snapshot_date}")
        
        # Mock system time (in production, would use time machine library)
        # For now, we just pass the historical date in the context
        context = {
            "simulation_date": snapshot_date.isoformat(),
            "is_historical": True,
            "historical_news": historical_news
        }
        
        # Run debate protocol
        result = await self.orchestrator.analyze_discovery(
            raw_data=historical_news,
            source=f"historical_simulation_{snapshot_date.isoformat()}",
            system_settings=system_settings
        )
        
        # Add historical context to result
        result["simulation_date"] = snapshot_date.isoformat()
        result["historical_context"] = context
        
        return result


class PerformanceAuditor:
    """
    Performance Auditor for The Time Machine (PRD v9.0)
    
    Compares AI recommendations against actual historical price movements
    and calculates performance metrics (Sharpe Ratio, Max Drawdown, Win Rate).
    """
    
    def __init__(self):
        """Initialize performance auditor"""
        logger.info("Performance Auditor initialized")
    
    def audit_backtest_performance(
        self,
        trades: List[Trade],
        equity_curve: List[Dict[str, Any]],
        initial_capital: Decimal
    ) -> Dict[str, Any]:
        """
        Audit backtest performance and calculate metrics
        
        Args:
            trades: List of trades from backtest
            equity_curve: Equity curve data
            initial_capital: Initial capital for backtest
        
        Returns:
            Performance metrics dictionary
        """
        # Calculate returns
        returns = []
        for i in range(1, len(equity_curve)):
            prev_capital = Decimal(str(equity_curve[i-1]["capital"]))
            curr_capital = Decimal(str(equity_curve[i]["capital"]))
            if prev_capital > 0:
                daily_return = (curr_capital - prev_capital) / prev_capital
                returns.append(float(daily_return))
        
        # Calculate Sharpe Ratio (assuming 2% annual risk-free rate)
        if len(returns) > 0:
            avg_return = sum(returns) / len(returns)
            std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            if std_return > 0:
                sharpe_ratio = (avg_return * 252 - 0.02) / (std_return * (252 ** 0.5))
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
        
        # Calculate Maximum Drawdown
        peak = initial_capital
        max_drawdown = Decimal("0")
        
        for point in equity_curve:
            capital = Decimal(str(point["capital"]))
            if capital > peak:
                peak = capital
            
            drawdown = (peak - capital) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Calculate Win Rate
        winning_trades = sum(1 for t in trades if t.win)
        win_rate = winning_trades / len(trades) if trades else 0.0
        
        # Calculate Total Return
        final_capital = Decimal(str(equity_curve[-1]["capital"])) if equity_curve else initial_capital
        total_return_pct = ((final_capital - initial_capital) / initial_capital) * 100
        
        # Kelly Criterion Effectiveness
        kelly_effective = self._audit_kelly_effectiveness(trades)
        
        metrics = {
            "total_return_pct": float(total_return_pct),
            "final_capital": float(final_capital),
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown_pct": float(max_drawdown * 100),
            "win_rate": win_rate,
            "total_trades": len(trades),
            "winning_trades": winning_trades,
            "kelly_effectiveness": kelly_effective,
            "audited_at": datetime.now().isoformat()
        }
        
        logger.info(f"Performance Audit: Return={total_return_pct:.2f}%, "
                   f"Sharpe={sharpe_ratio:.2f}, MaxDD={max_drawdown*100:.2f}%, "
                   f"WinRate={win_rate:.2%}")
        
        return metrics
    
    def _audit_kelly_effectiveness(self, trades: List[Trade]) -> Dict[str, Any]:
        """
        Audit Kelly Criterion effectiveness in position sizing
        
        Args:
            trades: List of trades
        
        Returns:
            Kelly effectiveness metrics
        """
        if not trades:
            return {"effective": False, "reason": "No trades to analyze"}
        
        # Calculate average position size
        avg_position_size = sum(t.position_size for t in trades) / len(trades)
        
        # Calculate if position sizing correlated with returns
        # (In production, would do statistical analysis)
        oversized_losses = sum(1 for t in trades if not t.win and t.position_size > avg_position_size * 1.5)
        
        effectiveness = {
            "avg_position_size": float(avg_position_size),
            "oversized_losses": oversized_losses,
            "effective": oversized_losses < len(trades) * 0.3,  # Less than 30% oversized losses
            "recommendation": "Kelly sizing appears effective" if oversized_losses < len(trades) * 0.3 else "Consider reducing Kelly fraction"
        }
        
        return effectiveness


async def run_historical_simulation_pipeline(
    start_date: date,
    end_date: date,
    tickers: List[str],
    slm_orchestrator,
    system_settings: Dict[str, Any],
    use_real_data: bool = True
) -> Dict[str, Any]:
    """
    Run complete historical simulation pipeline (PRD v9.0, Phase 10.6)
    
    Args:
        start_date: Start date for simulation
        end_date: End date for simulation
        tickers: List of tickers to simulate
        slm_orchestrator: SLMOrchestrator instance
        system_settings: System settings
        use_real_data: Whether to use real historical data (PRD v10.0 Phase 10.6)
    
    Returns:
        Complete simulation results
    """
    logger.info(f"Starting historical simulation pipeline from {start_date} to {end_date}")
    
    snapshotter = HistoricalSnapshotter(slm_orchestrator)
    auditor = PerformanceAuditor()
    
    # PRD v10.0 Phase 10.6: Fetch real historical data if enabled
    historical_data_fetcher = None
    if use_real_data:
        historical_data_fetcher = get_historical_data_fetcher()
        logger.info("Using real historical data from yfinance")
    
    # Generate snapshots
    snapshots = snapshotter.generate_time_snapshots(start_date, end_date, interval_days=7)
    
    # Run simulations for each snapshot
    all_results = []
    for snapshot_date in snapshots:
        for ticker in tickers:
            # PRD v10.0 Phase 10.6: Fetch real historical news if enabled
            if use_real_data and historical_data_fetcher:
                news_headlines = historical_data_fetcher.fetch_news_headlines(ticker, snapshot_date, snapshot_date)
                historical_news = " ".join([item["title"] for item in news_headlines])
                if not historical_news:
                    historical_news = f"No news available for {ticker} on {snapshot_date}"
            else:
                # Fallback to mock data
                historical_news = f"Historical news for {ticker} on {snapshot_date}"
            
            try:
                result = await snapshotter.run_historical_simulation(
                    snapshot_date=snapshot_date,
                    historical_news=historical_news,
                    ticker=ticker,
                    system_settings=system_settings
                )
                all_results.append(result)
            except Exception as e:
                logger.warning(f"Failed to simulate {ticker} on {snapshot_date}: {e}")
    
    # Calculate overall performance
    # (In production, would convert results to trades and run audit)
    
    return {
        "snapshots_analyzed": len(snapshots),
        "simulations_run": len(all_results),
        "use_real_data": use_real_data,
        "results": all_results,
        "completed_at": datetime.now().isoformat()
    }
