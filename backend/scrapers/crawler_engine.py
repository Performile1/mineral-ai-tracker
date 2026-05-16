import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from utils.logger import setup_logger

logger = setup_logger("crawl4ai_engine")

class MineralCrawler:
    def __init__(self):
        # Configure strategies for specific pages
        self.sgu_schema = {
            "name": "SGU_Nyheter",
            "baseSelector": "article.news-item",
            "fields": [
                {"name": "title", "selector": "h2", "type": "text"},
                {"name": "date", "selector": "time", "type": "text"},
                {"name": "summary", "selector": "p.summary", "type": "text"},
                {"name": "link", "selector": "a", "type": "attribute", "attribute": "href"}
            ]
        }

    async def scrape_structured_data(self, url: str, schema: dict):
        """
        Skrapar en sida och tvingar datan in i ett strikt JSON-format via CSS-selektorer.
        Perfekt för listor med pressmeddelanden eller börsintroduktioner (IPO).
        """
        logger.info(f"Crawl4AI startar extraktion från: {url}")
        
        strategy = JsonCssExtractionStrategy(schema, verbose=True)
        
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(
                url=url,
                extraction_strategy=strategy,
                bypass_cache=True,
                magic=True # Hanterar JS-rendering, anti-bot och iframes automatiskt
            )
            
            if result.success:
                logger.info("Skrapning lyckades.")
                return result.extracted_content # Returnerar strukturerad JSON
            else:
                logger.error(f"Skrapning misslyckades: {result.error_message}")
                return None

    async def scrape_clean_markdown(self, url: str):
        """
        Skrapar en artikel eller PDF-sida och rensar bort all HTML.
        Returnerar ren Markdown som är perfekt för vår makro-logik att läsa av.
        """
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(
                url=url,
                word_count_threshold=50, # Ignorera navigeringslänkar och footers
                magic=True
            )
            
            if result.success:
                return result.markdown
            return None
