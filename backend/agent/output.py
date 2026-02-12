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

    def _split_message_sections(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """
        Split message into magic/identity sections for 3-part SMS flow.

        Returns (before_image, after_image) where:
        - before_image = "The magic:" section
        - after_image = "This outfit says:" section

        If text doesn't match the expected format, returns (text, None).
        """
        if not text:
            return None, None

        # Look for the "This outfit says:" marker (case insensitive, with or without bold)
        import re
        # Match **This outfit says:** or This outfit says: (with optional whitespace)
        pattern = r'(\*{0,2}This outfit says:?\*{0,2})'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            before_image = text[:match.start()].strip()
            after_image = text[match.start():].strip()
            return before_image if before_image else None, after_image if after_image else None

        # No marker found - send all text before image
        return text, None

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
            import time
            # Split text into before/after image sections
            before_image, after_image = self._split_message_sections(text)

            # Send in 3 parts: magic → image → how to wear it
            # Add delays to help WhatsApp deliver in order
            if before_image:
                send_sms(self.phone, before_image)
                time.sleep(0.5)  # 500ms delay
            send_mms(self.phone, " ", [collage_url])
            if after_image:
                time.sleep(0.5)  # 500ms delay
                send_sms(self.phone, after_image)

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
        self.message_sent = False  # Track if send() was called (to avoid duplicate sends)

    def send(self, text: Optional[str], images: List[str], layout: str = "list"):
        # Mark that send() was called (prevents duplicate sends in sms.py)
        self.message_sent = True

        # First, send via parent class (collage)
        super().send(text, images, layout)

        # Capture outfit for state if this looks like an outfit
        # (layout="outfit" or multiple images suggesting a styled look)
        is_outfit = images and (layout == "outfit" or len(images) >= 2)

        if is_outfit:
            # Normalize to web format (items[].image_path) for consistency
            # This ensures SMS-saved outfits work with visualization_manager
            outfit_data = {
                "items": [
                    {"image_path": url, "name": f"Item {i+1}"}
                    for i, url in enumerate(images)
                ],
                "image_urls": images,  # Keep for backward compat
                "styling_notes": text,
            }
            self.state_manager.set_last_outfit(outfit_data)
            logger.info(f"StatefulSMSOutput: captured outfit with {len(images)} items to state")

            # Send expectation message for visualization (Step 1: set user expectations)
            from services.twilio_service import send_sms
            send_sms(self.phone, "✨ Generating a styled version for you... (~15 more seconds)")
            logger.info(f"StatefulSMSOutput: sent visualization expectation message to {self.phone}")

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
                    send_mms(self.phone, "Here's how it looks on you! 👗", [viz_url])
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
