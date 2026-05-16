"""
Mineral AI Tracker - Source Authority Matrix (Phase 12.1)
Description: Evaluate news source authority for financial events
"""

from typing import Optional
from loguru import logger


def get_authority_score(source_type: str, source_name: Optional[str] = None) -> float:
    """
    Calculate authority score for a news source based on type and name.
    
    Authority Matrix:
    - Category A (1.0): Financial Reports, Annual Reports, SEC Filings
    - Category B (0.8): Official Press Releases (PR)
    - Category C (0.4): News Articles, Analyst Releases
    
    Args:
        source_type: Type of source (e.g., 'financial_report', 'press_release', 'news_article')
        source_name: Optional source name for additional context
        
    Returns:
        Authority score between 0.1 and 1.0
    """
    if not source_type:
        logger.warning(f"No source_type provided, defaulting to 0.4")
        return 0.4
    
    # Normalize source type for comparison
    source_type_lower = source_type.lower()
    
    # Category A: Financial Reports, SEC Filings (100% Authority)
    if any(keyword in source_type_lower for keyword in [
        'financial_report', 'annual_report', 'quarterly_report', 'sec_filing',
        '10-k', '10-q', '20-f', '8-k', 'earnings_release', 'q3', 'q4'
    ]):
        return 1.0
    
    # Check source name for Category A indicators
    if source_name:
        source_name_lower = source_name.lower()
        if any(keyword in source_name_lower for keyword in [
            'sec.gov', 'investor', 'ir.', 'annualreport', 'quarterly',
            'earnings', 'filing'
        ]):
            return 1.0
    
    # Category B: Official Press Releases (80% Authority)
    if any(keyword in source_type_lower for keyword in [
        'press_release', 'pr', 'official_statement', 'company_announcement'
    ]):
        return 0.8
    
    # Check source name for Category B indicators
    if source_name:
        source_name_lower = source_name.lower()
        if any(keyword in source_name_lower for keyword in [
            'prnewswire', 'globenewswire', 'businesswire', 'press.',
            'newsroom'
        ]):
            return 0.8
    
    # Category C: News Articles, Analyst Releases (40% Authority)
    if any(keyword in source_type_lower for keyword in [
        'news_article', 'analyst_report', 'blog_post', 'opinion',
        'market_commentary'
    ]):
        return 0.4
    
    # Default to lowest authority for unknown sources
    logger.warning(f"Unknown source_type '{source_type}', defaulting to 0.4")
    return 0.4


def get_authority_category(score: float) -> str:
    """
    Get the authority category label for a given score.
    
    Args:
        score: Authority score between 0.1 and 1.0
        
    Returns:
        Category label string
    """
    if score >= 1.0:
        return "A (Financial Reports)"
    elif score >= 0.8:
        return "B (Press Releases)"
    else:
        return "C (News Articles)"
