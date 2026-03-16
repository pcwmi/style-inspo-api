"""
Agent context loading - pre-fetch user data to eliminate LLM round-trips.

Shared across all channels (SMS, web, API).
"""

import json
import logging

logger = logging.getLogger(__name__)

MAX_RECENT_GENERATIONS = 3
RECENT_GENERATIONS_FILE = "recent_generations.json"


def record_generated_outfit(user_id: str, item_names: list[str]):
    """Record an outfit that was just generated (not necessarily saved).

    Called by output handlers after present_outfit to track what the agent
    suggested, so future generations can avoid repeating items.
    """
    from services.storage_manager import StorageManager
    sm = StorageManager(storage_type="s3", user_id=user_id)
    try:
        data = sm.load_json(RECENT_GENERATIONS_FILE)
    except Exception:
        data = {"outfits": []}

    data["outfits"].append(item_names)
    data["outfits"] = data["outfits"][-MAX_RECENT_GENERATIONS:]
    sm.save_json(data, RECENT_GENERATIONS_FILE)


def get_recent_generations(user_id: str) -> list[list[str]]:
    """Read recently generated outfit item names for variety context."""
    from services.storage_manager import StorageManager
    sm = StorageManager(storage_type="s3", user_id=user_id)
    try:
        data = sm.load_json(RECENT_GENERATIONS_FILE)
        return data.get("outfits", [])
    except Exception:
        return []


def preload_user_context(user_id: str) -> str:
    """Pre-fetch profile, wardrobe items, and feedback patterns.

    Injected into the system prompt to eliminate the first LLM round-trip
    where the agent would call get_profile + get_items + get_feedback_patterns.
    """
    from services.wardrobe_manager import WardrobeManager
    from services.user_profile_manager import UserProfileManager
    from services.disliked_outfits_manager import DislikedOutfitsManager

    sections = []

    # Profile
    try:
        profile = UserProfileManager(user_id=user_id).get_profile(user_id)
        if profile:
            sections.append(f"Profile: {json.dumps(profile, default=str)}")
    except Exception as e:
        logger.warning(f"Failed to preload profile: {e}")

    # Wardrobe items (compact format, shuffled to prevent positional bias)
    try:
        from agent.agent import get_compact_items
        items = WardrobeManager(user_id=user_id).get_wardrobe_items(filter_type="all")
        compact = get_compact_items(items, include_image_url=False)
        sections.append(f"Wardrobe ({len(compact)} items): {json.dumps(compact)}")
    except Exception as e:
        logger.warning(f"Failed to preload items: {e}")

    # Feedback patterns (same filtering as get_feedback_patterns tool)
    try:
        USELESS = {
            "the outfit doesn't make sense", "not my style",
            "won't look good on me", "doesn't match my occasions",
            "i don't like this outfit", "doesn't fit my style",
        }
        feedback_list = DislikedOutfitsManager(user_id=user_id).get_disliked_outfits(enrich_with_current_images=False)
        actionable = []
        for f in feedback_list:
            reason = f.get("user_reason", "").strip()
            if not reason or reason.lower().strip('"') in USELESS:
                continue
            reason_clean = reason.strip('"').strip()
            if reason_clean.lower().startswith('other:'):
                reason = reason_clean[6:].strip()
            else:
                reason = reason_clean
            items_data = f.get("outfit_data", {}).get("items", [])
            item_names = [i.get("name", "Unknown") for i in items_data]
            actionable.append({"items": item_names, "reason": reason})
        if actionable:
            sections.append(f"Feedback patterns ({len(actionable)} actionable): {json.dumps(actionable)}")
    except Exception as e:
        logger.warning(f"Failed to preload feedback: {e}")

    # Recent generations (for variety — avoid repeating items)
    try:
        recent_items = get_recent_generations(user_id)
        if recent_items:
            sections.append(
                f"Recent outfits ({len(recent_items)} most recent — AVOID reusing these items): "
                f"{json.dumps(recent_items)}"
            )
    except Exception as e:
        logger.warning(f"Failed to preload recent generations: {e}")

    return "\n\n".join(sections)
