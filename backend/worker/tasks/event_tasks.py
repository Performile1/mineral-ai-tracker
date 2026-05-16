"""
Mineral AI Tracker - Event Processing Tasks (Phase 12.1 - Event Correlation Engine)
Description: Celery tasks for processing financial news events with AI summaries and price impact
"""

import os
from typing import Optional
from datetime import datetime, timedelta

from celery import shared_task
from loguru import logger

from utils.database import get_db_connection
from utils.authority_matrix import get_authority_score
from ml.ollama_client import OllamaClient


@shared_task
def process_event_summary(event_id: str) -> dict:
    """
    Process an event to generate AI summary using Phi-3.
    
    Args:
        event_id: UUID of the event to process
        
    Returns:
        Dict with processing status and result
    """
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Fetch event details
                cur.execute(
                    """
                    SELECT id, ticker, title, url, published_at
                    FROM asset_events
                    WHERE id = %s
                    """,
                    (event_id,)
                )
                row = cur.fetchone()
                
                if not row:
                    logger.error(f"Event {event_id} not found")
                    return {"status": "error", "message": "Event not found"}
                
                # Generate AI summary using Phi-3
                ollama = OllamaClient()
                summary_prompt = f"Summarize this financial news in exactly one short sentence: {row['title']}"
                
                try:
                    summary = ollama.generate_completion(
                        prompt=summary_prompt,
                        model=os.getenv("OLLAMA_PHI3_MODEL", "phi3")
                    )
                    
                    # Update event with AI summary
                    cur.execute(
                        """
                        UPDATE asset_events
                        SET ai_summary = %s
                        WHERE id = %s
                        """,
                        (summary, event_id)
                    )
                    conn.commit()
                    
                    logger.info(f"Generated AI summary for event {event_id}")
                    
                    return {
                        "status": "success",
                        "event_id": event_id,
                        "ai_summary": summary
                    }
                except Exception as e:
                    logger.error(f"Failed to generate AI summary: {e}")
                    return {"status": "error", "message": str(e)}
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to process event summary: {e}")
        return {"status": "error", "message": str(e)}


@shared_task
def calculate_price_impact(event_id: str) -> dict:
    """
    Calculate price impact for an event by comparing price at published_at vs 4 hours later.
    
    Critical Hotfix: Implemented actual price impact calculation using market API.
    Phase 12.1 Enhancement: Added robust error handling for market closures and missing data.
    
    Args:
        event_id: UUID of the event to process
        
    Returns:
        Dict with processing status and price impact
    """
    try:
        import httpx
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Fetch event details
                cur.execute(
                    """
                    SELECT id, ticker, published_at
                    FROM asset_events
                    WHERE id = %s
                    """,
                    (event_id,)
                )
                row = cur.fetchone()
                
                if not row:
                    logger.error(f"Event {event_id} not found")
                    return {"status": "error", "message": "Event not found"}
                
                ticker = row['ticker']
                published_at = row['published_at']
                
                # Calculate 4-hour later timestamp
                four_hours_later = published_at + timedelta(hours=4)
                
                # Fetch OHLC data from market API (Yahoo Finance proxy)
                market_api_url = os.getenv("MARKET_API_URL", "http://localhost:8000")
                
                price_impact = None
                
                try:
                    # Fetch price at published_at
                    start_time = published_at.strftime("%Y-%m-%d")
                    end_time = (published_at + timedelta(days=2)).strftime("%Y-%m-%d")  # Get 2 days of data to find 4h later
                    
                    # Use market.py to get OHLC data
                    ohlc_response = httpx.get(
                        f"{market_api_url}/api/market/ohlc/{ticker}",
                        params={"start_date": start_time, "end_date": end_time},
                        timeout=30
                    )
                    ohlc_data = ohlc_response.json()
                    
                    if ohlc_data and len(ohlc_data.get("data", [])) > 0:
                        ohlc_list = ohlc_data.get("data", [])
                        
                        # Find price at published_at (or closest available before)
                        price_at_event = None
                        price_4h_later = None
                        
                        # Convert published_at to date string for comparison
                        event_date_str = published_at.strftime("%Y-%m-%d")
                        event_time = published_at.time()
                        
                        # Find the first candle on or after the event date
                        for i, candle in enumerate(ohlc_list):
                            candle_date = candle.get("date")
                            if candle_date == event_date_str:
                                # Found the event day, use this as baseline
                                price_at_event = candle.get("close")
                                # Look for 4h later (next available candle)
                                for j in range(i + 1, min(i + 10, len(ohlc_list))):  # Look ahead up to 10 candles
                                    if ohlc_list[j].get("close"):
                                        price_4h_later = ohlc_list[j].get("close")
                                        break
                                break
                            elif candle_date > event_date_str and price_at_event is None:
                                # Event date not found, use first available after
                                price_at_event = candle.get("close")
                                # Look for next candle
                                if i + 1 < len(ohlc_list):
                                    price_4h_later = ohlc_list[i + 1].get("close")
                                break
                        
                        # Fallback: if no exact match, use first and last available
                        if price_at_event is None:
                            price_at_event = ohlc_list[0].get("close")
                            logger.warning(f"Using first available price for {ticker} at {published_at}")
                        
                        if price_4h_later is None and len(ohlc_list) > 1:
                            price_4h_later = ohlc_list[-1].get("close")
                            logger.warning(f"Using last available price for {ticker} 4h after {published_at}")
                        
                        # Validate prices
                        if price_at_event and price_at_event > 0:
                            if price_4h_later and price_4h_later > 0:
                                # Calculate percentage change
                                price_impact = ((price_4h_later - price_at_event) / price_at_event) * 100
                                logger.info(f"Calculated price impact for {ticker}: {price_impact:.2f}%")
                            else:
                                logger.warning(f"Invalid or missing 4h price for {ticker}")
                                price_impact = None
                        else:
                            logger.warning(f"Invalid or missing base price for {ticker}")
                            price_impact = None
                    else:
                        logger.warning(f"No OHLC data available for {ticker}")
                        price_impact = None
                        
                except httpx.TimeoutException:
                    logger.warning(f"Timeout fetching OHLC data for {ticker}")
                    price_impact = None
                except httpx.HTTPStatusError as e:
                    logger.warning(f"HTTP error fetching OHLC data for {ticker}: {e}")
                    price_impact = None
                except Exception as e:
                    logger.error(f"Failed to fetch OHLC data for {ticker}: {e}")
                    price_impact = None
                
                # Update event with price impact
                cur.execute(
                    """
                    UPDATE asset_events
                    SET price_impact_4h = %s
                    WHERE id = %s
                    """,
                    (price_impact, event_id)
                )
                conn.commit()
                
                return {
                    "status": "success",
                    "event_id": event_id,
                    "price_impact_4h": price_impact
                }
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to calculate price impact: {e}")
        return {"status": "error", "message": str(e)}


@shared_task
def process_new_event(
    ticker: str,
    title: str,
    url: Optional[str],
    source_type: str,
    source_name: Optional[str],
    published_at: str
) -> dict:
    """
    Complete pipeline: Create event, generate AI summary, and calculate price impact.
    
    Args:
        ticker: Asset ticker symbol
        title: Event title
        url: Optional URL to the event source
        source_type: Type of source for authority calculation
        source_name: Optional source name for authority calculation
        published_at: Publication timestamp (ISO format)
        
    Returns:
        Dict with processing status and event ID
    """
    try:
        # Calculate authority score
        authority_score = get_authority_score(source_type, source_name)
        
        # Create event in database
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO asset_events 
                    (ticker, published_at, title, url, source_authority_score)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (ticker, published_at, url) DO NOTHING
                    RETURNING id
                    """,
                    (ticker.upper(), published_at, title, url, authority_score)
                )
                row = cur.fetchone()
                conn.commit()
                
                if not row:
                    return {"status": "skipped", "message": "Event already exists"}
                
                event_id = row["id"]
                logger.info(f"Created event {event_id} for {ticker} with authority {authority_score}")
                
                # Trigger AI summary task
                process_event_summary.delay(event_id)
                
                # Trigger price impact calculation
                calculate_price_impact.delay(event_id)
                
                return {
                    "status": "success",
                    "event_id": str(event_id),
                    "authority_score": authority_score
                }
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to process new event: {e}")
        return {"status": "error", "message": str(e)}


# Phase 12.1 spec alias: the prompt names this orchestrator `process_event_pipeline`.
# `process_new_event` is kept as the canonical implementation for backwards
# compatibility with existing `.delay()` callers; both names resolve to the
# same Celery task.
process_event_pipeline = process_new_event
