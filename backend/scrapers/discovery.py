"""
Mineral AI Tracker - Watchlist Discovery (PRD v8.6)
Version: 8.6
Description: Fast Yahoo Finance RSS lookup - finds the latest 3 news URLs
             for a given ticker. Feeds the Watchlist Stalker pipeline.
"""

from __future__ import annotations

import re
import asyncio
from html import unescape
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET

import httpx
from loguru import logger


YAHOO_RSS_TEMPLATE = "https://finance.yahoo.com/rss/headline?s={ticker}"
USER_AGENT = "Mozilla/5.0 (compatible; MineralAI/8.6; +https://mineral.ai)"
DEFAULT_LIMIT = 3
REQUEST_TIMEOUT = 12.0


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", unescape(text or "")).strip()


async def fetch_yahoo_rss(ticker: str, timeout: float = REQUEST_TIMEOUT) -> Optional[str]:
    """Fetch raw RSS XML for a ticker. Returns None on failure."""
    url = YAHOO_RSS_TEMPLATE.format(ticker=ticker.strip())
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.warning(f"Yahoo RSS fetch failed for {ticker}: {e}")
        return None


def _parse_rss_items(xml_text: str, limit: int) -> List[Dict[str, str]]:
    """Parse RSS XML and return up to `limit` items."""
    items: List[Dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning(f"RSS XML parse error: {e}")
        return items

    # Yahoo RSS is plain RSS 2.0 (no namespaces on item-level)
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        description = _strip_html(item.findtext("description") or "")
        if not link:
            continue
        items.append({
            "title": title,
            "url": link,
            "pub_date": pub_date,
            "summary": description[:400],
        })
        if len(items) >= limit:
            break
    return items


async def discover_news(ticker: str, limit: int = DEFAULT_LIMIT) -> List[Dict[str, str]]:
    """
    Returns up to `limit` recent news items for `ticker`:
        [{title, url, pub_date, summary}, ...]
    """
    ticker = (ticker or "").strip()
    if not ticker:
        return []

    xml_text = await fetch_yahoo_rss(ticker)
    if not xml_text:
        return []

    items = _parse_rss_items(xml_text, limit)
    logger.info(f"🔎 Discovery: {ticker} -> {len(items)} news items")
    return items


__all__ = ["discover_news", "fetch_yahoo_rss"]


if __name__ == "__main__":
    async def _demo():
        out = await discover_news("BOL.ST")
        for i, n in enumerate(out, 1):
            print(f"{i}. {n['title']}\n   {n['url']}\n")
    asyncio.run(_demo())
