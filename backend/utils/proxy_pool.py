"""
Mineral AI Tracker - Proxy Pool Manager (PRD v10.0 Phase 10.5)
Version: 10.5
Description: Proxy rotation pool for scraper stability and IP protection
"""

import os
import random
import time
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from loguru import logger
import httpx


@dataclass
class ProxyConfig:
    """Proxy configuration"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"  # http, https, socks5
    
    def to_url(self) -> str:
        """Convert to proxy URL format"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to httpx proxy dict"""
        return {
            "http://": self.to_url(),
            "https://": self.to_url()
        }


@dataclass
class ProxyStats:
    """Proxy usage statistics"""
    success_count: int = 0
    failure_count: int = 0
    last_used: float = 0
    last_success: float = 0
    last_failure: float = 0
    consecutive_failures: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total
    
    @property
    def is_healthy(self) -> bool:
        """Check if proxy is healthy"""
        # Consider unhealthy if:
        # - More than 5 consecutive failures
        # - Success rate below 50% with at least 10 requests
        # - No successful requests in last hour
        if self.consecutive_failures >= 5:
            return False
        if (self.success_count + self.failure_count) >= 10 and self.success_rate < 0.5:
            return False
        if self.last_success > 0 and (time.time() - self.last_success) > 3600:
            return False
        return True


class ProxyPool:
    """
    Proxy pool manager for rotating through multiple proxies
    
    Features:
    - Round-robin rotation
    - Health checking
    - Automatic removal of dead proxies
    - Rate limiting per proxy
    - Fallback to direct connection
    """
    
    def __init__(self):
        self.proxies: List[ProxyConfig] = []
        self.stats: Dict[str, ProxyStats] = {}
        self.current_index = 0
        self.use_proxies = os.getenv("USE_PROXIES", "false").lower() == "true"
        self.max_retries = int(os.getenv("PROXY_MAX_RETRIES", "3"))
        self._load_proxies_from_env()
    
    def _load_proxies_from_env(self):
        """Load proxies from environment variable"""
        proxy_list = os.getenv("PROXY_LIST", "")
        if not proxy_list:
            logger.warning("No proxies configured in PROXY_LIST environment variable")
            return
        
        for proxy_str in proxy_list.split(","):
            proxy_str = proxy_str.strip()
            if not proxy_str:
                continue
            
            try:
                # Parse proxy string: http://user:pass@host:port or http://host:port
                if "@" in proxy_str:
                    auth_part, addr_part = proxy_str.split("@")
                    protocol_auth = auth_part.split("://")
                    protocol = protocol_auth[0] if len(protocol_auth) > 1 else "http"
                    user_pass = protocol_auth[1] if len(protocol_auth) > 1 else ""
                    if ":" in user_pass:
                        username, password = user_pass.split(":")
                    else:
                        username = user_pass
                        password = None
                    host, port = addr_part.split(":")
                else:
                    protocol_host = proxy_str.split("://")
                    protocol = protocol_host[0] if len(protocol_host) > 1 else "http"
                    addr_part = protocol_host[1] if len(protocol_host) > 1 else protocol_host[0]
                    if ":" in addr_part:
                        host, port = addr_part.split(":")
                    else:
                        host = addr_part
                        port = 8080
                    username = None
                    password = None
                
                proxy = ProxyConfig(
                    host=host,
                    port=int(port),
                    username=username,
                    password=password,
                    protocol=protocol
                )
                self.proxies.append(proxy)
                self.stats[proxy.to_url()] = ProxyStats()
                logger.info(f"Loaded proxy: {proxy.to_url()}")
            except Exception as e:
                logger.error(f"Failed to parse proxy '{proxy_str}': {e}")
        
        logger.info(f"Loaded {len(self.proxies)} proxies from environment")
    
    def get_proxy(self) -> Optional[ProxyConfig]:
        """Get next proxy from pool (round-robin)"""
        if not self.use_proxies or not self.proxies:
            return None
        
        # Filter healthy proxies
        healthy_proxies = [p for p in self.proxies if self.stats[p.to_url()].is_healthy]
        
        if not healthy_proxies:
            logger.warning("No healthy proxies available, falling back to direct connection")
            return None
        
        # Round-robin selection
        proxy = healthy_proxies[self.current_index % len(healthy_proxies)]
        self.current_index += 1
        
        logger.debug(f"Selected proxy: {proxy.to_url()}")
        return proxy
    
    def record_success(self, proxy: Optional[ProxyConfig]):
        """Record successful request through proxy"""
        if not proxy:
            return
        
        stats = self.stats[proxy.to_url()]
        stats.success_count += 1
        stats.last_used = time.time()
        stats.last_success = time.time()
        stats.consecutive_failures = 0
    
    def record_failure(self, proxy: Optional[ProxyConfig]):
        """Record failed request through proxy"""
        if not proxy:
            return
        
        stats = self.stats[proxy.to_url()]
        stats.failure_count += 1
        stats.last_used = time.time()
        stats.last_failure = time.time()
        stats.consecutive_failures += 1
        
        logger.warning(f"Proxy failure: {proxy.to_url()} (consecutive failures: {stats.consecutive_failures})")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy pool statistics"""
        return {
            "total_proxies": len(self.proxies),
            "healthy_proxies": sum(1 for p in self.proxies if self.stats[p.to_url()].is_healthy),
            "use_proxies": self.use_proxies,
            "proxy_stats": {
                proxy.to_url(): {
                    "success_count": stats.success_count,
                    "failure_count": stats.failure_count,
                    "success_rate": stats.success_rate,
                    "consecutive_failures": stats.consecutive_failures,
                    "is_healthy": stats.is_healthy
                }
                for proxy, stats in self.stats.items()
            }
        }
    
    async def health_check(self):
        """Health check all proxies"""
        if not self.proxies:
            return
        
        logger.info(f"Starting health check for {len(self.proxies)} proxies")
        
        async def check_proxy(proxy: ProxyConfig):
            try:
                async with httpx.AsyncClient(proxy=proxy.to_dict(), timeout=10.0) as client:
                    response = await client.get("http://httpbin.org/ip")
                    if response.status_code == 200:
                        self.record_success(proxy)
                        logger.debug(f"Proxy {proxy.to_url()} is healthy")
                    else:
                        self.record_failure(proxy)
            except Exception as e:
                self.record_failure(proxy)
                logger.debug(f"Proxy {proxy.to_url()} health check failed: {e}")
        
        # Check proxies in parallel
        tasks = [check_proxy(proxy) for proxy in self.proxies]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        stats = self.get_stats()
        logger.info(f"Health check complete: {stats['healthy_proxies']}/{stats['total_proxies']} proxies healthy")


# Global proxy pool instance
proxy_pool = ProxyPool()


def get_proxy_pool() -> ProxyPool:
    """Get global proxy pool instance"""
    return proxy_pool
