"""
Mineral AI Tracker - Base Scraper with Proxy Rotation & Rate Limiting
Version: 3.0
Description: Base scraper class with proxy rotation, rate limiting, and retry logic
"""

import asyncio
import random
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

import httpx
from httpx import AsyncClient, Response, HTTPError, TimeoutException


class ProxyRotator:
    """Manages proxy rotation for HTTP requests"""
    
    def __init__(self, proxy_list: List[str]):
        self.proxy_list = proxy_list
        self.current_index = 0
        self.failed_proxies: Dict[str, int] = {}
        self.max_failures = 5
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next available proxy, skipping failed ones"""
        if not self.proxy_list:
            return None
        
        # Try to find a working proxy
        attempts = 0
        max_attempts = len(self.proxy_list)
        
        while attempts < max_attempts:
            proxy = self.proxy_list[self.current_index]
            
            # Check if proxy has failed too many times
            if self.failed_proxies.get(proxy, 0) < self.max_failures:
                self.current_index = (self.current_index + 1) % len(self.proxy_list)
                return proxy
            
            # Move to next proxy
            self.current_index = (self.current_index + 1) % len(self.proxy_list)
            attempts += 1
        
        # All proxies failed, reset and try again
        logger.warning("All proxies failed, resetting failure counts")
        self.failed_proxies.clear()
        return self.proxy_list[0]
    
    def mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed"""
        if proxy:
            self.failed_proxies[proxy] = self.failed_proxies.get(proxy, 0) + 1
            logger.warning(f"Proxy failed: {proxy} (failures: {self.failed_proxies[proxy]})")
    
    def mark_proxy_success(self, proxy: str):
        """Mark a proxy as successful, reset failure count"""
        if proxy and proxy in self.failed_proxies:
            del self.failed_proxies[proxy]


class RateLimiter:
    """Implements rate limiting for API requests"""
    
    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_requests: List[float] = []
        self.hour_requests: List[float] = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait until rate limit allows request"""
        async with self.lock:
            now = time.time()
            
            # Clean old requests
            self.minute_requests = [t for t in self.minute_requests if now - t < 60]
            self.hour_requests = [t for t in self.hour_requests if now - t < 3600]
            
            # Check minute limit
            if len(self.minute_requests) >= self.requests_per_minute:
                sleep_time = 60 - (now - self.minute_requests[0])
                if sleep_time > 0:
                    logger.info(f"Rate limit reached (minute), sleeping {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
            
            # Check hour limit
            if len(self.hour_requests) >= self.requests_per_hour:
                sleep_time = 3600 - (now - self.hour_requests[0])
                if sleep_time > 0:
                    logger.warning(f"Rate limit reached (hour), sleeping {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
            
            # Record request
            self.minute_requests.append(now)
            self.hour_requests.append(now)


class BaseScraper:
    """Base scraper class with proxy rotation, rate limiting, and retry logic"""
    
    def __init__(
        self,
        name: str,
        proxy_list: Optional[List[str]] = None,
        rate_limit_per_minute: int = 60,
        rate_limit_per_hour: int = 1000,
        max_retries: int = 3,
        timeout: int = 30,
        user_agent: Optional[str] = None
    ):
        self.name = name
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Initialize proxy rotator
        proxy_list = proxy_list or []
        self.proxy_rotator = ProxyRotator(proxy_list) if proxy_list else None
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(rate_limit_per_minute, rate_limit_per_hour)
        
        # User agent rotation
        self.user_agents = [
            user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        
        logger.info(f"Initialized {name} scraper with proxy rotation: {len(proxy_list)} proxies")
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        return random.choice(self.user_agents)
    
    async def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        use_proxy: bool = True
    ) -> Optional[Response]:
        """
        Fetch URL with proxy rotation, rate limiting, and retry logic
        
        Args:
            url: URL to fetch
            method: HTTP method (GET, POST, etc.)
            headers: Request headers
            params: Query parameters
            data: Form data
            json_data: JSON data
            use_proxy: Whether to use proxy rotation
        
        Returns:
            Response object or None if all retries failed
        """
        # Rate limit
        await self.rate_limiter.acquire()
        
        # Prepare headers
        headers = headers or {}
        headers["User-Agent"] = self.get_random_user_agent()
        
        # Retry logic
        for attempt in range(self.max_retries):
            proxy = None
            if use_proxy and self.proxy_rotator:
                proxy = self.proxy_rotator.get_next_proxy()
            
            try:
                async with AsyncClient(timeout=self.timeout) as client:
                    # Build proxy dict if using proxy
                    proxies = None
                    if proxy:
                        proxies = {"http://": proxy, "https://": proxy}
                    
                    logger.debug(f"Attempt {attempt + 1}/{self.max_retries}: {method} {url}")
                    if proxy:
                        logger.debug(f"Using proxy: {proxy}")
                    
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        data=data,
                        json=json_data,
                        proxies=proxies,
                        follow_redirects=True
                    )
                    
                    response.raise_for_status()
                    
                    # Mark proxy as successful
                    if proxy and self.proxy_rotator:
                        self.proxy_rotator.mark_proxy_success(proxy)
                    
                    logger.info(f"Success: {method} {url} - Status: {response.status_code}")
                    return response
                    
            except HTTPError as e:
                logger.warning(f"HTTP Error on attempt {attempt + 1}: {e}")
                if proxy and self.proxy_rotator:
                    self.proxy_rotator.mark_proxy_failed(proxy)
                
                # Exponential backoff
                wait_time = min(2 ** attempt, 10) + random.uniform(0, 1)
                logger.info(f"Retrying in {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)
                
            except TimeoutException as e:
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                if proxy and self.proxy_rotator:
                    self.proxy_rotator.mark_proxy_failed(proxy)
                
                wait_time = min(2 ** attempt, 10) + random.uniform(0, 1)
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if proxy and self.proxy_rotator:
                    self.proxy_rotator.mark_proxy_failed(proxy)
                
                wait_time = min(2 ** attempt, 10) + random.uniform(0, 1)
                await asyncio.sleep(wait_time)
        
        logger.error(f"All {self.max_retries} attempts failed for: {url}")
        return None
    
    async def fetch_json(
        self,
        url: str,
        method: str = "GET",
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Fetch URL and parse JSON response"""
        response = await self.fetch(url, method=method, **kwargs)
        if response:
            try:
                return response.json()
            except Exception as e:
                logger.error(f"Failed to parse JSON: {e}")
                return None
        return None
    
    async def fetch_html(
        self,
        url: str,
        method: str = "GET",
        **kwargs
    ) -> Optional[str]:
        """Fetch URL and return HTML text"""
        response = await self.fetch(url, method=method, **kwargs)
        if response:
            return response.text
        return None
    
    def parse_html(self, html: str):
        """Parse HTML using BeautifulSoup"""
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "lxml")
    
    async def scrape(self) -> Dict[str, Any]:
        """Main scraping method - to be overridden by subclasses"""
        raise NotImplementedError("Subclasses must implement scrape() method")
    
    def log_stats(self):
        """Log scraping statistics"""
        if self.proxy_rotator:
            logger.info(f"Proxy stats: {len(self.proxy_rotator.failed_proxies)} failed proxies")
        
        if self.rate_limiter:
            logger.info(f"Rate limiter: {len(self.rate_limiter.minute_requests)} requests in last minute")
