"""
Agent context loading - pre-fetch user data to eliminate LLM round-trips.

Shared across all channels (SMS, web, API).
"""

import json
import logging
import time

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


def _fetch_profile(user_id: str) -> str | None:
    """Fetch user profile section."""
    from services.user_profile_manager import UserProfileManager
    try:
        profile = UserProfileManager(user_id=user_id).get_profile(user_id)
        if profile:
            return f"Profile: {json.dumps(profile, default=str)}"
    except Exception as e:
        logger.warning(f"Failed to preload profile: {e}")
    return None


def _fetch_items(user_id: str) -> list:
    """Fetch compact wardrobe items."""
    from services.wardrobe_manager import WardrobeManager
    from agent.agent import get_compact_items
    try:
        items = WardrobeManager(user_id=user_id).get_wardrobe_items(filter_type="all")
        return get_compact_items(items, include_image_url=False)
    except Exception as e:
        logger.warning(f"Failed to preload items: {e}")
        return []


def _fetch_feedback(user_id: str) -> str | None:
    """Fetch actionable feedback patterns section."""
    from services.disliked_outfits_manager import DislikedOutfitsManager
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
            return f"Feedback patterns ({len(actionable)} actionable): {json.dumps(actionable)}"
    except Exception as e:
        logger.warning(f"Failed to preload feedback: {e}")
    return None


def _fetch_recent(user_id: str) -> list[list[str]]:
    """Fetch recent generation item names."""
    try:
        return get_recent_generations(user_id)
    except Exception as e:
        logger.warning(f"Failed to preload recent generations: {e}")
        return []


def _cap_wardrobe(items: list, max_items: int) -> list:
    """Cap wardrobe to max_items while keeping category diversity.

    Ensures at least 2 items per category (when available) before filling
    remaining slots randomly. Items are already shuffled by get_compact_items.
    """
    if len(items) <= max_items:
        return items

    # Group by category
    by_cat: dict[str, list] = {}
    for item in items:
        cat = item.get("category", "unknown")
        by_cat.setdefault(cat, []).append(item)

    # First pass: take up to 2 per category
    selected = []
    for cat, cat_items in by_cat.items():
        selected.extend(cat_items[:2])

    # Second pass: fill remaining slots from leftover items
    selected_names = {s.get("name") for s in selected}
    remaining = [i for i in items if i.get("name") not in selected_names]
    slots_left = max_items - len(selected)
    if slots_left > 0:
        selected.extend(remaining[:slots_left])

    return selected[:max_items]


def preload_user_context(user_id: str, max_items: int = 0) -> str:
    """Pre-fetch profile, wardrobe items, and feedback patterns.

    Injected into the system prompt to eliminate the first LLM round-trip
    where the agent would call get_profile + get_items + get_feedback_patterns.

    All four fetches run concurrently via ThreadPoolExecutor.

    Args:
        max_items: If > 0, cap wardrobe to this many items (category-balanced).
            Use for the fast path to reduce LLM input tokens.
    """
    from concurrent.futures import ThreadPoolExecutor

    preload_start = time.perf_counter()

    # Run all four fetches in parallel
    with ThreadPoolExecutor(max_workers=4) as pool:
        profile_fut = pool.submit(_fetch_profile, user_id)
        items_fut = pool.submit(_fetch_items, user_id)
        feedback_fut = pool.submit(_fetch_feedback, user_id)
        recent_fut = pool.submit(_fetch_recent, user_id)

    profile_section = profile_fut.result()
    compact_items = items_fut.result()
    feedback_section = feedback_fut.result()
    recent_items = recent_fut.result()

    # Assemble sections
    sections = []

    if profile_section:
        sections.append(profile_section)

    # Filter recently-used items from wardrobe for variety
    if compact_items:
        recently_used_names = set()
        for outfit_names in recent_items:
            recently_used_names.update(outfit_names)

        if recently_used_names and len(compact_items) > 20:
            filtered = [c for c in compact_items if c.get("name") not in recently_used_names]
            excluded = len(compact_items) - len(filtered)
        else:
            filtered = compact_items
            excluded = 0

        # Cap to max_items for fast path (reduces LLM input tokens)
        if max_items > 0 and len(filtered) > max_items:
            filtered = _cap_wardrobe(filtered, max_items)

        label = f"Wardrobe ({len(filtered)} items"
        if excluded:
            label += f", {excluded} recently-used hidden"
        if max_items > 0 and len(compact_items) > max_items:
            label += f", {len(compact_items) - len(filtered)} others omitted for speed"
        label += ")"
        sections.append(f"{label}: {json.dumps(filtered)}")

    if feedback_section:
        sections.append(feedback_section)

    if recent_items:
        sections.append(
            f"Recent outfits ({len(recent_items)} most recent — AVOID reusing these items): "
            f"{json.dumps(recent_items)}"
        )

    preload_ms = int((time.perf_counter() - preload_start) * 1000)
    logger.info(f"Context preload: {preload_ms}ms (parallel), {len(sections)} sections, {sum(len(s) for s in sections)} chars")
    return "\n\n".join(sections)
