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


class StatefulSMSOutput(SMSOutput):
    """SMS output that captures outfits for conversation state.

    Extends SMSOutput to also save sent outfits to Redis-backed state,
    enabling multi-turn conversations ("save this", "swap the shoes", etc.)

    Also triggers automatic visualization for outfits (sent as follow-up MMS).
    """

    def __init__(self, phone: str, user_id: str, state_manager):
        super().__init__(phone, user_id)
        self.state_manager = state_manager

    def send(self, text: Optional[str], images: List[str], layout: str = "list"):
        # First, send via parent class (collage)
        super().send(text, images, layout)

        # Capture outfit for state if this looks like an outfit
        # (layout="outfit" or multiple images suggesting a styled look)
        is_outfit = images and (layout == "outfit" or len(images) >= 2)

        if is_outfit:
            outfit_data = {
                "image_urls": images,
                "styling_notes": text,
            }
            self.state_manager.set_last_outfit(outfit_data)
            logger.info(f"StatefulSMSOutput: captured outfit with {len(images)} items to state")

            # Trigger background visualization (sends follow-up MMS)
            self._trigger_background_visualization(images)

    def _trigger_background_visualization(self, images: List[str]):
        """Spawn background thread to generate and send visualization."""
        import threading

        def run_visualization():
            try:
                from services.visualization.visualization_manager import VisualizationManager
                from services.twilio_service import send_sms, send_mms

                logger.info(f"Starting background visualization for {self.user_id}")

                viz_manager = VisualizationManager(self.user_id)
                result = viz_manager.visualize_from_images(images)

                if result and result.get("visualization_url"):
                    viz_url = result["visualization_url"]
                    send_mms(self.phone, "Here's how it looks styled on you!", [viz_url])
                    logger.info(f"StatefulSMSOutput: sent visualization to {self.phone}")
                else:
                    # Silent fail - don't bother user
                    logger.warning(f"StatefulSMSOutput: visualization failed for {self.user_id}")

            except Exception as e:
                # Silent fail
                logger.error(f"StatefulSMSOutput: visualization error: {e}")

        # Run in background thread
        thread = threading.Thread(target=run_visualization, daemon=True)
        thread.start()
        logger.info(f"StatefulSMSOutput: spawned visualization thread for {self.user_id}")


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
