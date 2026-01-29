"""
Matching Primitive - Fuzzy match item names to wardrobe items.

Reuses the reveal page's proven three-tier matching logic:
1. Anchor items (user-selected)
2. Wardrobe items (fuzzy substring match)
3. Consider-buying items (fuzzy substring match)

This primitive enables the agent to return item NAMES rather than IDs,
and we fuzzy match to get the actual images.
"""

from typing import Dict, List, Optional, Any
import logging

from services.wardrobe_manager import WardrobeManager
from services.consider_buying_manager import ConsiderBuyingManager

logger = logging.getLogger(__name__)


def match_items_to_wardrobe(
    user_id: str,
    item_names: List[str],
    anchor_items: Optional[List[Dict]] = None
) -> List[Dict[str, Any]]:
    """
    Fuzzy match item names to wardrobe items.

    Uses the same three-tier matching logic as the reveal page:
    1. Anchor items (if provided) - exact user selections
    2. Wardrobe items - fuzzy substring matching
    3. Consider-buying items - fuzzy substring matching

    Args:
        user_id: User identifier
        item_names: List of item names from agent (e.g., ["Gray tee", "Floral skirt"])
        anchor_items: Optional pre-selected items to prioritize

    Returns:
        List of matched items with image_path, or placeholder for unmatched
        Each item: {
            "name": str,
            "category": str,
            "image_path": str or None,
            "matched": bool,
            "id": str or None
        }
    """
    # Load wardrobe and considering items
    wardrobe_manager = WardrobeManager(user_id=user_id)
    considering_manager = ConsiderBuyingManager(user_id=user_id)

    all_wardrobe = wardrobe_manager.get_wardrobe_items(filter_type="all")
    all_considering = considering_manager.get_items()

    # Build anchor lookup if provided
    anchor_lookup = {}
    if anchor_items:
        anchor_lookup = {item.get("id"): item for item in anchor_items}

    results = []

    for item_name in item_names:
        matched = None
        item_name_lower = item_name.lower().strip()

        # Skip empty names
        if not item_name_lower:
            continue

        # FIRST: Try to match anchor items with fuzzy matching
        for anchor_id, anchor_item in anchor_lookup.items():
            anchor_name = anchor_item.get("styling_details", {}).get("name", "").lower()
            if anchor_name and _fuzzy_match(item_name_lower, anchor_name):
                matched = anchor_item
                logger.info(f"Anchor match: '{item_name}' -> '{anchor_name}'")
                break

        # SECOND: Try fuzzy name match in wardrobe
        if not matched:
            for item in all_wardrobe:
                wardrobe_name = item.get("styling_details", {}).get("name", "").lower()
                if wardrobe_name and _fuzzy_match(item_name_lower, wardrobe_name):
                    matched = item
                    logger.info(f"Wardrobe match: '{item_name}' -> '{wardrobe_name}'")
                    break

        # THIRD: Try fuzzy name match in consider-buying items
        if not matched:
            for item in all_considering:
                consider_name = item.get("styling_details", {}).get("name", "").lower()
                if consider_name and _fuzzy_match(item_name_lower, consider_name):
                    matched = item
                    logger.info(f"Consider-buying match: '{item_name}' -> '{consider_name}'")
                    break

        if matched:
            # Handle image_path - wardrobe items have it in system_metadata,
            # consider-buying items may have it at top level
            image_path = (
                matched.get("system_metadata", {}).get("image_path") or
                matched.get("image_path")
            )

            results.append({
                "name": matched.get("styling_details", {}).get("name", item_name),
                "category": matched.get("styling_details", {}).get("category", "unknown"),
                "image_path": image_path,
                "matched": True,
                "id": matched.get("id")
            })
        else:
            logger.warning(f"No match found for: '{item_name}'")
            results.append({
                "name": item_name,
                "category": "unknown",
                "image_path": None,
                "matched": False,
                "id": None
            })

    return results


def _fuzzy_match(name1: str, name2: str) -> bool:
    """
    Fuzzy matching with multiple strategies.

    1. Substring match (original reveal page logic)
    2. Word overlap - if most words from shorter name appear in longer name

    Returns True if names match via any strategy.
    """
    # Strategy 1: Substring match (original logic)
    if name1 in name2 or name2 in name1:
        return True

    # Strategy 2: Word overlap
    # Tokenize into words (strip punctuation, lowercase already applied)
    words1 = set(name1.replace("-", " ").replace("'", "").split())
    words2 = set(name2.replace("-", " ").replace("'", "").split())

    # Remove common stopwords
    stopwords = {"a", "an", "the", "with", "and", "in", "on", "for"}
    words1 = words1 - stopwords
    words2 = words2 - stopwords

    if not words1 or not words2:
        return False

    # Calculate overlap
    common = words1 & words2
    shorter_len = min(len(words1), len(words2))

    # Match if at least 60% of words from shorter name appear in longer
    # or if at least 2 key words match
    overlap_ratio = len(common) / shorter_len if shorter_len > 0 else 0

    return overlap_ratio >= 0.6 or len(common) >= 2


def extract_item_names_from_response(response: str) -> List[str]:
    """
    Extract item names from agent response.

    Expects format:
    ITEMS:
    - Item name 1
    - Item name 2
    - Item name 3

    Returns list of item names.
    """
    items = []

    # Look for ITEMS: section
    if "ITEMS:" in response:
        lines = response.split("ITEMS:")[1].strip().split("\n")
        for line in lines:
            line = line.strip()
            # Stop at empty line or next section header
            if not line or (line.isupper() and line.endswith(":")):
                break
            # Remove bullet point markers
            if line.startswith("-"):
                line = line[1:].strip()
            elif line.startswith("•"):
                line = line[1:].strip()
            elif line.startswith("*"):
                line = line[1:].strip()
            # Skip empty lines after stripping
            if line:
                items.append(line)

    return items
