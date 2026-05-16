import asyncio
import json
from scrapers.crawler_engine import MineralCrawler
from utils.logger import setup_logger

logger = setup_logger("geo_events")

async def check_sgu_updates():
    """
    Hämtar senaste nyheter från SGU och sparar relevanta händelser till databasen.
    """
    crawler = MineralCrawler()
    
    # 1. Hämta strukturerad lista över nyheter
    news_items = await crawler.scrape_structured_data(
        url="https://www.sgu.se/om-sgu/nyheter/",
        schema=crawler.sgu_schema
    )
    
    # 2. Om vi hittar nyckelord (t.ex. "borrning", "litium"), mappa mot databasen
    if news_items:
        data = json.loads(news_items)
        for item in data:
            summary = item.get('summary', '').lower()
            title = item.get('title', '').lower()
            
            # Check for relevant keywords
            keywords = ['litium', 'kobolt', 'nickel', 'koppar', 'guld', 'uran', 'borrning', 'fyndighet']
            if any(keyword in summary or keyword in title for keyword in keywords):
                logger.info(f"🚨 Geologisk händelse hittad: {item['title']}")
                # TODO: Spara till Supabase table: geo_events
                # await save_to_supabase("geo_events", item)
    
    return news_items

async def check_ngu_updates():
    """
    Hämtar senaste nyheter från NGU (Norge).
    """
    crawler = MineralCrawler()
    
    ngu_schema = {
        "name": "NGU_Nyheter",
        "baseSelector": "article.news-item",
        "fields": [
            {"name": "title", "selector": "h2", "type": "text"},
            {"name": "date", "selector": "time", "type": "text"},
            {"name": "summary", "selector": "p", "type": "text"},
            {"name": "link", "selector": "a", "type": "attribute", "attribute": "href"}
        ]
    }
    
    news_items = await crawler.scrape_structured_data(
        url="https://www.ngu.no/no/nyheter",
        schema=ngu_schema
    )
    
    if news_items:
        data = json.loads(news_items)
        for item in data:
            logger.info(f"NGU händelse: {item['title']}")
            # TODO: Spara till Supabase
    
    return news_items

async def check_gtk_updates():
    """
    Hämtar senaste nyheter från GTK (Finland).
    """
    crawler = MineralCrawler()
    
    gtk_schema = {
        "name": "GTK_Nyheter",
        "baseSelector": "article",
        "fields": [
            {"name": "title", "selector": "h2", "type": "text"},
            {"name": "date", "selector": "time", "type": "text"},
            {"name": "summary", "selector": "p", "type": "text"},
            {"name": "link", "selector": "a", "type": "attribute", "attribute": "href"}
        ]
    }
    
    news_items = await crawler.scrape_structured_data(
        url="https://www.gtk.fi/en/news/",
        schema=gtk_schema
    )
    
    if news_items:
        data = json.loads(news_items)
        for item in data:
            logger.info(f"GTK händelse: {item['title']}")
            # TODO: Spara till Supabase
    
    return news_items

async def scrape_all_geo_sources():
    """
    Kör alla geologiska källor parallellt.
    """
    logger.info("Startar skrapning av alla geologiska källor...")
    
    results = await asyncio.gather(
        check_sgu_updates(),
        check_ngu_updates(),
        check_gtk_updates(),
        return_exceptions=True
    )
    
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Error skrapande: {result}")
    
    logger.info("Skrapning av geologiska källor klar.")
    return results

if __name__ == "__main__":
    asyncio.run(scrape_all_geo_sources())
