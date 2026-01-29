"""
Twilio Service - SMS and MMS sending.

Simple wrapper around Twilio API for sending messages.
"""

import os
import logging
from typing import Optional, List

from twilio.rest import Client

logger = logging.getLogger(__name__)


class TwilioService:
    """Twilio SMS/MMS service."""

    # WhatsApp sandbox number (shared by all Twilio sandbox users)
    WHATSAPP_SANDBOX_NUMBER = "+14155238886"

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")

        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.warning("Twilio credentials not configured")
            self.client = None
        else:
            self.client = Client(self.account_sid, self.auth_token)

    def send_sms(self, to: str, body: str) -> Optional[str]:
        """
        Send an SMS or WhatsApp message.

        Args:
            to: Recipient phone number (E.164 format: +1xxxxxxxxxx or whatsapp:+1xxxxxxxxxx)
            body: Message text (will be split if > 1600 chars)

        Returns:
            Message SID if successful, None otherwise
        """
        if not self.client:
            logger.error("Twilio client not initialized")
            return None

        try:
            # Determine if WhatsApp - use sandbox number for WhatsApp
            is_whatsapp = to.startswith("whatsapp:")
            if is_whatsapp:
                from_number = f"whatsapp:{self.WHATSAPP_SANDBOX_NUMBER}"
            else:
                from_number = self.from_number

            message = self.client.messages.create(
                body=body,
                from_=from_number,
                to=to
            )
            logger.info(f"{'WhatsApp' if is_whatsapp else 'SMS'} sent to {to}: {message.sid}")
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send message to {to}: {e}")
            return None

    def send_mms(
        self,
        to: str,
        body: str,
        media_urls: List[str]
    ) -> Optional[str]:
        """
        Send an MMS or WhatsApp message with images.

        Args:
            to: Recipient phone number (E.164 format or whatsapp:+1xxxxxxxxxx)
            body: Message text
            media_urls: List of publicly accessible image URLs

        Returns:
            Message SID if successful, None otherwise
        """
        if not self.client:
            logger.error("Twilio client not initialized")
            return None

        try:
            # Determine if WhatsApp - use sandbox number for WhatsApp
            is_whatsapp = to.startswith("whatsapp:")
            if is_whatsapp:
                from_number = f"whatsapp:{self.WHATSAPP_SANDBOX_NUMBER}"
            else:
                from_number = self.from_number

            message = self.client.messages.create(
                body=body,
                from_=from_number,
                to=to,
                media_url=media_urls
            )
            logger.info(f"{'WhatsApp' if is_whatsapp else 'MMS'} with media sent to {to}: {message.sid}")
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send MMS to {to}: {e}")
            return None


# Singleton instance
_twilio_service: Optional[TwilioService] = None


def get_twilio_service() -> TwilioService:
    """Get or create Twilio service instance."""
    global _twilio_service
    if _twilio_service is None:
        _twilio_service = TwilioService()
    return _twilio_service


def send_sms(to: str, body: str) -> Optional[str]:
    """Convenience function to send SMS."""
    return get_twilio_service().send_sms(to, body)


def send_mms(to: str, body: str, media_urls: List[str]) -> Optional[str]:
    """Convenience function to send MMS."""
    return get_twilio_service().send_mms(to, body, media_urls)
