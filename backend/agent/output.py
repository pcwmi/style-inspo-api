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
    def send(self, text: Optional[str], images: List[str], layout: str = "list", visualize: bool = False):
        """
        Send a message to the user.

        Args:
            text: Optional text message
            images: List of image URLs to include
            layout: 'list' for browsing items, 'outfit' for styled collage
            visualize: Whether to generate a styled model visualization (agent decides)
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

    def send(self, text: Optional[str], images: List[str], layout: str = "list", visualize: bool = False):
        from services.twilio_service import send_sms, send_mms
        from services.collage import generate_outfit_collage

        if not images:
            # Text only
            if text:
                send_sms(self.phone, text)
                logger.info(f"SMSOutput: sent text to {self.phone}")
            return

        import time

        # Split images into chunks of 6 for collage generation
        chunks = [images[i:i+6] for i in range(0, len(images), 6)]
        collage_urls = []
        for chunk in chunks:
            url = generate_outfit_collage(self.user_id, chunk)
            if url:
                collage_urls.append(url)

        if not collage_urls:
            # Fallback: send text only if all collages fail
            logger.warning("SMSOutput: collage generation failed, sending text only")
            if text:
                send_sms(self.phone, text)
            else:
                send_sms(self.phone, "Here are your items (images unavailable)")
            return

        # Split text into before/after image sections
        before_image, after_image = self._split_message_sections(text)

        # Send: text → collage(s) → after-image text
        if before_image:
            send_sms(self.phone, before_image)
            time.sleep(0.5)

        for collage_url in collage_urls:
            send_mms(self.phone, " ", [collage_url])
            time.sleep(0.5)

        if after_image:
            send_sms(self.phone, after_image)

        logger.info(f"SMSOutput: sent {len(images)} images as {len(collage_urls)} collage(s) to {self.phone}")


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

    def send(self, text: Optional[str], images: List[str], layout: str = "list", visualize: bool = False):
        # Mark that send() was called (prevents duplicate sends in sms.py)
        self.message_sent = True

        # First, send via parent class (collage + text)
        super().send(text, images, layout, visualize)

        # Agent decides whether this is an outfit worth saving + visualizing
        if visualize and images:
            # Look up actual item names from URLs (for meaningful context)
            items_with_names = self._lookup_item_names(images)

            outfit_data = {
                "items": items_with_names,
                "image_urls": images,
                "styling_notes": text,
            }
            self.state_manager.set_last_outfit(outfit_data)
            logger.info(f"StatefulSMSOutput: captured outfit with {len(images)} items to state")

            # Send expectation message for visualization
            from services.twilio_service import send_sms
            send_sms(self.phone, "Generating a styled version for you... (~15 more seconds)")
            logger.info(f"StatefulSMSOutput: sent visualization expectation message to {self.phone}")

            # Trigger background visualization (sends follow-up MMS)
            styling_hint = self._extract_magic_section(text)
            self._trigger_background_visualization(images, styling_hint)

    def _lookup_item_names(self, image_urls: List[str]) -> List[dict]:
        """Reverse-lookup item names from image URLs.

        Maps URLs back to wardrobe items so SESSION_STATE shows real names
        like "Grey cashmere sweater" instead of "Item 1".
        """
        try:
            from services.wardrobe_manager import WardrobeManager
            wm = WardrobeManager(user_id=self.user_id)
            all_items = wm.get_wardrobe_items(filter_type="all")

            # Build URL -> item name mapping
            url_to_name = {}
            for item in all_items:
                # URL is stored as image_path, not image_url
                url = item.get("system_metadata", {}).get("image_path", "")
                name = item.get("styling_details", {}).get("name", "")
                if url and name:
                    url_to_name[url] = name

            # Map each image URL to its name (fallback to generic if not found)
            result = []
            for i, url in enumerate(image_urls):
                name = url_to_name.get(url, f"Item {i+1}")
                result.append({"image_path": url, "name": name})

            logger.info(f"_lookup_item_names: matched {sum(1 for r in result if not r['name'].startswith('Item '))} of {len(image_urls)} items")
            return result

        except Exception as e:
            logger.warning(f"_lookup_item_names failed: {e}, using generic names")
            return [{"image_path": url, "name": f"Item {i+1}"} for i, url in enumerate(image_urls)]

    def _extract_magic_section(self, text: str) -> str:
        """Extract 'The magic:' section from outfit text for Runway styling hints."""
        if not text:
            return ""

        import re
        # Find "The magic:" or "**The magic:**" section
        match = re.search(r'\*{0,2}The magic:?\*{0,2}\s*(.+?)(?:\n\n|\*{0,2}This outfit says|\Z)', text, re.IGNORECASE | re.DOTALL)
        if match:
            magic = match.group(1).strip()
            # Clean up markdown formatting
            magic = re.sub(r'\*+', '', magic)
            # Limit to 150 chars for Runway prompt budget
            return magic[:150] if len(magic) > 150 else magic
        return ""

    def _trigger_background_visualization(self, images: List[str], styling_notes: str = ""):
        """Spawn background thread to generate and send visualization."""
        import threading

        def run_visualization():
            try:
                from services.visualization.visualization_manager import VisualizationManager
                from services.twilio_service import send_sms, send_mms

                logger.info(f"Starting background visualization for {self.user_id}")
                if styling_notes:
                    logger.info(f"Styling hint for Runway: {styling_notes[:80]}...")

                viz_manager = VisualizationManager(self.user_id)
                result = viz_manager.visualize_from_images(images, styling_notes=styling_notes)

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


class WebOutput(OutputHandler):
    """Web output - collects structured outfits for SSE streaming.

    When the agent calls send_message with layout="outfit", this handler
    enriches the data into the format the frontend expects (items with IDs,
    image_paths, styling_notes, viz_key) and puts it on a queue for the
    SSE endpoint to stream.
    """

    def __init__(self, user_id: str, outfit_queue=None):
        self.user_id = user_id
        self.outfit_queue = outfit_queue  # thread-safe queue for SSE bridge
        self.outfits = []
        self._pending_reasoning = []  # Accumulated reasoning since last outfit

    def capture_reasoning(self, tool_name: str, reasoning: str):
        """Called by agent loop when a tool is invoked with reasoning."""
        if reasoning:
            self._pending_reasoning.append({"tool": tool_name, "reasoning": reasoning})

    def send(self, text: Optional[str], images: List[str], layout: str = "list", visualize: bool = False):
        if layout == "outfit" and images:
            enriched = self._enrich_outfit(text, images, visualize)
            self.outfits.append(enriched)
            if self.outfit_queue:
                self.outfit_queue.put_nowait(enriched)
        else:
            # Non-outfit messages (browse results, text-only) — log but don't queue as outfit
            logger.info(f"WebOutput: non-outfit message ({len(images)} images, layout={layout})")

    def _enrich_outfit(self, text: Optional[str], images: List[str], visualize: bool) -> dict:
        """Convert agent send_message into web outfit format."""
        import hashlib

        # Reverse-lookup image URLs to wardrobe items
        enriched_items = self._resolve_items_from_urls(images)

        # Parse agent text into styling_notes and why_it_works
        styling_notes, why_it_works = self._parse_agent_text(text)

        outfit = {
            "items": enriched_items,
            "styling_notes": styling_notes,
            "why_it_works": why_it_works,
            "confidence_level": "medium",
            "vibe_keywords": [],
        }

        # Attach accumulated reasoning and reset
        if self._pending_reasoning:
            outfit["agent_reasoning"] = list(self._pending_reasoning)
            self._pending_reasoning = []

        # Viz key + background trigger
        garment_images = [item.get("image_path") for item in enriched_items if item.get("image_path")]
        if visualize and garment_images:
            viz_key = hashlib.md5('|'.join(sorted(garment_images)).encode()).hexdigest()[:12]
            outfit["viz_key"] = viz_key
            outfit["viz_pending"] = True

            from api.outfits import _trigger_visualization_by_key
            _trigger_visualization_by_key(self.user_id, viz_key, garment_images)

        return outfit

    def _resolve_items_from_urls(self, image_urls: List[str]) -> list:
        """Map image URLs back to full wardrobe item data."""
        try:
            from services.wardrobe_manager import WardrobeManager
            wm = WardrobeManager(user_id=self.user_id)
            all_items = wm.get_wardrobe_items(filter_type="all")

            url_to_item = {}
            for item in all_items:
                url = item.get("system_metadata", {}).get("image_path", "")
                if url:
                    url_to_item[url] = item

            enriched = []
            for url in image_urls:
                item = url_to_item.get(url)
                if item:
                    enriched.append({
                        "id": item.get("id"),
                        "name": item.get("styling_details", {}).get("name", ""),
                        "category": item.get("styling_details", {}).get("category", ""),
                        "sub_category": item.get("styling_details", {}).get("sub_category", ""),
                        "image_path": url,
                    })
                else:
                    enriched.append({"name": "Unknown item", "category": "unknown", "sub_category": "", "image_path": url})
            return enriched

        except Exception as e:
            logger.warning(f"WebOutput._resolve_items_from_urls failed: {e}")
            return [{"name": f"Item {i+1}", "category": "unknown", "sub_category": "", "image_path": url} for i, url in enumerate(image_urls)]

    def _parse_agent_text(self, text: Optional[str]) -> tuple:
        """Split agent text into (styling_notes, why_it_works)."""
        if not text:
            return "", ""

        import re

        # Extract "The magic:" section
        magic_match = re.search(
            r'\*{0,2}The magic:?\*{0,2}\s*(.+?)(?=\*{0,2}This outfit says|\Z)',
            text, re.DOTALL | re.IGNORECASE
        )
        # Extract "This outfit says:" section
        identity_match = re.search(
            r'\*{0,2}This outfit says:?\*{0,2}\s*(.+)',
            text, re.DOTALL | re.IGNORECASE
        )

        styling = magic_match.group(1).strip() if magic_match else text.strip()
        why = identity_match.group(1).strip() if identity_match else ""

        # Clean markdown bold markers
        styling = re.sub(r'\*+', '', styling).strip()
        why = re.sub(r'\*+', '', why).strip()

        return styling, why


class MockOutput(OutputHandler):
    """Mock output handler for testing - captures what would be sent."""

    def __init__(self):
        self.messages = []

    def send(self, text: Optional[str], images: List[str], layout: str = "list", visualize: bool = False):
        self.messages.append({
            "text": text,
            "images": images,
            "layout": layout,
            "visualize": visualize,
        })
        logger.info(f"MockOutput: captured message with {len(images)} images, layout={layout}, visualize={visualize}")
