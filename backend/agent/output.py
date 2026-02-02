"""
Output primitive - modality-aware message sending.

This is DETERMINISTIC. No AI. Just rendering + delivery.
The agent decides WHAT to send, this layer decides HOW to render it.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger(__name__)


class OutputHandler(ABC):
    """Base class for modality-specific output."""

    @abstractmethod
    def send(self, text: Optional[str], images: List[str], layout: str = "list"):
        """
        Send a message to the user.

        Args:
            text: Optional text message
            images: List of image URLs to include
            layout: 'list' for browsing items, 'outfit' for styled collage
        """
        pass


class SMSOutput(OutputHandler):
    """SMS/WhatsApp output via Twilio."""

    def __init__(self, phone: str, user_id: str):
        self.phone = phone
        self.user_id = user_id

    def send(self, text: Optional[str], images: List[str], layout: str = "list"):
        from services.twilio_service import send_sms, send_mms
        from services.collage import generate_outfit_collage

        if not images:
            # Text only
            if text:
                send_sms(self.phone, text)
                logger.info(f"SMSOutput: sent text to {self.phone}")
            return

        # Generate collage for images (both layouts use collage for SMS efficiency)
        collage_url = generate_outfit_collage(self.user_id, images)

        if collage_url:
            if text:
                send_sms(self.phone, text)
            send_mms(self.phone, " ", [collage_url])
            logger.info(f"SMSOutput: sent {len(images)} images as {layout} collage to {self.phone}")
        else:
            # Fallback: send text only if collage fails
            logger.warning("SMSOutput: collage generation failed, sending text only")
            if text:
                send_sms(self.phone, text)
            else:
                send_sms(self.phone, "Here are your items (images unavailable)")


class MockOutput(OutputHandler):
    """Mock output handler for testing - captures what would be sent."""

    def __init__(self):
        self.messages = []

    def send(self, text: Optional[str], images: List[str], layout: str = "list"):
        self.messages.append({
            "text": text,
            "images": images,
            "layout": layout
        })
        logger.info(f"MockOutput: captured message with {len(images)} images, layout={layout}")
