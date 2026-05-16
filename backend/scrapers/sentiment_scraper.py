"""
Mineral AI Tracker - Trader Sentiment Scraper
Version: 3.0
Description: Scraper for trader sentiment from Placera, Reddit, eToro, trader blogs
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import re

from .base_scraper import BaseScraper


class PlaceraScraper(BaseScraper):
    """Placera (Swedish financial forum) scraper"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        super().__init__(
            name="Placera",
            proxy_list=proxy_list,
            rate_limit_per_minute=30,
            rate_limit_per_hour=500
        )
        self.base_url = "https://www.placera.se"
    
    async def scrape_forum_posts(self, ticker: Optional[str] = None, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Scrape forum posts from Placera
        
        Args:
            ticker: Optional ticker to filter
            days_back: Number of days to look back
        
        Returns:
            List of sentiment records
        """
        logger.info(f"Scraping Placera forum posts (last {days_back} days)")
        
        # Placera forum URL
        url = f"{self.base_url}/forum"
        
        if ticker:
            url += f"/{ticker}"
        
        html = await self.fetch_html(url)
        
        if not html:
            logger.error("Failed to fetch Placera forum")
            return []
        
        soup = self.parse_html(html)
        posts = []
        
        try:
            # Parse forum posts (implementation depends on actual HTML structure)
            for item in soup.find_all("div", class_="forum-post"):
                post = {
                    "source_platform": "placera",
                    "source_url": self.base_url + item.find("a")["href"] if item.find("a") else url,
                    "author_handle": item.find("span", class_="author").text.strip() if item.find("span", class_="author") else None,
                    "post_title": item.find("h3").text.strip() if item.find("h3") else None,
                    "post_content": item.find("div", class_="content").text.strip() if item.find("div", class_="content") else None,
                    "post_date": self._parse_date(item.find("time")["datetime"] if item.find("time") else None),
                    "sentiment_score": self._analyze_sentiment(item.get_text()),
                    "confidence": 0.7,  # Base confidence
                    "scraped_at": datetime.now().isoformat()
                }
                
                # Filter by date if specified
                if days_back and post["post_date"]:
                    post_date = datetime.fromisoformat(post["post_date"])
                    if (datetime.now() - post_date).days > days_back:
                        continue
                
                posts.append(post)
            
            logger.info(f"Scraped {len(posts)} posts from Placera")
            
        except Exception as e:
            logger.error(f"Error parsing Placera posts: {e}")
        
        return posts
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string to ISO format"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str).isoformat()
        except:
            return None
    
    def _analyze_sentiment(self, text: str) -> float:
        """Basic sentiment analysis (can be enhanced with NLP)"""
        if not text:
            return 0.0
        
        # Simple keyword-based sentiment
        positive_keywords = ["köp", "bra", "stark", "uppgång", "bullish", "long"]
        negative_keywords = ["sälj", "dålig", "svag", "nedgång", "bearish", "short"]
        
        text_lower = text.lower()
        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total


class RedditScraper(BaseScraper):
    """Reddit scraper for trading subreddits"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        super().__init__(
            name="Reddit",
            proxy_list=proxy_list,
            rate_limit_per_minute=60,
            rate_limit_per_hour=1000
        )
        self.base_url = "https://www.reddit.com"
    
    async def scrape_subreddit_posts(
        self,
        subreddit: str = "investing",
        ticker: Optional[str] = None,
        days_back: int = 7,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Scrape posts from Reddit subreddit
        
        Args:
            subreddit: Subreddit name
            ticker: Optional ticker to filter
            days_back: Number of days to look back
            limit: Maximum number of posts to fetch
        
        Returns:
            List of sentiment records
        """
        logger.info(f"Scraping r/{subreddit} posts (last {days_back} days)")
        
        # Reddit JSON API
        url = f"{self.base_url}/r/{subreddit}/new.json"
        
        params = {
            "limit": limit,
            "t": "week" if days_back <= 7 else "month"
        }
        
        data = await self.fetch_json(url, params=params)
        
        if not data:
            logger.error(f"Failed to fetch r/{subreddit} data")
            return []
        
        posts = []
        
        try:
            for item in data.get("data", {}).get("children", []):
                post_data = item.get("data", {})
                
                # Filter by ticker if specified
                if ticker and ticker.lower() not in post_data.get("title", "").lower():
                    if ticker.lower() not in post_data.get("selftext", "").lower():
                        continue
                
                post = {
                    "source_platform": "reddit",
                    "source_url": f"{self.base_url}{post_data.get('permalink')}",
                    "author_handle": post_data.get("author"),
                    "post_title": post_data.get("title"),
                    "post_content": post_data.get("selftext"),
                    "post_date": datetime.fromtimestamp(post_data.get("created_utc", 0)).isoformat(),
                    "sentiment_score": self._analyze_sentiment(post_data.get("title", "") + " " + post_data.get("selftext", "")),
                    "confidence": 0.6,  # Lower confidence for general subreddit
                    "trader_followers_count": post_data.get("ups", 0),  # Upvotes as proxy for followers
                    "is_verified_trader": post_data.get("author_flair_text") is not None,
                    "scraped_at": datetime.now().isoformat()
                }
                
                # Filter by date
                post_date = datetime.fromisoformat(post["post_date"])
                if (datetime.now() - post_date).days > days_back:
                    continue
                
                posts.append(post)
            
            logger.info(f"Scraped {len(posts)} posts from r/{subreddit}")
            
        except Exception as e:
            logger.error(f"Error parsing Reddit posts: {e}")
        
        return posts
    
    def _analyze_sentiment(self, text: str) -> float:
        """Basic sentiment analysis"""
        if not text:
            return 0.0
        
        positive_keywords = ["buy", "good", "strong", "up", "bullish", "long", "moon", "rocket"]
        negative_keywords = ["sell", "bad", "weak", "down", "bearish", "short", "dump", "crash"]
        
        text_lower = text.lower()
        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total


class EtoroScraper(BaseScraper):
    """eToro scraper for popular trader profiles and positions"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        super().__init__(
            name="eToro",
            proxy_list=proxy_list,
            rate_limit_per_minute=30,
            rate_limit_per_hour=500
        )
        self.base_url = "https://www.etoro.com"
    
    async def scrape_popular_traders(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Scrape popular trader profiles from eToro
        
        Args:
            limit: Maximum number of traders to fetch
        
        Returns:
            List of trader profile records
        """
        logger.info(f"Scraping eToro popular traders (limit: {limit})")
        
        # eToro API endpoint (may require authentication)
        url = f"{self.base_url}/api/v1/copytrophies/leaders"
        
        params = {
            "limit": limit,
            "sort": "gain"
        }
        
        data = await self.fetch_json(url, params=params)
        
        if not data:
            logger.error("Failed to fetch eToro traders")
            return []
        
        traders = []
        
        try:
            for trader in data.get("leaders", [])[:limit]:
                trader_data = {
                    "source_platform": "etoro",
                    "author_handle": trader.get("username"),
                    "trader_success_rate": trader.get("gainPercent", 0) / 100,
                    "trader_followers_count": trader.get("copiers", 0),
                    "is_verified_trader": trader.get("isGold", False),
                    "trader_type": "popular_investor",
                    "scraped_at": datetime.now().isoformat()
                }
                traders.append(trader_data)
            
            logger.info(f"Scraped {len(traders)} traders from eToro")
            
        except Exception as e:
            logger.error(f"Error parsing eToro traders: {e}")
        
        return traders
    
    async def scrape_trader_positions(self, trader_username: str) -> List[Dict[str, Any]]:
        """
        Scrape positions for a specific trader
        
        Args:
            trader_username: eToro username
        
        Returns:
            List of position records
        """
        logger.info(f"Scraping eToro positions for {trader_username}")
        
        url = f"{self.base_url}/api/v1/users/{trader_username}/portfolio"
        
        data = await self.fetch_json(url)
        
        if not data:
            logger.error(f"Failed to fetch eToro positions for {trader_username}")
            return []
        
        positions = []
        
        try:
            for position in data.get("portfolio", {}).get("positions", []):
                pos_data = {
                    "source_platform": "etoro",
                    "author_handle": trader_username,
                    "ticker": position.get("instrumentID"),
                    "trade_direction": "long" if position.get("isBuy") else "short",
                    "entry_price": position.get("openRate"),
                    "target_price": position.get("takeProfitRate"),
                    "stop_loss": position.get("stopLossRate"),
                    "current_price": position.get("currentRate"),
                    "unrealized_pnl_percentage": position.get("unrealizedPLPercent"),
                    "scraped_at": datetime.now().isoformat()
                }
                positions.append(pos_data)
            
            logger.info(f"Scraped {len(positions)} positions for {trader_username}")
            
        except Exception as e:
            logger.error(f"Error parsing eToro positions: {e}")
        
        return positions


class TraderBlogScraper(BaseScraper):
    """Generic trader blog scraper (can be configured for specific blogs)"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        super().__init__(
            name="TraderBlog",
            proxy_list=proxy_list,
            rate_limit_per_minute=20,
            rate_limit_per_hour=400
        )
    
    async def scrape_blog_posts(
        self,
        blog_url: str,
        ticker: Optional[str] = None,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Scrape posts from a trader blog
        
        Args:
            blog_url: URL of the blog
            ticker: Optional ticker to filter
            days_back: Number of days to look back
        
        Returns:
            List of sentiment records
        """
        logger.info(f"Scraping blog posts from {blog_url}")
        
        html = await self.fetch_html(blog_url)
        
        if not html:
            logger.error(f"Failed to fetch blog from {blog_url}")
            return []
        
        soup = self.parse_html(html)
        posts = []
        
        try:
            # Generic blog post parsing
            for item in soup.find_all("article"):
                post = {
                    "source_platform": "trader_blog",
                    "source_url": blog_url + item.find("a")["href"] if item.find("a") else blog_url,
                    "author_handle": soup.find("meta", attrs={"name": "author"})["content"] if soup.find("meta", attrs={"name": "author"}) else None,
                    "post_title": item.find("h2").text.strip() if item.find("h2") else item.find("h1").text.strip() if item.find("h1") else None,
                    "post_content": item.find("div", class_="entry-content").text.strip() if item.find("div", class_="entry-content") else None,
                    "post_date": self._parse_date(item.find("time")["datetime"] if item.find("time") else None),
                    "sentiment_score": self._analyze_sentiment(item.get_text()),
                    "confidence": 0.8,  # Higher confidence for dedicated trader blogs
                    "scraped_at": datetime.now().isoformat()
                }
                
                # Filter by ticker if specified
                if ticker and post["post_title"]:
                    if ticker.lower() not in post["post_title"].lower():
                        continue
                
                # Filter by date
                if days_back and post["post_date"]:
                    post_date = datetime.fromisoformat(post["post_date"])
                    if (datetime.now() - post_date).days > days_back:
                        continue
                
                posts.append(post)
            
            logger.info(f"Scraped {len(posts)} posts from blog")
            
        except Exception as e:
            logger.error(f"Error parsing blog posts: {e}")
        
        return posts
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string to ISO format"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str).isoformat()
        except:
            return None
    
    def _analyze_sentiment(self, text: str) -> float:
        """Basic sentiment analysis"""
        if not text:
            return 0.0
        
        positive_keywords = ["buy", "good", "strong", "up", "bullish", "long", "recommend", "opportunity"]
        negative_keywords = ["sell", "bad", "weak", "down", "bearish", "short", "avoid", "risk"]
        
        text_lower = text.lower()
        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total


class SentimentScraperManager:
    """Manager for all sentiment scrapers"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        self.scrapers = {
            "Placera": PlaceraScraper(proxy_list),
            "Reddit": RedditScraper(proxy_list),
            "eToro": EtoroScraper(proxy_list),
            "TraderBlog": TraderBlogScraper(proxy_list)
        }
    
    async def scrape_all(
        self,
        tickers: Optional[List[str]] = None,
        days_back: int = 7,
        sources: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape sentiment data from all or specified sources
        
        Args:
            tickers: List of tickers to filter
            days_back: Number of days to look back
            sources: List of source names (None = all)
        
        Returns:
            Dictionary mapping source names to scraped data
        """
        sources = sources or list(self.scrapers.keys())
        results = {}
        
        for source_name in sources:
            if source_name in self.scrapers:
                scraper = self.scrapers[source_name]
                try:
                    if source_name == "Placera":
                        # Scrape for each ticker if specified
                        if tickers:
                            all_posts = []
                            for ticker in tickers:
                                posts = await scraper.scrape_forum_posts(ticker, days_back)
                                all_posts.extend(posts)
                            results[source_name] = all_posts
                        else:
                            results[source_name] = await scraper.scrape_forum_posts(days_back=days_back)
                    
                    elif source_name == "Reddit":
                        all_posts = []
                        # Scrape from multiple subreddits
                        subreddits = ["investing", "stocks", "wallstreetbets"]
                        for subreddit in subreddits:
                            if tickers:
                                for ticker in tickers:
                                    posts = await scraper.scrape_subreddit_posts(subreddit, ticker, days_back)
                                    all_posts.extend(posts)
                            else:
                                posts = await scraper.scrape_subreddit_posts(subreddit, days_back=days_back)
                                all_posts.extend(posts)
                        results[source_name] = all_posts
                    
                    elif source_name == "eToro":
                        # Scrape popular traders
                        traders = await scraper.scrape_popular_traders()
                        # For each trader, scrape positions
                        all_positions = []
                        for trader in traders[:10]:  # Limit to top 10 traders
                            positions = await scraper.scrape_trader_positions(trader["author_handle"])
                            all_positions.extend(positions)
                        results[source_name] = all_positions
                    
                    elif source_name == "TraderBlog":
                        # This would need a list of configured blog URLs
                        # For now, return empty
                        results[source_name] = []
                
                except Exception as e:
                    logger.error(f"Error scraping {source_name}: {e}")
                    results[source_name] = []
        
        return results
    
    def aggregate_sentiment(self, sentiment_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, float]:
        """
        Aggregate sentiment scores from all sources
        
        Args:
            sentiment_data: Dictionary of scraped sentiment data
        
        Returns:
            Dictionary mapping tickers to aggregated sentiment scores
        """
        ticker_scores = {}
        ticker_counts = {}
        
        for source, data in sentiment_data.items():
            for record in data:
                ticker = record.get("ticker") or record.get("post_title", "")
                score = record.get("sentiment_score", 0)
                confidence = record.get("confidence", 0.5)
                
                # Extract ticker from title if not directly provided
                if not ticker and record.get("post_title"):
                    ticker = self._extract_ticker_from_title(record["post_title"])
                
                if ticker:
                    weighted_score = score * confidence
                    if ticker not in ticker_scores:
                        ticker_scores[ticker] = 0
                        ticker_counts[ticker] = 0
                    ticker_scores[ticker] += weighted_score
                    ticker_counts[ticker] += confidence
        
        # Calculate weighted average
        aggregated = {}
        for ticker in ticker_scores:
            if ticker_counts[ticker] > 0:
                aggregated[ticker] = ticker_scores[ticker] / ticker_counts[ticker]
        
        return aggregated
    
    def _extract_ticker_from_title(self, title: str) -> Optional[str]:
        """Extract ticker symbol from title using regex"""
        # Simple pattern for common ticker formats
        patterns = [
            r'\b[A-Z]{2,5}\b',  # 2-5 uppercase letters
            r'\$[A-Z]{2,5}\b',  # $ followed by ticker
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, title)
            if matches:
                return matches[0].replace('$', '')
        
        return None
    
    def log_stats(self):
        """Log statistics from all scrapers"""
        for name, scraper in self.scrapers.items():
            logger.info(f"--- {name} Stats ---")
            scraper.log_stats()
