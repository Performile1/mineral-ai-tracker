"""
Mineral AI Tracker - Twilio SMS Notifications
Version: 3.0
Description: Twilio integration for critical SMS alerts (stop-loss, black swan events)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio library not installed. SMS notifications will be disabled.")


class TwilioNotificationService:
    """
    Twilio SMS Notification Service
    
    Sends critical alerts via SMS for:
    - Stop-loss triggers
    - Black swan geopolitical events
    - Target price hits (optional)
    """
    
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
        enabled: bool = True
    ):
        """
        Initialize Twilio notification service
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Twilio phone number to send from
            enabled: Whether SMS notifications are enabled
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.enabled = enabled and TWILIO_AVAILABLE
        
        if self.enabled and all([account_sid, auth_token, from_number]):
            try:
                self.client = Client(account_sid, auth_token)
                logger.info("Twilio notification service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self.enabled = False
        else:
            self.client = None
            if not TWILIO_AVAILABLE:
                logger.warning("Twilio library not available")
            elif not all([account_sid, auth_token, from_number]):
                logger.warning("Twilio credentials not provided")
    
    def send_stop_loss_alert(
        self,
        to_number: str,
        ticker: str,
        current_price: float,
        stop_loss: float,
        position_value: float
    ) -> bool:
        """
        Send stop-loss alert SMS
        
        Args:
            to_number: Recipient phone number
            ticker: Asset ticker
            current_price: Current price
            stop_loss: Stop-loss price
            position_value: Value of position
        
        Returns:
            True if sent successfully, False otherwise
        """
        message = (
            f"⚠️ STOP-LOSS TRIGGERED\n\n"
            f"Asset: {ticker}\n"
            f"Current Price: {current_price:.2f} SEK\n"
            f"Stop-Loss: {stop_loss:.2f} SEK\n"
            f"Position Value: {position_value:.2f} SEK\n\n"
            f"Please review your position immediately.\n\n"
            f"- Mineral AI Tracker"
        )
        
        return self._send_sms(to_number, message, alert_type="stop_loss")
    
    def send_target_price_alert(
        self,
        to_number: str,
        ticker: str,
        current_price: float,
        target_price: float,
        position_value: float
    ) -> bool:
        """
        Send target price hit alert SMS
        
        Args:
            to_number: Recipient phone number
            ticker: Asset ticker
            current_price: Current price
            target_price: Target price
            position_value: Value of position
        
        Returns:
            True if sent successfully, False otherwise
        """
        message = (
            f"🎯 TARGET PRICE HIT\n\n"
            f"Asset: {ticker}\n"
            f"Current Price: {current_price:.2f} SEK\n"
            f"Target: {target_price:.2f} SEK\n"
            f"Position Value: {position_value:.2f} SEK\n\n"
            f"Consider taking profits.\n\n"
            f"- Mineral AI Tracker"
        )
        
        return self._send_sms(to_number, message, alert_type="target_price")
    
    def send_black_swan_alert(
        self,
        to_number: str,
        event_type: str,
        description: str,
        affected_assets: List[str]
    ) -> bool:
        """
        Send black swan event alert SMS
        
        Args:
            to_number: Recipient phone number
            event_type: Type of black swan event
            description: Event description
            affected_assets: List of affected asset tickers
        
        Returns:
            True if sent successfully, False otherwise
        """
        assets_str = ", ".join(affected_assets)
        
        message = (
            f"🚨 BLACK SWAN EVENT\n\n"
            f"Type: {event_type.upper()}\n"
            f"Description: {description}\n"
            f"Affected Assets: {assets_str}\n\n"
            f"Review your positions immediately.\n\n"
            f"- Mineral AI Tracker"
        )
        
        return self._send_sms(to_number, message, alert_type="black_swan")
    
    def send_buffett_score_alert(
        self,
        to_number: str,
        ticker: str,
        old_score: float,
        new_score: float,
        recommendation: str
    ) -> bool:
        """
        Send Buffett Score change alert SMS (significant changes only)
        
        Args:
            to_number: Recipient phone number
            ticker: Asset ticker
            old_score: Previous Buffett score
            new_score: New Buffett score
            recommendation: New recommendation
        
        Returns:
            True if sent successfully, False otherwise
        """
        message = (
            f"📊 BUFFETT SCORE ALERT\n\n"
            f"Asset: {ticker}\n"
            f"Old Score: {old_score:.2f}\n"
            f"New Score: {new_score:.2f}\n"
            f"Recommendation: {recommendation.upper()}\n\n"
            f"- Mineral AI Tracker"
        )
        
        return self._send_sms(to_number, message, alert_type="buffett_score")
    
    def _send_sms(
        self,
        to_number: str,
        message: str,
        alert_type: str
    ) -> bool:
        """
        Send SMS via Twilio
        
        Args:
            to_number: Recipient phone number
            message: Message content
            alert_type: Type of alert for logging
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled or not self.client:
            logger.warning(f"SMS not sent (service disabled): {alert_type}")
            return False
        
        try:
            # Validate phone number format
            if not to_number.startswith("+"):
                to_number = "+" + to_number
            
            # Send SMS
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            logger.info(
                f"SMS sent successfully: {alert_type} | "
                f"To: {to_number} | "
                f"SID: {message_obj.sid}"
            )
            
            return True
            
        except TwilioRestException as e:
            logger.error(f"Twilio API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {e}")
            return False
    
    def send_batch_alerts(
        self,
        to_numbers: List[str],
        alert_type: str,
        **kwargs
    ) -> Dict[str, bool]:
        """
        Send alerts to multiple recipients
        
        Args:
            to_numbers: List of recipient phone numbers
            alert_type: Type of alert
            **kwargs: Alert-specific parameters
        
        Returns:
            Dictionary mapping phone numbers to success status
        """
        results = {}
        
        for number in to_numbers:
            if alert_type == "stop_loss":
                success = self.send_stop_loss_alert(
                    number,
                    kwargs.get("ticker", ""),
                    kwargs.get("current_price", 0),
                    kwargs.get("stop_loss", 0),
                    kwargs.get("position_value", 0)
                )
            elif alert_type == "target_price":
                success = self.send_target_price_alert(
                    number,
                    kwargs.get("ticker", ""),
                    kwargs.get("current_price", 0),
                    kwargs.get("target_price", 0),
                    kwargs.get("position_value", 0)
                )
            elif alert_type == "black_swan":
                success = self.send_black_swan_alert(
                    number,
                    kwargs.get("event_type", ""),
                    kwargs.get("description", ""),
                    kwargs.get("affected_assets", [])
                )
            elif alert_type == "buffett_score":
                success = self.send_buffett_score_alert(
                    number,
                    kwargs.get("ticker", ""),
                    kwargs.get("old_score", 0),
                    kwargs.get("new_score", 0),
                    kwargs.get("recommendation", "")
                )
            else:
                logger.warning(f"Unknown alert type: {alert_type}")
                success = False
            
            results[number] = success
        
        return results
    
    def test_connection(self) -> bool:
        """
        Test Twilio connection by sending a test message
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.enabled or not self.client:
            logger.warning("Cannot test connection (service disabled)")
            return False
        
        try:
            # Try to fetch account info (lightweight test)
            account = self.client.api.accounts(self.account_sid).fetch()
            logger.info(f"Twilio connection test successful. Account: {account.friendly_name}")
            return True
        except Exception as e:
            logger.error(f"Twilio connection test failed: {e}")
            return False


# Singleton instance for application-wide use
_twilio_service: Optional[TwilioNotificationService] = None


def get_twilio_service() -> Optional[TwilioNotificationService]:
    """Get or create the singleton Twilio service instance"""
    global _twilio_service
    
    if _twilio_service is None:
        from ..config import settings
        
        _twilio_service = TwilioNotificationService(
            account_sid=settings.TWILIO_ACCOUNT_SID,
            auth_token=settings.TWILIO_AUTH_TOKEN,
            from_number=settings.TWILIO_PHONE_NUMBER,
            enabled=True
        )
    
    return _twilio_service
