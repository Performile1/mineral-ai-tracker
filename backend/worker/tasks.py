"""
Mineral AI Tracker - Celery Tasks (PRD v10.0 Phase 10.3)
Version: 10.6
Description: Async tasks for analysis processing
PRD v10.0 Phase 10.4: Added retry logic, timeouts, and exponential backoff
PRD v10.0 Phase 11: Added backtesting task and rate limiting
"""

import os
import asyncio
from typing import Dict, Any, Optional
from datetime import date
from decimal import Decimal
from loguru import logger
from worker.celery_app import celery_app
from billiard.exceptions import SoftTimeLimitExceeded

from ml.ollama_client import OllamaClient
from ml.slm_orchestrator import SLMOrchestrator
from api.intelligence import load_system_settings_dict, save_signal_to_db, generate_signal_embedding
from quant.backtesting import Backtester, BacktestConfig
from quant.historical_data import get_historical_data_fetcher


@celery_app.task(bind=True, max_retries=3, soft_time_limit=180, time_limit=210, rate_limit='2/m')
def task_run_analysis(
    self, 
    ticker: str, 
    user_id: Optional[str] = None, 
    is_public: bool = False,
    ai_model: str = "local_swarm",
    raw_data: str = "",
    source: str = ""
) -> Dict[str, Any]:
    """
    Async analysis task for Celery worker (PRD v10.0 Phase 10.4)
    
    Args:
        ticker: Stock ticker symbol
        user_id: User UUID for data isolation
        is_public: Whether to share with Hive Mind
        ai_model: AI model to use (local_swarm, gemini_flash, gemini_pro) - Phase 13.2
        raw_data: Raw data for analysis (optional) - Phase 13.2
        source: Data source (optional) - Phase 13.2
    
    Returns:
        Dict with task result including signal_id
    
    PRD v10.0 Phase 10.4: Added retry logic, timeouts, and exponential backoff
    PRD v13.2 Phase 13.2: Added multi-model selector support
    """
    try:
        logger.info(f"Starting async analysis for {ticker} with {ai_model} (user_id: {user_id})")
        
        # Run the analysis synchronously in the worker
        # Note: We run this in a sync context since Celery tasks are synchronous
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_run_analysis_async(ticker, user_id, is_public, ai_model, raw_data, source))
            return {
                "status": "success",
                "signal_id": result.get("signal_id"),
                "ticker": ticker,
                "signal_type": result.get("signal_type"),
                "confidence": result.get("confidence"),
            }
        finally:
            loop.close()
            
    except SoftTimeLimitExceeded:
        logger.error(f"Task timeout for {ticker}: SoftTimeLimitExceeded")
        return {
            "status": "FAILED_TIMEOUT",
            "error": "Analysis exceeded time limit (3 minutes)",
            "ticker": ticker,
        }
    except Exception as e:
        # PRD v10.0 Phase 10.4: Retry logic with exponential backoff
        if self.request.retries < self.max_retries:
            # Calculate exponential backoff: 2^retry_count seconds
            backoff = 2 ** self.request.retries
            logger.warning(f"Retrying analysis for {ticker} (attempt {self.request.retries + 1}/{self.max_retries}) in {backoff}s: {e}")
            raise self.retry(exc=e, countdown=backoff)
        
        logger.error(f"Analysis task failed for {ticker} after {self.max_retries} retries: {e}")
        return {
            "status": "error",
            "error": str(e),
            "ticker": ticker,
        }


async def _run_analysis_async(
    ticker: str, 
    user_id: Optional[str], 
    is_public: bool,
    ai_model: str = "local_swarm",
    raw_data: str = "",
    source: str = ""
) -> Dict[str, Any]:
    """Helper function to run analysis asynchronously within Celery task
    Phase 13.2: Added ai_model parameter for multi-model support
    """
    from scrapers.discovery import discover_news
    from scrapers.crawler import fetch_markdown
    from datetime import datetime
    from ml.gemini_client import GeminiClient
    
    # Initialize components
    ollama = OllamaClient()
    orchestrator = SLMOrchestrator(ollama)
    sys_settings = load_system_settings_dict()
    
    # Phase 13.2: If raw_data and source are provided, skip discovery/crawl and use provided data
    if raw_data and source:
        logger.info(f"Using provided raw data for {ticker} with {ai_model}")
        combined_chunks = [raw_data]
        articles = []
    else:
        # Step 1: Discovery
        logger.info(f"Step 1: Discovery for {ticker}")
        articles = await discover_news(ticker)
        if not articles:
            raise Exception(f"No articles found for {ticker}")
        
        # Step 2: Crawl
        logger.info(f"Step 2: Crawl for {ticker}")
        crawl_tasks = [fetch_markdown(item["url"]) for item in articles]
        markdowns = await asyncio.gather(*crawl_tasks, return_exceptions=True)
        
        combined_chunks = []
        for item, md in zip(articles, markdowns):
            content = "" if isinstance(md, Exception) or md is None else str(md)
            combined_chunks.append(content)
    
    # Phase 13.2: Route to appropriate AI model
    if ai_model == "local_swarm":
        # Use existing SLM orchestrator
        logger.info(f"Using Local Swarm for {ticker}")
        raw_combined = "\n\n".join(combined_chunks)
        result = await orchestrator.analyze_discovery(
            raw_data=raw_combined,
            source=source or "Yahoo Finance",
            system_settings=sys_settings,
        )
    else:
        # Use Gemini client
        logger.info(f"Using {ai_model} for {ticker}")
        gemini_client = GeminiClient()
        if not gemini_client.is_available():
            raise Exception(f"Gemini API not configured for {ai_model}")
        
        raw_combined = "\n\n".join(combined_chunks)
        if ai_model == "gemini_flash":
            analysis = await gemini_client.generate_flash(raw_combined)
        else:  # gemini_pro
            analysis = await gemini_client.generate_pro(raw_combined)
        
        # Format Gemini response to match expected structure
        result = {
            "signal_type": "HOLD",
            "confidence_score": 75,
            "recommendation": analysis,
            "consensus_score": 0.5,
            "pydantic_passed": True,
            "pydantic_errors": [],
            "debate_log": []
        }
    
    # Step 3: Save to database (only for local_swarm, Gemini results are not saved to signals table)
    logger.info(f"Step 3: Save to database for {ticker}")
    if ai_model == "local_swarm":
        threshold = sys_settings.get("min_confidence_score", 85)
        if result.pydantic_passed and result.confidence_score >= threshold:
            embedding = await generate_signal_embedding(ollama, raw_combined)
            signal_id = save_signal_to_db(
                result,
                asset_id=ticker,
                source=source or f"celery:{ticker}",
                user_id=user_id,
                embedding=embedding,
            )
            
            # Trigger Sentinel alerts if configured
            await orchestrator._trigger_sentinel_alerts(
                signal_type=result.signal_type,
                confidence=result.confidence_score,
                recommendation=result.recommendation,
                ticker=ticker,
                hive_data={}
            )
        else:
            signal_id = None
    else:
        signal_id = None  # Gemini results not saved to signals table
    
    return {
        "signal_id": signal_id,
        "signal_type": result.signal_type,
        "confidence": result.confidence_score,
        "recommendation": result.recommendation,
    }


@celery_app.task(bind=True, max_retries=2, soft_time_limit=600, time_limit=660)
def task_run_backtest(
    self,
    strategy_name: str,
    start_date: str,
    end_date: str,
    initial_capital: float,
    tickers: list,
    weights: Dict[str, float],
    use_half_kelly: bool = True,
    max_position_size: float = 0.25,
    use_real_data: bool = True
) -> Dict[str, Any]:
    """
    Async backtesting task for Celery worker (PRD v10.0 Phase 11)
    
    Args:
        strategy_name: Name of the strategy
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        initial_capital: Initial capital for backtest
        tickers: List of tickers to backtest
        weights: Weights for Buffett Score factors
        use_half_kelly: Use half Kelly criterion
        max_position_size: Maximum position size
        use_real_data: Use real historical data from yfinance
    
    Returns:
        Dict with backtest results
    """
    try:
        logger.info(f"Starting backtest for strategy {strategy_name} with {len(tickers)} tickers")
        
        # Run backtesting synchronously in the worker
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _run_backtest_async(
                    strategy_name=strategy_name,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    tickers=tickers,
                    weights=weights,
                    use_half_kelly=use_half_kelly,
                    max_position_size=max_position_size,
                    use_real_data=use_real_data
                )
            )
            return {
                "status": "success",
                "strategy_name": strategy_name,
                "results": result
            }
        finally:
            loop.close()
            
    except SoftTimeLimitExceeded:
        logger.error(f"Backtest timeout for {strategy_name}: SoftTimeLimitExceeded")
        return {
            "status": "FAILED_TIMEOUT",
            "error": "Backtest exceeded time limit (10 minutes)",
            "strategy_name": strategy_name,
        }
    except Exception as e:
        # Retry logic with exponential backoff
        if self.request.retries < self.max_retries:
            backoff = 2 ** self.request.retries
            logger.warning(f"Retrying backtest for {strategy_name} (attempt {self.request.retries + 1}/{self.max_retries}) in {backoff}s: {e}")
            raise self.retry(exc=e, countdown=backoff)
        
        logger.error(f"Backtest task failed for {strategy_name} after {self.max_retries} retries: {e}")
        return {
            "status": "error",
            "error": str(e),
            "strategy_name": strategy_name,
        }


async def _run_backtest_async(
    strategy_name: str,
    start_date: str,
    end_date: str,
    initial_capital: float,
    tickers: list,
    weights: Dict[str, float],
    use_half_kelly: bool,
    max_position_size: float,
    use_real_data: bool
) -> Dict[str, Any]:
    """Helper function to run backtesting asynchronously within Celery task"""
    from datetime import date
    
    start_dt = date.fromisoformat(start_date)
    end_dt = date.fromisoformat(end_date)
    
    # Fetch historical data
    data_fetcher = get_historical_data_fetcher()
    
    if use_real_data:
        # Create backtesting dataset with real historical data
        logger.info(f"Fetching real historical data for {len(tickers)} tickers")
        historical_data = data_fetcher.create_backtesting_dataset(
            tickers=tickers,
            start_date=start_dt,
            end_date=end_dt,
            interval="1d"
        )
    else:
        # Use mock data (placeholder)
        logger.warning("Using mock data for backtesting")
        historical_data = []
    
    if not historical_data:
        raise Exception("No historical data available for backtesting")
    
    # Create backtest configuration
    config = BacktestConfig(
        strategy_name=strategy_name,
        start_date=start_dt,
        end_date=end_dt,
        initial_capital=Decimal(str(initial_capital)),
        weight_macro=Decimal(str(weights.get("macro", 0.2))),
        weight_commodity=Decimal(str(weights.get("commodity", 0.2))),
        weight_geo=Decimal(str(weights.get("geo", 0.2))),
        weight_insider=Decimal(str(weights.get("insider", 0.2))),
        weight_sentiment=Decimal(str(weights.get("sentiment", 0.2))),
        use_half_kelly=use_half_kelly,
        max_position_size=Decimal(str(max_position_size))
    )
    
    # Run backtest
    logger.info(f"Running backtest with {len(historical_data)} data points")
    backtester = Backtester(config)
    results = await backtester.run_backtest(historical_data)
    
    logger.info(f"Backtest completed: {results['total_return_percentage']:.2f}% return")
    
    return results
