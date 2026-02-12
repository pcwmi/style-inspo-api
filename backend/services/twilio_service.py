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

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")
        # WhatsApp Business number (production) - falls back to sandbox if not set
        self.whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")

        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.warning("Twilio credentials not configured")
            self.client = None
        else:
            self.client = Client(self.account_sid, self.auth_token)

    def _chunk_message(self, body: str, max_length: int = 1500) -> List[str]:
        """
        Split a long message into chunks at natural boundaries.

        Uses 1500 to leave buffer for WhatsApp's 1600 limit.
        Splits at paragraph breaks (##, \n\n) or sentence boundaries.
        """
        if len(body) <= max_length:
            return [body]

        chunks = []
        remaining = body

        while remaining:
            if len(remaining) <= max_length:
                chunks.append(remaining)
                break

            # Find a good split point within max_length
            chunk = remaining[:max_length]

            # Try to split at ## header (markdown)
            header_pos = chunk.rfind('\n##')
            if header_pos > max_length // 2:
                split_at = header_pos
            else:
                # Try to split at double newline (paragraph)
                para_pos = chunk.rfind('\n\n')
                if para_pos > max_length // 2:
                    split_at = para_pos
                else:
                    # Try to split at single newline
                    line_pos = chunk.rfind('\n')
                    if line_pos > max_length // 2:
                        split_at = line_pos
                    else:
                        # Last resort: split at space
                        space_pos = chunk.rfind(' ')
                        split_at = space_pos if space_pos > 0 else max_length

            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()

        return chunks

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
            # Determine if WhatsApp - use WhatsApp Business number
            is_whatsapp = to.startswith("whatsapp:")
            if is_whatsapp:
                from_number = f"whatsapp:{self.whatsapp_number}"
            else:
                from_number = self.from_number

            # Split long messages into chunks
            chunks = self._chunk_message(body)
            last_sid = None

            import time
            for i, chunk in enumerate(chunks):
                if i > 0:
                    time.sleep(0.3)  # Small delay between chunks for ordering

                message = self.client.messages.create(
                    body=chunk,
                    from_=from_number,
                    to=to
                )
                last_sid = message.sid

            if len(chunks) > 1:
                logger.info(f"{'WhatsApp' if is_whatsapp else 'SMS'} sent to {to} in {len(chunks)} chunks: {last_sid}")
            else:
                logger.info(f"{'WhatsApp' if is_whatsapp else 'SMS'} sent to {to}: {last_sid}")
            return last_sid
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
            # Determine if WhatsApp - use WhatsApp Business number
            is_whatsapp = to.startswith("whatsapp:")
            if is_whatsapp:
                from_number = f"whatsapp:{self.whatsapp_number}"
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
