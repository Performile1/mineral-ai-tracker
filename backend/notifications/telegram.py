"""
Mineral AI Tracker - Telegram Notifications (PRD v9.0 Phase 1)
Version: 9.0
Description: Telegram bot integration for sending rich alert messages
"""

from typing import Optional
from loguru import logger
import httpx

TELEGRAM_API_BASE = "https://api.telegram.org"
TIMEOUT = 10.0


async def send_telegram_message(
    chat_id: str,
    message: str,
    parse_mode: str = "Markdown",
    reply_markup: Optional[dict] = None
) -> bool:
    """
    Send message via Telegram Bot API
    
    Args:
        chat_id: Telegram chat ID
        message: Message text (supports Markdown)
        parse_mode: Parse mode (Markdown or HTML)
        reply_markup: Inline keyboard markup for action buttons
    
    Returns:
        True if successful, False otherwise
    """
    bot_token = _get_bot_token()
    if not bot_token:
        logger.error("Telegram bot token not configured")
        return False
    
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                logger.info(f"Telegram message sent to chat {chat_id}")
                return True
            else:
                logger.error(f"Telegram API error: {data.get('description')}")
                return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


async def send_telegram_alert(
    chat_id: str,
    ticker: str,
    signal: str,
    confidence: int,
    reasoning: str,
    dashboard_url: str
) -> bool:
    """
    Send formatted alert message with action buttons
    
    Args:
        chat_id: Telegram chat ID
        ticker: Stock ticker
        signal: Signal type (BUY, SELL, PASS)
        confidence: Confidence score (0-100)
        reasoning: AI reasoning summary
        dashboard_url: URL to dashboard for the asset
    
    Returns:
        True if successful, False otherwise
    """
    # Format message with Markdown
    message = f"""
🤖 *Mineral AI Alert*

*Ticker:* `{ticker}`
*Signal:* {'✅' if signal == 'BUY' else '❌' if signal == 'SELL' else '⏸️'} {signal}
*Confidence:* {confidence}%

*AI Reasoning:*
_{reasoning[:300]}..._

[View Asset]({dashboard_url})
[Execute Trade]({dashboard_url}?action=execute)
    """
    
    # Create inline keyboard with action buttons
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "📊 View Asset", "url": dashboard_url},
                {"text": "⚡ Execute Trade", "url": f"{dashboard_url}?action=execute"}
            ]
        ]
    }
    
    return await send_telegram_message(
        chat_id=chat_id,
        message=message.strip(),
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


def _get_bot_token() -> Optional[str]:
    """
    Get Telegram bot token from environment variables
    
    Returns:
        Bot token or None if not configured
    """
    import os
    return os.environ.get("TELEGRAM_BOT_TOKEN")


def validate_chat_id(chat_id: str) -> bool:
    """
    Validate Telegram chat ID format
    
    Args:
        chat_id: Chat ID to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        # Chat ID should be numeric (can be negative for groups)
        int(chat_id)
        return True
    except (ValueError, TypeError):
        return False


__all__ = [
    "send_telegram_message",
    "send_telegram_alert",
    "validate_chat_id",
]
