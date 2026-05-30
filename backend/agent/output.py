"""
Output primitive - modality-aware message sending.

This is DETERMINISTIC. No AI. Just rendering + delivery.
The agent decides WHAT to send, this layer decides HOW to render it.
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger(__name__)


def resolve_items_from_urls(user_id: str, image_urls: List[str]) -> List[dict]:
    """Map image URLs to full wardrobe item metadata. Single source of truth.

    Returns list of dicts with: {id, name, category, sub_category, image_url}
    Falls back to generic placeholders for unmatched URLs.
    """
    try:
        from services.wardrobe_manager import WardrobeManager
        wm = WardrobeManager(user_id=user_id)
        all_items = wm.get_wardrobe_items(filter_type="all")

        url_to_item = {}
        for item in all_items:
            url = item.get("system_metadata", {}).get("image_path", "")
            if url:
                url_to_item[url] = item

        result = []
        for i, url in enumerate(image_urls):
            item = url_to_item.get(url)
            if item:
                sd = item.get("styling_details", {})
                result.append({
                    "id": item.get("id", ""),
                    "name": sd.get("name", ""),
                    "category": sd.get("category", "unknown"),
                    "sub_category": sd.get("sub_category", ""),
                    "image_url": url,
                })
            else:
                result.append({
                    "id": "",
                    "name": f"Item {i + 1}",
                    "category": "unknown",
                    "sub_category": "",
                    "image_url": url,
                })
        return result
    except Exception as e:
        logger.warning(f"resolve_items_from_urls failed for {user_id}: {e}")
        return [{"id": "", "name": f"Item {i + 1}", "category": "unknown", "sub_category": "", "image_url": url}
                for i, url in enumerate(image_urls)]


def parse_outfit_text(text: Optional[str]) -> dict:
    """Parse agent outfit text into structured sections.

    Returns: {magic: str, identity: str, full: str}
    - magic = "The magic:" content (styling notes, markdown stripped)
    - identity = "This outfit says:" content (markdown stripped)
    - full = original text
    """
    if not text:
        return {"magic": "", "identity": "", "full": ""}

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

    magic = re.sub(r'\*+', '', magic_match.group(1)).strip() if magic_match else text.strip()
    identity = re.sub(r'\*+', '', identity_match.group(1)).strip() if identity_match else ""

    return {"magic": magic, "identity": identity, "full": text}


class OutputHandler(ABC):
    """Base class for modality-specific output."""

    @abstractmethod
    def send(self, text: Optional[str], images: List[str]):
        """Send text and/or images as-is. No collage processing."""
        pass

    @abstractmethod
    def present_outfit(self, text: Optional[str], images: List[str], visualize: bool = False, skip_enhance: bool = False):
        """Present a new outfit with editorial collage."""
        pass

    @staticmethod
    def _record_for_variety(user_id: str, resolved_items: List[dict]):
        """Record generated outfit item names for variety tracking."""
        try:
            from agent.context import record_generated_outfit
            names = [r["name"] for r in resolved_items if r.get("name")]
            if names:
                record_generated_outfit(user_id, names)
        except Exception as e:
            logger.warning(f"Failed to record generation for variety: {e}")


class SMSOutput(OutputHandler):
    """SMS/WhatsApp output via Twilio."""

    def __init__(self, phone: str, user_id: str):
        self.phone = phone
        self.user_id = user_id


    def send(self, text: Optional[str], images: List[str]):
        """Send text and/or images as-is. No collage. Each image sent individually."""
        from services.twilio_service import send_sms, send_mms

        if not images:
            if text:
                send_sms(self.phone, text)
                logger.info(f"SMSOutput: sent text to {self.phone}")
            return

        import time

        # Send text first, then each image as individual MMS
        if text:
            send_sms(self.phone, text)
            time.sleep(0.5)

        for image_url in images:
            send_mms(self.phone, " ", [image_url])
            time.sleep(0.5)

        logger.info(f"SMSOutput: sent {len(images)} individual image(s) to {self.phone}")

    def present_outfit(self, text: Optional[str], images: List[str], visualize: bool = False, skip_enhance: bool = False):
        """Present a new outfit with editorial collage."""
        from services.twilio_service import send_sms, send_mms
        from services.collage import generate_outfit_collage

        if not images:
            if text:
                send_sms(self.phone, text)
                logger.info(f"SMSOutput: sent outfit text (no images) to {self.phone}")
            return

        import time

        # Resolve item metadata so collage knows categories for silhouette layout
        items_metadata = resolve_items_from_urls(self.user_id, images)
        self._record_for_variety(self.user_id, items_metadata)

        collage_urls = []
        url = generate_outfit_collage(self.user_id, images, items=items_metadata, skip_enhance=skip_enhance)
        if url:
            collage_urls.append(url)

        if not collage_urls:
            logger.warning("SMSOutput: collage generation failed, sending text only")
            if text:
                send_sms(self.phone, text)
            else:
                send_sms(self.phone, "Here are your items (images unavailable)")
            return

        # Split text into magic/identity sections for 3-part SMS flow
        parsed = parse_outfit_text(text)
        before_image = parsed["magic"] if parsed["magic"] else (text if text else None)
        after_image = f"This outfit says: {parsed['identity']}" if parsed["identity"] else None

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

    def send(self, text: Optional[str], images: List[str]):
        self.message_sent = True
        super().send(text, images)

    def present_outfit(self, text: Optional[str], images: List[str], visualize: bool = False, skip_enhance: bool = False):
        self.message_sent = True

        # Send via parent class (collage + text)
        super().present_outfit(text, images, visualize, skip_enhance=skip_enhance)

        # Capture outfit state + trigger visualization
        if visualize and images:
            resolved = resolve_items_from_urls(self.user_id, images)
            items_with_names = [{"image_path": r["image_url"], "name": r["name"]} for r in resolved]

            outfit_data = {
                "items": items_with_names,
                "image_urls": images,
                "styling_notes": text,
            }
            self.state_manager.set_last_outfit(outfit_data)
            logger.info(f"StatefulSMSOutput: captured outfit with {len(images)} items to state")

            from services.twilio_service import send_sms
            send_sms(self.phone, "Generating a styled version for you... this can take about a minute.")
            logger.info(f"StatefulSMSOutput: sent visualization expectation message to {self.phone}")

            item_names = [r["name"] for r in resolved if r.get("name")]
            styling_hint = parse_outfit_text(text)["magic"][:150]
            self._trigger_background_visualization(images, styling_hint, item_names=item_names)

    def _trigger_background_visualization(
        self,
        images: List[str],
        styling_notes: str = "",
        item_names: Optional[List[str]] = None,
    ):
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
                result = viz_manager.visualize_from_images(
                    images,
                    styling_notes=styling_notes,
                    item_names=item_names or [],
                )

                if result and result.get("visualization_url"):
                    viz_url = result["visualization_url"]
                    send_mms(self.phone, "Here's how it looks on you.", [viz_url])
                    logger.info(f"StatefulSMSOutput: sent visualization to {self.phone}")

                    # Persist viz URL to conversation state for later save_outfit linkage
                    try:
                        state = self.state_manager.get_state()
                        if state and state.last_outfit:
                            state.last_outfit["visualization_url"] = viz_url
                            self.state_manager.save_state(state)
                            logger.info(f"StatefulSMSOutput: persisted viz_url to conversation state")
                    except Exception as e:
                        logger.warning(f"StatefulSMSOutput: failed to persist viz_url: {e}")
                else:
                    error = (result or {}).get("error", "unknown error")
                    logger.warning(f"StatefulSMSOutput: visualization failed for {self.user_id}: {error}")
                    send_sms(
                        self.phone,
                        "I couldn't generate the on-person view this time, but the outfit collage above is ready."
                    )

            except Exception as e:
                logger.error(f"StatefulSMSOutput: visualization error: {e}")
                try:
                    from services.twilio_service import send_sms
                    send_sms(
                        self.phone,
                        "I couldn't generate the on-person view this time, but the outfit collage above is ready."
                    )
                except Exception:
                    logger.exception("StatefulSMSOutput: failed to send visualization failure fallback")

        # Run in background thread
        thread = threading.Thread(target=run_visualization, daemon=True)
        thread.start()
        logger.info(f"StatefulSMSOutput: spawned visualization thread for {self.user_id}")


class WebOutput(OutputHandler):
    """Web output - collects structured outfits for SSE streaming.

    When the agent calls present_outfit, this handler enriches the data
    into the format the frontend expects (items with IDs, image_paths,
    styling_notes, viz_key) and puts it on a queue for the SSE endpoint
    to stream.
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

    def send(self, text: Optional[str], images: List[str]):
        # Non-outfit messages (browse results, text-only) — log but don't queue as outfit
        logger.info(f"WebOutput: non-outfit message ({len(images)} images)")

    def present_outfit(self, text: Optional[str], images: List[str], visualize: bool = False, skip_enhance: bool = False):
        if images:
            enriched = self._enrich_outfit(text, images, visualize, skip_enhance=skip_enhance)
            self.outfits.append(enriched)
            if self.outfit_queue:
                self.outfit_queue.put_nowait(enriched)

    def _enrich_outfit(self, text: Optional[str], images: List[str], visualize: bool, skip_enhance: bool = False) -> dict:
        """Convert agent send_message into web outfit format."""
        import hashlib

        # Reverse-lookup image URLs to wardrobe items
        resolved = resolve_items_from_urls(self.user_id, images)
        self._record_for_variety(self.user_id, resolved)
        # Frontend expects image_path key
        enriched_items = [{**r, "image_path": r["image_url"]} for r in resolved]

        # Generate editorial collage (same as SMS/API flows)
        collage_url = None
        try:
            from services.collage import generate_outfit_collage
            collage_url = generate_outfit_collage(self.user_id, images, items=resolved, skip_enhance=skip_enhance)
        except Exception as e:
            logger.warning(f"WebOutput: collage generation failed: {e}")

        # Parse agent text into styling_notes and why_it_works
        parsed = parse_outfit_text(text)
        styling_notes, why_it_works = parsed["magic"], parsed["identity"]

        outfit = {
            "items": enriched_items,
            "collage_url": collage_url,
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

            from services.visualization.viz_trigger import trigger_visualization_by_key
            trigger_visualization_by_key(self.user_id, viz_key, garment_images)

        return outfit


class APIOutput(OutputHandler):
    """Collects agent output for API responses. No side effects."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.outfits = []
        self.messages = []

    def send(self, text: Optional[str], images: List[str]):
        msg = {"text": text, "images": images or []}
        self.messages.append(msg)
        logger.info(f"APIOutput: collected message with {len(images)} images")

    def present_outfit(self, text: Optional[str], images: List[str], visualize: bool = False, skip_enhance: bool = False):
        outfit = {"text": text, "images": images or []}

        if images:
            items_meta = resolve_items_from_urls(self.user_id, images)
            self._record_for_variety(self.user_id, items_meta)
            from services.collage import generate_outfit_collage
            collage_url = generate_outfit_collage(self.user_id, images, items=items_meta, skip_enhance=skip_enhance)
            outfit["collage_url"] = collage_url

            if visualize:
                try:
                    from services.visualization.visualization_manager import VisualizationManager
                    viz_manager = VisualizationManager(self.user_id)
                    result = viz_manager.visualize_from_images(images)
                    if result and result.get("visualization_url"):
                        outfit["visualization_url"] = result["visualization_url"]
                except Exception as e:
                    logger.warning(f"APIOutput: visualization failed: {e}")

        self.outfits.append(outfit)
        if text:
            self.messages.append(text)
        logger.info(f"APIOutput: collected outfit with {len(images)} images, visualize={visualize}")


class MockOutput(OutputHandler):
    """Mock output handler for testing - captures what would be sent."""

    def __init__(self):
        self.messages = []

    def send(self, text: Optional[str], images: List[str]):
        self.messages.append({
            "tool": "send_message",
            "text": text,
            "images": images,
        })
        logger.info(f"MockOutput: captured send_message with {len(images)} images")

    def present_outfit(self, text: Optional[str], images: List[str], visualize: bool = False, skip_enhance: bool = False):
        self.messages.append({
            "tool": "present_outfit",
            "text": text,
            "images": images,
            "visualize": visualize,
        })
        logger.info(f"MockOutput: captured present_outfit with {len(images)} images, visualize={visualize}")
