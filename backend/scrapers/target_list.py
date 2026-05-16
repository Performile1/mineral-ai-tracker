"""
Mineral AI Tracker - Target List (PRD v8.3)
Version: 8.3
Description: 3-tier configurable scrape target list.
"""

from typing import Dict, List

# 3-tier Target List per PRD v8.3:
#  1. Regulatory  - government and disclosure sources (highest signal)
#  2. News        - industry press
#  3. PR          - press release wires (lowest signal, used for fluff detection)
TARGET_LIST: Dict[str, List[Dict[str, str]]] = {
    "Regulatory": [
        {"name": "SGU", "url": "https://www.sgu.se/mineralnaring/"},
        {"name": "NGU", "url": "https://www.ngu.no/en/topic/mineral-resources"},
        {"name": "GTK", "url": "https://www.gtk.fi/en/news/"},
        {"name": "SEC EDGAR - Mining 8-K", "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=8-K&SIC=1040&dateb=&owner=include&count=40"},
        {"name": "Finansinspektionen Insynsregistret", "url": "https://marknadssok.fi.se/publiceringsklient"},
    ],
    "News": [
        {"name": "Mining.com", "url": "https://www.mining.com/"},
        {"name": "Northern Miner", "url": "https://www.northernminer.com/"},
        {"name": "Kitco News", "url": "https://www.kitco.com/news/"},
        {"name": "Mining Weekly", "url": "https://www.miningweekly.com/"},
    ],
    "PR": [
        {"name": "Cision Mining", "url": "https://news.cision.com/se/listing?n=10&q=gruva"},
        {"name": "PR Newswire Mining", "url": "https://www.prnewswire.com/news-releases/financial-business-latest-news/mining-list/"},
    ],
}


def iter_targets():
    """Yield (tier, name, url) for every target in the list."""
    for tier, items in TARGET_LIST.items():
        for item in items:
            yield tier, item["name"], item["url"]
