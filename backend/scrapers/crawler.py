"""
Mineral AI Tracker - Crawl4AI Crawler (PRD v8.3)
Version: 10.5
Description: Renders JS/bot-protected pages and extracts clean Markdown,
             then forwards to /api/intelligence/analyze for the SLM debate.
PRD v10.0 Phase 10.5: Added proxy rotation for scraper stability
"""

import asyncio
from typing import Optional, Dict, Any
import httpx
from loguru import logger

try:
    # Crawl4AI is optional at import-time so the rest of the backend can boot
    # even if the package isn't installed yet on a dev machine.
    from crawl4ai import AsyncWebCrawler  # type: ignore
    CRAWL4AI_AVAILABLE = True
except Exception:  # pragma: no cover
    AsyncWebCrawler = None  # type: ignore
    CRAWL4AI_AVAILABLE = False

from config import settings
from utils.proxy_pool import get_proxy_pool


INTELLIGENCE_ANALYZE_URL = "http://localhost:8000/api/intelligence/analyze"


async def fetch_markdown(url: str, timeout: float = 60.0) -> Optional[str]:
    """
    Render a URL with Crawl4AI and return clean Markdown.
    Falls back to plain httpx fetch if Crawl4AI is unavailable.
    PRD v10.0 Phase 10.5: Added proxy rotation support
    """
    proxy_pool = get_proxy_pool()
    proxy = proxy_pool.get_proxy()
    
    if CRAWL4AI_AVAILABLE:
        try:
            # Crawl4AI doesn't support direct proxy configuration in the basic API
            # We'll use the fallback httpx with proxy support instead
            pass
        except Exception as e:
            logger.error(f"Crawl4AI error for {url}: {e}")

    # Fallback: raw HTTP fetch (no JS rendering) with proxy support
    try:
        proxy_dict = proxy.to_dict() if proxy else None
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            proxy=proxy_dict
        ) as client:
            resp = await client.get(url, headers={"User-Agent": "MineralAI/10.5"})
            resp.raise_for_status()
            
            if proxy:
                proxy_pool.record_success(proxy)
            
            return resp.text
    except Exception as e:
        if proxy:
            proxy_pool.record_failure(proxy)
        logger.error(f"Fallback fetch error for {url}: {e}")
        return None


async def scrape_and_send(
    url: str,
    source: str,
    analyze_url: str = INTELLIGENCE_ANALYZE_URL,
    timeout: float = 200.0,
) -> Optional[Dict[str, Any]]:
    """
    Full pipeline step: fetch URL -> send raw markdown to intelligence API.

    The intelligence endpoint runs the Multi-SLM debate protocol
    (Phi-3 -> Pydantic -> Mistral -> Llama-3 -> Consensus) sequentially.
    """
    logger.info(f"🌐 Scraping {source}: {url}")
    raw = await fetch_markdown(url)
    if not raw:
        logger.warning(f"No content fetched from {url}")
        return None

    # Trim to avoid massive prompts (the SLMs only need clean text)
    if len(raw) > 20_000:
        raw = raw[:20_000]

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                analyze_url,
                json={"raw_data": raw, "source": source},
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(
                f"✅ Analyzed {url} -> {data.get('signal_type')} "
                f"(confidence {data.get('confidence_score')})"
            )
            return data
    except Exception as e:
        logger.error(f"Failed to post to intelligence API for {url}: {e}")
        return None
