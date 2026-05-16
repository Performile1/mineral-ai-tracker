"""
Mineral AI Tracker - Discord Notifications (PRD v9.0 Phase 1)
Version: 9.0
Description: Discord webhook integration for sending rich alert messages
"""

from typing import Optional, Dict, Any
from loguru import logger
import httpx

TIMEOUT = 10.0


async def send_discord_webhook(
    webhook_url: str,
    embed: Dict[str, Any],
    username: Optional[str] = None,
    avatar_url: Optional[str] = None
) -> bool:
    """
    Send message via Discord webhook
    
    Args:
        webhook_url: Discord webhook URL
        embed: Discord embed object
        username: Override bot username
        avatar_url: Override bot avatar
    
    Returns:
        True if successful, False otherwise
    """
    if not webhook_url:
        logger.error("Discord webhook URL not configured")
        return False
    
    payload = {
        "embeds": [embed]
    }
    
    if username:
        payload["username"] = username
    
    if avatar_url:
        payload["avatar_url"] = avatar_url
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info("Discord webhook message sent successfully")
            return True
    except Exception as e:
        logger.error(f"Failed to send Discord webhook: {e}")
        return False


async def send_discord_alert(
    webhook_url: str,
    ticker: str,
    signal: str,
    confidence: int,
    reasoning: str,
    dashboard_url: str
) -> bool:
    """
    Send formatted alert message with embed and action buttons
    
    Args:
        webhook_url: Discord webhook URL
        ticker: Stock ticker
        signal: Signal type (BUY, SELL, PASS)
        confidence: Confidence score (0-100)
        reasoning: AI reasoning summary
        dashboard_url: URL to dashboard for the asset
    
    Returns:
        True if successful, False otherwise
    """
    # Determine color based on signal
    if signal == "BUY":
        color = 5763719  # Green
        emoji = "📈"
    elif signal == "SELL":
        color = 15548997  # Red
        emoji = "📉"
    else:
        color = 9807270  # Gray
        emoji = "⏸️"
    
    # Create Discord embed
    embed = {
        "title": f"{emoji} Mineral AI Alert",
        "color": color,
        "fields": [
            {
                "name": "Ticker",
                "value": f"`{ticker}`",
                "inline": True
            },
            {
                "name": "Signal",
                "value": signal,
                "inline": True
            },
            {
                "name": "Confidence",
                "value": f"{confidence}%",
                "inline": True
            },
            {
                "name": "AI Reasoning",
                "value": reasoning[:500] + "..." if len(reasoning) > 500 else reasoning,
                "inline": False
            }
        ],
        "timestamp": None,  # Discord will set current time
        "footer": {
            "text": "Mineral AI Tracker v9.0"
        }
    }
    
    # Add action buttons via components
    # Note: Discord webhooks don't support interactive buttons directly,
    # so we include links in the description instead
    embed["description"] = f"[📊 View Asset]({dashboard_url}) | [⚡ Execute Trade]({dashboard_url}?action=execute)"
    
    return await send_discord_webhook(
        webhook_url=webhook_url,
        embed=embed,
        username="Mineral AI Sentinel"
    )


def validate_webhook_url(webhook_url: str) -> bool:
    """
    Validate Discord webhook URL format
    
    Args:
        webhook_url: Webhook URL to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not webhook_url:
        return False
    
    # Discord webhook URLs follow the pattern:
    # https://discord.com/api/webhooks/{id}/{token}
    return webhook_url.startswith("https://discord.com/api/webhooks/") or \
           webhook_url.startswith("https://discordapp.com/api/webhooks/")


__all__ = [
    "send_discord_webhook",
    "send_discord_alert",
    "validate_webhook_url",
]
