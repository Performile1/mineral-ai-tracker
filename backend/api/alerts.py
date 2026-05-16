"""
Mineral AI Tracker - Alerts API (PRD v9.0 Phase 1)
Version: 9.0
Description: Alert configuration and notification management for The Sentinel
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from loguru import logger

import psycopg2
from psycopg2.extras import RealDictCursor

from api.deps import get_current_user


router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ============================================================================
# Pydantic Models
# ============================================================================

class AlertConfig(BaseModel):
    """Alert configuration model"""
    confidence_threshold: int = Field(90, ge=0, le=100, description="Minimum confidence to trigger alert")
    price_drift_threshold: float = Field(8.0, ge=0, le=100, description="Price drift percentage to trigger alert")
    alert_on_buy: bool = Field(True, description="Alert on BUY signals")
    alert_on_sell: bool = Field(True, description="Alert on SELL signals")
    alert_on_pass: bool = Field(False, description="Alert on PASS signals")
    telegram_enabled: bool = Field(False, description="Enable Telegram notifications")
    telegram_chat_id: Optional[str] = Field(None, description="Telegram chat ID")
    discord_enabled: bool = Field(False, description="Enable Discord notifications")
    discord_webhook_url: Optional[str] = Field(None, description="Discord webhook URL")
    email_enabled: bool = Field(False, description="Enable email notifications")
    email_address: Optional[str] = Field(None, description="Email address for notifications")


class AlertConfigResponse(AlertConfig):
    """Alert configuration response with metadata"""
    id: str
    user_id: str
    created_at: str
    updated_at: str


class TestAlertRequest(BaseModel):
    """Request to send a test alert"""
    channel: str = Field(..., description="Channel to send test alert to (telegram, discord, email)")


class AlertHistoryItem(BaseModel):
    """Alert history item"""
    id: str
    signal_id: str
    channel: str
    sent_at: str
    status: str
    error_message: Optional[str] = None


# ============================================================================
# Database Helpers
# ============================================================================

def get_db_connection():
    """Get database connection"""
    import os
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "mineral_ai_tracker"),
        user=os.getenv("POSTGRES_USER", "mineral_user"),
        password=os.getenv("POSTGRES_PASSWORD", "mineralpass123"),
        cursor_factory=RealDictCursor
    )


def ensure_alert_tables():
    """Ensure alert tables exist"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS alert_configs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255),
                    confidence_threshold INTEGER DEFAULT 90,
                    price_drift_threshold DECIMAL(5,2) DEFAULT 8.0,
                    alert_on_buy BOOLEAN DEFAULT true,
                    alert_on_sell BOOLEAN DEFAULT true,
                    alert_on_pass BOOLEAN DEFAULT false,
                    telegram_enabled BOOLEAN DEFAULT false,
                    telegram_chat_id VARCHAR(255),
                    discord_enabled BOOLEAN DEFAULT false,
                    discord_webhook_url TEXT,
                    email_enabled BOOLEAN DEFAULT false,
                    email_address VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS alert_history (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    signal_id UUID REFERENCES investment_signals(id),
                    config_id UUID REFERENCES alert_configs(id),
                    channel VARCHAR(50),
                    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    status VARCHAR(20),
                    error_message TEXT
                );
            """)
            conn.commit()
    finally:
        conn.close()


# ============================================================================
# Alert Manager
# ============================================================================

class AlertManager:
    """Manages alert monitoring and notification sending"""
    
    def __init__(self):
        self.config_cache: Dict[str, AlertConfig] = {}
        self.load_configs()
    
    def load_configs(self):
        """Load alert configurations from database"""
        try:
            ensure_alert_tables()
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM alert_configs")
                    rows = cur.fetchall()
                    for row in rows:
                        self.config_cache[str(row['id'])] = AlertConfig(**dict(row))
            finally:
                conn.close()
            logger.info(f"Loaded {len(self.config_cache)} alert configurations")
        except Exception as e:
            logger.error(f"Failed to load alert configs: {e}")
    
    def should_alert(self, signal: Dict[str, Any], config: AlertConfig) -> bool:
        """
        Check if signal should trigger alert based on configuration
        
        Args:
            signal: Signal data from investment_signals
            config: Alert configuration
        
        Returns:
            True if alert should be sent
        """
        # Check confidence threshold
        confidence = signal.get('confidence_score', 0)
        if confidence < config.confidence_threshold:
            return False
        
        # Check signal type
        recommendation = signal.get('recommendation', '').upper()
        if recommendation == 'BUY' and not config.alert_on_buy:
            return False
        elif recommendation == 'SELL' and not config.alert_on_sell:
            return False
        elif recommendation == 'PASS' and not config.alert_on_pass:
            return False
        
        return True
    
    async def send_alert(self, signal: Dict[str, Any], config: AlertConfig):
        """
        Send alert via configured channels
        
        Args:
            signal: Signal data
            config: Alert configuration
        """
        sent_channels = []
        
        if config.telegram_enabled and config.telegram_chat_id:
            try:
                from notifications.telegram import send_telegram_message
                message = self._format_alert_message(signal, "telegram")
                await send_telegram_message(config.telegram_chat_id, message)
                sent_channels.append("telegram")
                logger.info(f"Telegram alert sent for signal {signal.get('id')}")
            except Exception as e:
                logger.error(f"Failed to send Telegram alert: {e}")
        
        if config.discord_enabled and config.discord_webhook_url:
            try:
                from notifications.discord import send_discord_webhook
                embed = self._format_alert_message(signal, "discord")
                await send_discord_webhook(config.discord_webhook_url, embed)
                sent_channels.append("discord")
                logger.info(f"Discord alert sent for signal {signal.get('id')}")
            except Exception as e:
                logger.error(f"Failed to send Discord alert: {e}")
        
        # Log alert history
        self._log_alert_history(signal.get('id'), sent_channels)
    
    def _format_alert_message(self, signal: Dict[str, Any], channel: str) -> str:
        """Format alert message for specific channel"""
        ticker = signal.get('asset_id', 'UNKNOWN')
        recommendation = signal.get('recommendation', 'PASS')
        confidence = signal.get('confidence_score', 0)
        
        # Extract reasoning from debate log
        debate_log = signal.get('debate_log', {})
        if isinstance(debate_log, dict):
            # Get Llama-3 reasoning
            llama3_reasoning = debate_log.get('llama3_reasoning', 'No reasoning available')
        else:
            llama3_reasoning = 'No reasoning available'
        
        if channel == "telegram":
            return f"""
🤖 *Mineral AI Alert*

*Ticker:* {ticker}
*Signal:* {recommendation}
*Confidence:* {confidence}%

*AI Reasoning:*
{llama3_reasoning[:500]}...

[View Asset](http://localhost:3000/assets/{ticker})
[Execute Trade](http://localhost:3000/dashboard?ticker={ticker})
"""
        elif channel == "discord":
            return f"""
Mineral AI Alert
Ticker: {ticker}
Signal: {recommendation}
Confidence: {confidence}%

AI Reasoning: {llama3_reasoning[:500]}...
"""
        return f"Alert: {ticker} - {recommendation} ({confidence}%)"
    
    def _log_alert_history(self, signal_id: str, channels: List[str]):
        """Log alert history to database"""
        try:
            ensure_alert_tables()
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    for channel in channels:
                        cur.execute("""
                            INSERT INTO alert_history (signal_id, channel, status)
                            VALUES (%s, %s, %s)
                        """, (signal_id, channel, "sent"))
                    conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Failed to log alert history: {e}")


# Singleton instance
alert_manager = AlertManager()


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/config", response_model=List[AlertConfigResponse])
async def get_alert_configs(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """Get all alert configurations for current user"""
    try:
        user_id = current_user["id"]  # Critical Hotfix: Extract user_id from auth context
        ensure_alert_tables()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Critical Hotfix: Add user_id filtering for application-level data isolation
                cur.execute("SELECT * FROM alert_configs WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
                rows = cur.fetchall()
                return [AlertConfigResponse(**dict(r)) for r in rows]
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to get alert configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config", response_model=AlertConfigResponse)
async def create_alert_config(
    config: AlertConfig,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """Create new alert configuration"""
    try:
        user_id = current_user["id"]  # Critical Hotfix: Extract user_id from auth context
        ensure_alert_tables()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Critical Hotfix: Use authenticated user_id instead of 'default'
                cur.execute("""
                    INSERT INTO alert_configs (
                        user_id, confidence_threshold, price_drift_threshold,
                        alert_on_buy, alert_on_sell, alert_on_pass,
                        telegram_enabled, telegram_chat_id,
                        discord_enabled, discord_webhook_url,
                        email_enabled, email_address
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id, created_at, updated_at
                """, (
                    user_id,
                    config.confidence_threshold,
                    config.price_drift_threshold,
                    config.alert_on_buy,
                    config.alert_on_sell,
                    config.alert_on_pass,
                    config.telegram_enabled,
                    config.telegram_chat_id,
                    config.discord_enabled,
                    config.discord_webhook_url,
                    config.email_enabled,
                    config.email_address
                ))
                row = cur.fetchone()
                conn.commit()
                
                # Refresh cache
                alert_manager.load_configs()
                
                return AlertConfigResponse(
                    id=str(row['id']),
                    user_id=user_id,
                    **config.dict(),
                    created_at=row['created_at'].isoformat(),
                    updated_at=row['updated_at'].isoformat()
                )
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to create alert config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/{config_id}", response_model=AlertConfigResponse)
async def update_alert_config(
    config_id: str,
    config: AlertConfig,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """Update existing alert configuration"""
    try:
        user_id = current_user["id"]  # Critical Hotfix: Extract user_id from auth context
        ensure_alert_tables()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Critical Hotfix: Add user_id check to prevent cross-user updates
                cur.execute("""
                    UPDATE alert_configs SET
                        confidence_threshold = %s,
                        price_drift_threshold = %s,
                        alert_on_buy = %s,
                        alert_on_sell = %s,
                        alert_on_pass = %s,
                        telegram_enabled = %s,
                        telegram_chat_id = %s,
                        discord_enabled = %s,
                        discord_webhook_url = %s,
                        email_enabled = %s,
                        email_address = %s,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s
                    RETURNING id, user_id, created_at, updated_at
                """, (
                    config.confidence_threshold,
                    config.price_drift_threshold,
                    config.alert_on_buy,
                    config.alert_on_sell,
                    config.alert_on_pass,
                    config.telegram_enabled,
                    config.telegram_chat_id,
                    config.discord_enabled,
                    config.discord_webhook_url,
                    config.email_enabled,
                    config.email_address,
                    config_id,
                    user_id
                ))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Alert config not found")
                conn.commit()
                
                # Refresh cache
                alert_manager.load_configs()
                
                return AlertConfigResponse(
                    id=str(row['id']),
                    user_id=row['user_id'],
                    **config.dict(),
                    created_at=row['created_at'].isoformat(),
                    updated_at=row['updated_at'].isoformat()
                )
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update alert config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def send_test_alert(
    request: TestAlertRequest,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """Send a test alert to verify configuration"""
    try:
        user_id = current_user["id"]  # Critical Hotfix: Extract user_id from auth context
        # Create a test signal
        test_signal = {
            'id': 'test_signal_id',
            'asset_id': 'TEST',
            'recommendation': 'BUY',
            'confidence_score': 95,
            'debate_log': {
                'llama3_reasoning': 'This is a test alert to verify your notification configuration is working correctly.'
            }
        }
        
        # Get default config
        ensure_alert_tables()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Critical Hotfix: Use authenticated user_id instead of 'default'
                cur.execute("SELECT * FROM alert_configs WHERE user_id = %s LIMIT 1", (user_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="No alert configuration found. Please create one first.")
                config = AlertConfig(**dict(row))
        finally:
            conn.close()
        
        # Send test alert
        await alert_manager.send_alert(test_signal, config)
        
        return {"status": "success", "message": f"Test alert sent to {request.channel}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send test alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[AlertHistoryItem])
async def get_alert_history(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """Get alert history"""
    try:
        ensure_alert_tables()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, signal_id, channel, sent_at, status, error_message
                    FROM alert_history
                    ORDER BY sent_at DESC LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
                return [
                    AlertHistoryItem(
                        id=str(r['id']),
                        signal_id=str(r['signal_id']),
                        channel=r['channel'],
                        sent_at=r['sent_at'].isoformat(),
                        status=r['status'],
                        error_message=r['error_message']
                    )
                    for r in rows
                ]
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to get alert history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router", "alert_manager"]
