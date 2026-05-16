"""
Mineral AI Tracker - Historical Data Fetcher (PRD v10.0 Phase 10.6)
Version: 11.0
Description: Fetch real historical data for backtesting (yfinance integration)
PRD v10.0 Phase 11: Added Alpha Vantage News API fallback
"""

import yfinance as yf
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger
import httpx
from config import settings


class HistoricalDataFetcher:
    """
    Fetch real historical data for backtesting (PRD v10.0 Phase 10.6)
    
    Uses yfinance to fetch:
    - Historical price data (OHLCV)
    - Historical news headlines (if available)
    - Macro data for the time period
    """
    
    def __init__(self):
        """Initialize historical data fetcher"""
        logger.info("Historical Data Fetcher initialized")
    
    def fetch_price_history(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical price data for a ticker
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval (1d, 1wk, 1mo)
        
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Fetching price history for {ticker} from {start_date} to {end_date}")
        
        try:
            # Convert date strings to yfinance format
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Fetch data using yfinance
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(start=start_str, end=end_str, interval=interval)
            
            if hist.empty:
                logger.warning(f"No price data found for {ticker} in date range")
                return pd.DataFrame()
            
            # Reset index to make Date a column
            hist = hist.reset_index()
            
            # Rename columns to standard format
            hist = hist.rename(columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
                "Adj Close": "adj_close"
            })
            
            # Convert date to date object
            hist["date"] = pd.to_datetime(hist["date"]).dt.date
            
            logger.info(f"Fetched {len(hist)} price data points for {ticker}")
            return hist
            
        except Exception as e:
            logger.error(f"Failed to fetch price history for {ticker}: {e}")
            return pd.DataFrame()
    
    def fetch_multiple_tickers(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical price data for multiple tickers
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval (1d, 1wk, 1mo)
        
        Returns:
            Dictionary mapping ticker to DataFrame
        """
        logger.info(f"Fetching price history for {len(tickers)} tickers")
        
        results = {}
        for ticker in tickers:
            hist = self.fetch_price_history(ticker, start_date, end_date, interval)
            if not hist.empty:
                results[ticker] = hist
        
        logger.info(f"Successfully fetched data for {len(results)}/{len(tickers)} tickers")
        return results
    
    def fetch_news_headlines(
        self,
        ticker: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical news headlines for a ticker
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for news
            end_date: End date for news
        
        Returns:
            List of news headline dictionaries
        """
        logger.info(f"Fetching news headlines for {ticker} from {start_date} to {end_date}")
        
        # Try yfinance first
        yf_news = self._fetch_yfinance_news(ticker, start_date, end_date)
        if yf_news:
            return yf_news
        
        # Fallback to Alpha Vantage if configured
        if hasattr(settings, 'ALPHA_VANTAGE_API_KEY') and settings.ALPHA_VANTAGE_API_KEY:
            logger.info("Falling back to Alpha Vantage News API")
            return self._fetch_alpha_vantage_news(ticker, start_date, end_date)
        
        logger.warning(f"No news found for {ticker}")
        return []
    
    def _fetch_yfinance_news(
        self,
        ticker: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Fetch news from yfinance"""
        try:
            ticker_obj = yf.Ticker(ticker)
            news = ticker_obj.news
            
            if not news:
                return []
            
            # Filter news by date range and format
            filtered_news = []
            for item in news:
                pub_date = item.get("providerPublishTime")
                if pub_date:
                    pub_dt = datetime.fromtimestamp(pub_date).date()
                    if start_date <= pub_dt <= end_date:
                        filtered_news.append({
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "published": pub_dt.isoformat(),
                            "source": item.get("publisher", "")
                        })
            
            logger.info(f"Fetched {len(filtered_news)} news headlines from yfinance for {ticker}")
            return filtered_news
            
        except Exception as e:
            logger.warning(f"Failed to fetch yfinance news for {ticker}: {e}")
            return []
    
    def _fetch_alpha_vantage_news(
        self,
        ticker: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Fetch news from Alpha Vantage News API (PRD v10.0 Phase 11)"""
        try:
            base_url = "https://www.alphavantage.co/query"
            params = {
                "function": "NEWS_SENTIMENT",
                "tickers": ticker,
                "time_from": start_date.strftime("%Y%m%dT%H%M%S"),
                "time_to": end_date.strftime("%Y%m%dT%H%M%S"),
                "apikey": settings.ALPHA_VANTAGE_API_KEY
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if "feed" not in data:
                logger.warning(f"No news feed in Alpha Vantage response for {ticker}")
                return []
            
            # Format news headlines
            news_headlines = []
            for item in data["feed"]:
                news_headlines.append({
                    "title": item.get("title", ""),
                    "link": item.get("url", ""),
                    "published": item.get("time_published", ""),
                    "source": item.get("source", "")
                })
            
            logger.info(f"Fetched {len(news_headlines)} news headlines from Alpha Vantage for {ticker}")
            return news_headlines
            
        except Exception as e:
            logger.warning(f"Failed to fetch Alpha Vantage news for {ticker}: {e}")
            return []
    
    def create_backtesting_dataset(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        """
        Create a complete backtesting dataset with price and news data
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date for backtesting
            end_date: End date for backtesting
            interval: Data interval (1d, 1wk, 1mo)
        
        Returns:
            List of historical data points for backtesting
        """
        logger.info(f"Creating backtesting dataset from {start_date} to {end_date}")
        
        # Fetch price data for all tickers
        price_data = self.fetch_multiple_tickers(tickers, start_date, end_date, interval)
        
        # Build dataset
        dataset = []
        
        for ticker, hist in price_data.items():
            # Fetch news for this ticker
            news_headlines = self.fetch_news_headlines(ticker, start_date, end_date)
            news_by_date = {item["published"]: item for item in news_headlines}
            
            # Create data points for each date
            for _, row in hist.iterrows():
                data_point = {
                    "date": row["date"],
                    "ticker": ticker,
                    "price": float(row["close"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "volume": float(row["volume"]) if pd.notna(row["volume"]) else 0,
                    "news": news_by_date.get(row["date"].isoformat(), {}).get("title", ""),
                    "confidence_score": 0.5,  # Will be calculated by AI
                    "recommendation": "HOLD",  # Will be calculated by AI
                    "target_price": row["close"] * 1.1,  # Will be calculated by AI
                    "stop_loss": row["close"] * 0.95,  # Will be calculated by AI
                }
                dataset.append(data_point)
        
        # Sort by date
        dataset.sort(key=lambda x: x["date"])
        
        logger.info(f"Created backtesting dataset with {len(dataset)} data points")
        return dataset
    
    def fetch_macro_data(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical macro data (interest rates, GDP, etc.)
        
        Args:
            start_date: Start date for macro data
            end_date: End date for macro data
        
        Returns:
            Dictionary mapping macro indicator to DataFrame
        """
        logger.info(f"Fetching macro data from {start_date} to {end_date}")
        
        macro_data = {}
        
        # Fetch 10-year Treasury yield (^TNX) as proxy for interest rates
        try:
            tn10_hist = self.fetch_price_history("^TNX", start_date, end_date)
            if not tn10_hist.empty:
                macro_data["interest_rate_10y"] = tn10_hist
        except Exception as e:
            logger.warning(f"Failed to fetch 10y Treasury data: {e}")
        
        # Fetch S&P 500 (^GSPC) as market benchmark
        try:
            spy_hist = self.fetch_price_history("^GSPC", start_date, end_date)
            if not spy_hist.empty:
                macro_data["sp500"] = spy_hist
        except Exception as e:
            logger.warning(f"Failed to fetch S&P 500 data: {e}")
        
        logger.info(f"Fetched {len(macro_data)} macro indicators")
        return macro_data


def get_historical_data_fetcher() -> HistoricalDataFetcher:
    """Get global historical data fetcher instance"""
    return HistoricalDataFetcher()
