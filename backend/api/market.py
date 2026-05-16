"""
Mineral AI Tracker - Market Data Proxy (PRD v8.6 Phase 8)
Version: 10.0
Description: Server-side proxy to Yahoo Finance public quote endpoint.
             Avoids CORS issues for the LiveTicker frontend component.
PRD v8.8 Phase 10: Added OHLC historical data endpoint for technical analysis.
PRD v9.0 Phase 9.9: Added graceful degradation (circuit breaker) for external API failures.
PRD v10.0 Phase 10.4: Added Redis caching for API cost reduction
"""

from typing import Optional, List, Dict, Any
import httpx
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from loguru import logger
from datetime import datetime, timedelta
from utils.cache import redis_cache
from utils.proxy_pool import get_proxy_pool
from api.deps import get_current_user

router = APIRouter(prefix="/api/market", tags=["market"])

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
USER_AGENT = "Mozilla/5.0 (compatible; MineralAI/8.6)"
TIMEOUT = 8.0


class Quote(BaseModel):
    symbol: str
    price: Optional[float] = None
    previous_close: Optional[float] = None
    currency: Optional[str] = None
    market_state: Optional[str] = None
    change_pct: Optional[float] = None
    long_name: Optional[str] = None


class OHLCData(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None


@redis_cache(ttl_seconds=60)  # Cache for 1 minute (live prices change frequently)
@router.get("/quote/{ticker}", response_model=Quote)
async def get_quote(ticker: str, current_user: dict = Depends(get_current_user)):
    """Single-ticker live quote via Yahoo Finance (server-side, no CORS)."""
    logger.info(f"User {current_user.get('id')} requesting quote for {ticker}")
    ticker = ticker.strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Empty ticker")

    proxy_pool = get_proxy_pool()
    proxy = proxy_pool.get_proxy()

    try:
        proxy_dict = proxy.to_dict() if proxy else None
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=True,
            proxy=proxy_dict
        ) as client:
            resp = await client.get(
                YAHOO_QUOTE_URL,
                params={"symbols": ticker},
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()
            
            if proxy:
                proxy_pool.record_success(proxy)
    except httpx.HTTPStatusError as e:
        # Phase 9.9: Graceful degradation - return empty Quote on 429/500 errors
        if e.response.status_code in [429, 500, 502, 503, 504]:
            logger.warning(f"Yahoo Finance rate limited or unavailable for {ticker}: {e}")
            if proxy:
                proxy_pool.record_failure(proxy)
            return Quote(symbol=ticker)  # Return empty quote instead of crashing
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")
    except httpx.TimeoutException:
        # Phase 9.9: Graceful degradation - return empty Quote on timeout
        logger.warning(f"Yahoo Finance timeout for {ticker}")
        if proxy:
            proxy_pool.record_failure(proxy)
        return Quote(symbol=ticker)
    except httpx.HTTPError as e:
        logger.warning(f"Yahoo quote fetch failed for {ticker}: {e}")
        if proxy:
            proxy_pool.record_failure(proxy)
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

    items = (data.get("quoteResponse") or {}).get("result") or []
    if not items:
        raise HTTPException(status_code=404, detail=f"No quote for {ticker}")

    item = items[0]
    return Quote(
        symbol=item.get("symbol", ticker),
        price=item.get("regularMarketPrice"),
        previous_close=item.get("regularMarketPreviousClose"),
        currency=item.get("currency"),
        market_state=item.get("marketState"),
        change_pct=item.get("regularMarketChangePercent"),
        long_name=item.get("longName") or item.get("shortName"),
    )


@redis_cache(ttl_seconds=60)  # Cache for 1 minute (live prices change frequently)
@router.get("/quotes")
async def get_quotes(symbols: str = Query(..., description="Comma-separated tickers"), current_user: dict = Depends(get_current_user)):
    """Multi-ticker batch quote (e.g., for the Bento Box top row)."""
    logger.info(f"User {current_user.get('id')} requesting batch quotes for {symbols}")
    syms = ",".join(s.strip() for s in symbols.split(",") if s.strip())
    if not syms:
        raise HTTPException(status_code=400, detail="No symbols")

    proxy_pool = get_proxy_pool()
    proxy = proxy_pool.get_proxy()

    try:
        proxy_dict = proxy.to_dict() if proxy else None
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=True,
            proxy=proxy_dict
        ) as client:
            resp = await client.get(
                YAHOO_QUOTE_URL,
                params={"symbols": syms},
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()
            
            if proxy:
                proxy_pool.record_success(proxy)
    except httpx.HTTPStatusError as e:
        # Phase 9.9: Graceful degradation - return empty list on 429/500 errors
        if e.response.status_code in [429, 500, 502, 503, 504]:
            logger.warning(f"Yahoo Finance rate limited or unavailable for batch quotes: {e}")
            if proxy:
                proxy_pool.record_failure(proxy)
            return {"quotes": []}  # Return empty list instead of crashing
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")
    except httpx.TimeoutException:
        # Phase 9.9: Graceful degradation - return empty list on timeout
        logger.warning("Yahoo Finance timeout for batch quotes")
        if proxy:
            proxy_pool.record_failure(proxy)
        return {"quotes": []}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

    items = (data.get("quoteResponse") or {}).get("result") or []
    return {
        "quotes": [
            {
                "symbol": it.get("symbol"),
                "price": it.get("regularMarketPrice"),
                "previous_close": it.get("regularMarketPreviousClose"),
                "change_pct": it.get("regularMarketChangePercent"),
                "currency": it.get("currency"),
                "market_state": it.get("marketState"),
            }
            for it in items
        ]
    }


@redis_cache(ttl_seconds=300)  # Cache for 5 minutes (OHLC data doesn't change instantly)
@router.get("/ohlc/{ticker}")
async def get_ohlc(
    ticker: str,
    period: str = Query("1y", description="Time period: 1m, 3m, 6m, 1y, 2y, 5y"),
    interval: str = Query("1d", description="Candle interval: 1d, 1wk, 1mo"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get historical OHLC data for technical analysis (PRD v8.8 Phase 10)

    Fetches daily candle data from Yahoo Finance for calculating technical indicators.
    Returns the last 250 days by default (sufficient for SMA 200).
    PRD v10.0 Phase 10.5: Added proxy rotation support
    """
    logger.info(f"User {current_user.get('id')} requesting OHLC for {ticker}")
    ticker = ticker.strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Empty ticker")

    # Map period to days
    period_map = {
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
    }
    days = period_map.get(period, 365)

    # Calculate timestamp range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    start_timestamp = int(start_date.timestamp())
    end_timestamp = int(end_date.timestamp())

    proxy_pool = get_proxy_pool()
    proxy = proxy_pool.get_proxy()

    try:
        proxy_dict = proxy.to_dict() if proxy else None
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=True,
            proxy=proxy_dict
        ) as client:
            resp = await client.get(
                YAHOO_CHART_URL,
                params={
                    "symbol": ticker,
                    "period1": start_timestamp,
                    "period2": end_timestamp,
                    "interval": interval,
                    "includePrePost": "true",
                },
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()
            
            if proxy:
                proxy_pool.record_success(proxy)
    except httpx.HTTPStatusError as e:
        # Phase 9.9: Graceful degradation - return empty OHLC on 429/500 errors
        if e.response.status_code in [429, 500, 502, 503, 504]:
            logger.warning(f"Yahoo Finance rate limited or unavailable for OHLC {ticker}: {e}")
            if proxy:
                proxy_pool.record_failure(proxy)
            return {
                "ticker": ticker,
                "period": period,
                "interval": interval,
                "data": [],
                "count": 0,
                "degraded": True
            }
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")
    except httpx.TimeoutException:
        # Phase 9.9: Graceful degradation - return empty OHLC on timeout
        logger.warning(f"Yahoo Finance timeout for OHLC {ticker}")
        if proxy:
            proxy_pool.record_failure(proxy)
        return {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "data": [],
            "count": 0,
            "degraded": True
        }
    except httpx.HTTPError as e:
        logger.warning(f"Yahoo OHLC fetch failed for {ticker}: {e}")
        if proxy:
            proxy_pool.record_failure(proxy)
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

    result = data.get("chart", {}).get("result", [])
    if not result:
        raise HTTPException(status_code=404, detail=f"No OHLC data for {ticker}")

    chart_data = result[0]
    timestamps = chart_data.get("timestamp", [])
    indicators = chart_data.get("indicators", {})
    quote_data = indicators.get("quote", [{}])[0]

    # Build OHLC list
    ohlc_list = []
    for i, ts in enumerate(timestamps):
        opens = quote_data.get("open", [])
        highs = quote_data.get("high", [])
        lows = quote_data.get("low", [])
        closes = quote_data.get("close", [])
        volumes = quote_data.get("volume", [])

        if i < len(opens) and i < len(highs) and i < len(lows) and i < len(closes):
            ohlc_list.append({
                "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
                "open": opens[i],
                "high": highs[i],
                "low": lows[i],
                "close": closes[i],
                "volume": volumes[i] if i < len(volumes) else None,
            })

    # Limit to last 250 candles for technical analysis
    ohlc_list = ohlc_list[-250:]

    return {
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "data": ohlc_list,
        "count": len(ohlc_list),
    }
