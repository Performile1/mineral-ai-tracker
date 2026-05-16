"""
Mineral AI Tracker - Financial Data Scrapers
Version: 3.0
Description: Scrapers for financial data from Avanza, Nordnet, Finansinspektionen
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from loguru import logger

from .base_scraper import BaseScraper


class AvanzaScraper(BaseScraper):
    """Avanza (Swedish broker) scraper for stock prices and data"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        super().__init__(
            name="Avanza",
            proxy_list=proxy_list,
            rate_limit_per_minute=120,
            rate_limit_per_hour=2000
        )
        self.base_url = "https://www.avanza.se"
    
    async def scrape_stock_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Scrape stock price data from Avanza
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Stock price data dictionary
        """
        logger.info(f"Scraping Avanza stock price for {ticker}")
        
        # Avanza API endpoint for stock data
        url = f"{self.base_url}/_api/market-guide/stock/{ticker}/overview"
        
        data = await self.fetch_json(url)
        
        if not data:
            logger.error(f"Failed to fetch Avanza data for {ticker}")
            return None
        
        try:
            stock_data = {
                "ticker": ticker,
                "current_price": data.get("lastPrice"),
                "change_percentage": data.get("changePercent"),
                "volume": data.get("totalVolumeTraded"),
                "market_cap": data.get("marketCapital"),
                "pe_ratio": data.get("peRatio"),
                "dividend_yield": data.get("directYield"),
                "currency": data.get("currency"),
                "exchange": "Avanza",
                "scraped_at": datetime.now().isoformat()
            }
            
            logger.info(f"Scraped price for {ticker}: {stock_data['current_price']}")
            return stock_data
            
        except Exception as e:
            logger.error(f"Error parsing Avanza data for {ticker}: {e}")
            return None
    
    async def scrape_multiple_stocks(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Scrape multiple stocks from Avanza
        
        Args:
            tickers: List of ticker symbols
        
        Returns:
            Dictionary mapping tickers to stock data
        """
        results = {}
        
        for ticker in tickers:
            try:
                data = await self.scrape_stock_price(ticker)
                if data:
                    results[ticker] = data
                # Small delay between requests
                import asyncio
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error scraping {ticker}: {e}")
                results[ticker] = None
        
        return results
    
    async def scrape_company_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Scrape company information from Avanza"""
        logger.info(f"Scraping Avanza company info for {ticker}")
        
        url = f"{self.base_url}/_api/market-guide/stock/{ticker}/company"
        
        data = await self.fetch_json(url)
        
        if not data:
            logger.error(f"Failed to fetch Avanza company info for {ticker}")
            return None
        
        try:
            company_data = {
                "ticker": ticker,
                "name": data.get("name"),
                "sector": data.get("branch"),
                "country": data.get("country"),
                "isin": data.get("isin"),
                "employees": data.get("numberOfEmployees"),
                "description": data.get("description"),
                "website": data.get("website"),
                "scraped_at": datetime.now().isoformat()
            }
            
            return company_data
            
        except Exception as e:
            logger.error(f"Error parsing Avanza company info for {ticker}: {e}")
            return None


class NordnetScraper(BaseScraper):
    """Nordnet (Nordic broker) scraper for stock prices and data"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        super().__init__(
            name="Nordnet",
            proxy_list=proxy_list,
            rate_limit_per_minute=120,
            rate_limit_per_hour=2000
        )
        self.base_url = "https://www.nordnet.se"
    
    async def scrape_stock_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Scrape stock price data from Nordnet
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Stock price data dictionary
        """
        logger.info(f"Scraping Nordnet stock price for {ticker}")
        
        # Nordnet API endpoint for stock data
        url = f"{self.base_url}/api/2/instruments/{ticker}/marketprice"
        
        data = await self.fetch_json(url)
        
        if not data:
            logger.error(f"Failed to fetch Nordnet data for {ticker}")
            return None
        
        try:
            stock_data = {
                "ticker": ticker,
                "current_price": data.get("price"),
                "change_percentage": data.get("change"),
                "volume": data.get("volume"),
                "market_cap": data.get("market_cap"),
                "currency": data.get("currency"),
                "exchange": "Nordnet",
                "scraped_at": datetime.now().isoformat()
            }
            
            logger.info(f"Scraped price for {ticker}: {stock_data['current_price']}")
            return stock_data
            
        except Exception as e:
            logger.error(f"Error parsing Nordnet data for {ticker}: {e}")
            return None
    
    async def scrape_multiple_stocks(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Scrape multiple stocks from Nordnet"""
        results = {}
        
        for ticker in tickers:
            try:
                data = await self.scrape_stock_price(ticker)
                if data:
                    results[ticker] = data
                import asyncio
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error scraping {ticker}: {e}")
                results[ticker] = None
        
        return results


class FinansinspektionenScraper(BaseScraper):
    """Finansinspektionen (Swedish Financial Supervisory Authority) scraper for insider data"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        super().__init__(
            name="Finansinspektionen",
            proxy_list=proxy_list,
            rate_limit_per_minute=30,
            rate_limit_per_hour=500
        )
        self.base_url = "https://www.fi.se"
    
    async def scrape_insider_trades(self, ticker: Optional[str] = None, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Scrape insider trading data from Finansinspektionen
        
        Args:
            ticker: Optional ticker symbol to filter
            days_back: Number of days to look back
        
        Returns:
            List of insider trade records
        """
        logger.info(f"Scraping Finansinspektionen insider trades (last {days_back} days)")
        
        # FI provides insider data via API
        url = f"{self.base_url}/api/insidertrades"
        
        params = {
            "fromDate": (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d"),
            "toDate": datetime.now().strftime("%Y-%m-%d")
        }
        
        if ticker:
            params["issuer"] = ticker
        
        data = await self.fetch_json(url, params=params)
        
        if not data:
            logger.error("Failed to fetch FI insider data")
            return []
        
        insider_data = []
        
        try:
            records = data.get("trades", [])
            for record in records:
                trade = {
                    "ticker": record.get("issuer"),
                    "insider_name": record.get("person"),
                    "position": record.get("position"),
                    "trade_type": record.get("transactionType"),  # buy/sell
                    "shares": record.get("numberOfShares"),
                    "price": record.get("price"),
                    "total_value": record.get("totalValue"),
                    "trade_date": record.get("transactionDate"),
                    "notification_date": record.get("notificationDate"),
                    "source": "Finansinspektionen",
                    "scraped_at": datetime.now().isoformat()
                }
                insider_data.append(trade)
            
            logger.info(f"Scraped {len(insider_data)} insider trades from FI")
            
        except Exception as e:
            logger.error(f"Error parsing FI insider data: {e}")
        
        return insider_data
    
    async def calculate_insider_score(self, ticker: str, days_back: int = 90) -> Optional[float]:
        """
        Calculate insider sentiment score based on recent insider trades
        
        Args:
            ticker: Stock ticker symbol
            days_back: Number of days to analyze
        
        Returns:
            Insider score between 0 and 1
        """
        trades = await self.scrape_insider_trades(ticker, days_back)
        
        if not trades:
            return 0.5  # Neutral if no data
        
        buy_volume = sum(t.get("shares", 0) for t in trades if t.get("trade_type") == "buy")
        sell_volume = sum(t.get("shares", 0) for t in trades if t.get("trade_type") == "sell")
        
        total_volume = buy_volume + sell_volume
        
        if total_volume == 0:
            return 0.5
        
        # Score based on buy vs sell ratio
        buy_ratio = buy_volume / total_volume
        
        # Normalize to 0-1 range with slight bias towards neutral
        score = 0.3 + (buy_ratio * 0.4)
        
        logger.info(f"Insider score for {ticker}: {score:.4f} (buy: {buy_volume}, sell: {sell_volume})")
        
        return score


class FinanceScraperManager:
    """Manager for all financial scrapers"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        self.scrapers = {
            "Avanza": AvanzaScraper(proxy_list),
            "Nordnet": NordnetScraper(proxy_list),
            "Finansinspektionen": FinansinspektionenScraper(proxy_list)
        }
    
    async def scrape_stock_prices(self, tickers: List[str], sources: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Scrape stock prices from specified sources
        
        Args:
            tickers: List of ticker symbols
            sources: List of source names (None = all)
        
        Returns:
            Dictionary mapping tickers to price data
        """
        sources = sources or ["Avanza", "Nordnet"]
        results = {ticker: {} for ticker in tickers}
        
        for source_name in sources:
            if source_name in self.scrapers:
                scraper = self.scrapers[source_name]
                try:
                    if source_name in ["Avanza", "Nordnet"]:
                        prices = await scraper.scrape_multiple_stocks(tickers)
                        for ticker, data in prices.items():
                            if ticker in results:
                                results[ticker][source_name] = data
                except Exception as e:
                    logger.error(f"Error scraping {source_name}: {e}")
        
        return results
    
    async def scrape_insider_data(self, tickers: List[str], days_back: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape insider trading data for multiple tickers
        
        Args:
            tickers: List of ticker symbols
            days_back: Number of days to look back
        
        Returns:
            Dictionary mapping tickers to insider trade data
        """
        scraper = self.scrapers["Finansinspektionen"]
        results = {}
        
        for ticker in tickers:
            try:
                trades = await scraper.scrape_insider_trades(ticker, days_back)
                results[ticker] = trades
            except Exception as e:
                logger.error(f"Error scraping insider data for {ticker}: {e}")
                results[ticker] = []
        
        return results
    
    async def calculate_all_insider_scores(self, tickers: List[str], days_back: int = 90) -> Dict[str, float]:
        """
        Calculate insider scores for all tickers
        
        Args:
            tickers: List of ticker symbols
            days_back: Number of days to analyze
        
        Returns:
            Dictionary mapping tickers to insider scores
        """
        scraper = self.scrapers["Finansinspektionen"]
        results = {}
        
        for ticker in tickers:
            try:
                score = await scraper.calculate_insider_score(ticker, days_back)
                results[ticker] = score
            except Exception as e:
                logger.error(f"Error calculating insider score for {ticker}: {e}")
                results[ticker] = 0.5  # Neutral on error
        
        return results
    
    def log_stats(self):
        """Log statistics from all scrapers"""
        for name, scraper in self.scrapers.items():
            logger.info(f"--- {name} Stats ---")
            scraper.log_stats()
