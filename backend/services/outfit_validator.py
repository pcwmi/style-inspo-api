"""
Outfit Validator - Slot-based physical plausibility check.

Maps each item's sub_category to a body "slot" and enforces max
occupancy per slot. Catches physically impossible combos like
vest + cardigan (both mid-layers) or t-shirt + t-shirt.

Wired into resolve_items in agent.py — invalid outfits are rejected
back to the agent with a suggestion to try a different combination.
"""

from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# --- Slot Mapping ---

# Sub-category -> body slot
# Format matches restructure_metadata.py output: "category_specific"
SUBCATEGORY_TO_SLOT = {
    # Base tops (worn against body)
    "tops_tshirt": "base_top",
    "tops_tank": "base_top",
    "tops_blouse": "base_top",
    "tops_buttonup": "base_top",
    "tops_polo": "base_top",
    "tops_crop": "base_top",
    "tops_henley": "base_top",
    "tops_bodysuit": "base_top",

    # Mid layers (worn over base)
    "tops_sweater": "mid_layer",
    "tops_cardigan": "mid_layer",
    "tops_vest": "mid_layer",
    "tops_sweatshirt": "mid_layer",
    "tops_hoodie": "mid_layer",
    "outerwear_vest": "mid_layer",
    "outerwear_cardigan": "mid_layer",

    # Outer layers (outermost structured layer)
    "outerwear_blazer": "outer_layer",
    "outerwear_jacket": "outer_layer",
    "outerwear_coat": "outer_layer",
    "outerwear_parka": "outer_layer",
    "outerwear_trench": "outer_layer",

    # Bottoms
    "bottoms_jeans": "bottom",
    "bottoms_trousers": "bottom",
    "bottoms_pants": "bottom",
    "bottoms_skirt": "bottom",
    "bottoms_shorts": "bottom",
    "bottoms_leggings": "bottom",
    "bottoms_culottes": "bottom",

    # Shoes
    "shoes_boots": "shoes",
    "shoes_sneakers": "shoes",
    "shoes_heels": "shoes",
    "shoes_flats": "shoes",
    "shoes_sandals": "shoes",
    "shoes_loafers": "shoes",
    "shoes_mules": "shoes",
    "footwear_boots": "shoes",
    "footwear_sneakers": "shoes",
    "footwear_heels": "shoes",
    "footwear_flats": "shoes",
    "footwear_sandals": "shoes",
    "footwear_loafers": "shoes",

    # Dresses / jumpsuits
    "dresses_mini": "dress",
    "dresses_midi": "dress",
    "dresses_maxi": "dress",
    "dresses_casual": "dress",
    "dresses_formal": "dress",
    "dresses_jumpsuit": "dress",

    # Accessories (unlimited)
    "accessories_belt": "accessory",
    "accessories_scarf": "accessory",
    "accessories_jewelry": "accessory",
    "accessories_hat": "accessory",
    "accessories_sunglasses": "accessory",
    "accessories_watch": "accessory",

    # Bags (generous limit)
    "bags_tote": "bag",
    "bags_crossbody": "bag",
    "bags_clutch": "bag",
    "bags_backpack": "bag",
}

# Fallback: category -> slot (when sub_category is missing/unknown)
CATEGORY_TO_SLOT = {
    "tops": "base_top",
    "outerwear": "outer_layer",
    "bottoms": "bottom",
    "shoes": "shoes",
    "footwear": "shoes",
    "dresses": "dress",
    "accessories": "accessory",
    "bags": "bag",
    "bag": "bag",
}

# Name keywords -> slot (last resort when sub_category is useless)
# Only checked when sub_category and category don't resolve
NAME_KEYWORDS_TO_SLOT = {
    "mid_layer": ["vest", "cardigan", "sweater", "pullover", "hoodie", "sweatshirt"],
    "outer_layer": ["blazer", "jacket", "coat", "parka", "trench"],
    "base_top": ["t-shirt", "tee", "tank", "blouse", "button-up", "button up",
                  "buttonup", "polo", "camisole", "henley", "bodysuit"],
    "bottom": ["jeans", "pants", "trousers", "skirt", "shorts", "leggings", "culottes"],
    "shoes": ["boots", "sneakers", "heels", "flats", "sandals", "loafers", "mules",
              "pumps", "oxfords", "slides"],
    "dress": ["dress", "jumpsuit", "romper"],
}

# Max items per slot
SLOT_MAX = {
    "base_top": 1,
    "mid_layer": 1,
    "outer_layer": 1,
    "bottom": 1,
    "shoes": 1,
    "dress": 1,
    "accessory": 99,
    "bag": 2,
}


def get_slot(item: dict) -> Optional[str]:
    """
    Determine the body slot for an item.

    Resolution order:
    1. sub_category exact match
    2. sub_category suffix match (handles unprefixed values like "cardigan")
    3. category fallback
    4. Item name keyword match (catches vests, cardigans, etc. with bad metadata)

    Returns slot string or None if truly unclassifiable.
    """
    sub_category = (
        item.get("sub_category")
        or item.get("styling_details", {}).get("sub_category", "")
    )

    if sub_category:
        sub_lower = sub_category.lower().strip()
        if sub_lower and sub_lower != "unknown":
            # Direct lookup
            if sub_lower in SUBCATEGORY_TO_SLOT:
                return SUBCATEGORY_TO_SLOT[sub_lower]

            # Suffix match (e.g., "cardigan" -> "tops_cardigan" -> mid_layer)
            for key, slot in SUBCATEGORY_TO_SLOT.items():
                if key.endswith(f"_{sub_lower}"):
                    return slot

    # Category fallback
    category = (
        item.get("category")
        or item.get("styling_details", {}).get("category", "")
    )
    if category:
        cat_lower = category.lower().strip()
        if cat_lower in CATEGORY_TO_SLOT:
            # Special case: category "tops" but name suggests mid-layer
            # Without this, a "vest" with category "tops" defaults to base_top
            if cat_lower == "tops":
                name_slot = _slot_from_name(item)
                if name_slot and name_slot != "base_top":
                    return name_slot
            return CATEGORY_TO_SLOT[cat_lower]

    # Last resort: check item name
    return _slot_from_name(item)


def _slot_from_name(item: dict) -> Optional[str]:
    """Infer slot from item name keywords."""
    name = (
        item.get("name")
        or item.get("styling_details", {}).get("name", "")
    )
    if not name:
        return None

    name_lower = name.lower()
    for slot, keywords in NAME_KEYWORDS_TO_SLOT.items():
        if any(kw in name_lower for kw in keywords):
            return slot

    return None


def validate_outfit(items: List[dict]) -> Tuple[bool, Optional[str]]:
    """
    Validate an outfit's physical plausibility.

    Args:
        items: List of item dicts. Each should have at minimum 'name'
               and ideally 'category' and 'sub_category'.

    Returns:
        (is_valid, rejection_reason) — reason is None if valid.
    """
    if not items or len(items) < 2:
        return True, None  # Can't validate a single item

    slot_counts: Dict[str, int] = {}
    slot_items: Dict[str, List[str]] = {}  # For readable error messages
    sub_categories_seen: Dict[str, str] = {}  # sub_cat -> item name

    for item in items:
        slot = get_slot(item)
        item_name = (
            item.get("name")
            or item.get("styling_details", {}).get("name", "unknown")
        )

        if slot:
            slot_counts[slot] = slot_counts.get(slot, 0) + 1
            if slot not in slot_items:
                slot_items[slot] = []
            slot_items[slot].append(item_name)

        # Track sub_categories for duplicate detection
        sub_cat = (
            item.get("sub_category")
            or item.get("styling_details", {}).get("sub_category", "")
        )
        if sub_cat and sub_cat.lower() not in ("unknown", ""):
            sc_lower = sub_cat.lower().strip()
            if sc_lower in sub_categories_seen:
                return (
                    False,
                    f"Duplicate type: '{item_name}' and '{sub_categories_seen[sc_lower]}' "
                    f"are both {sc_lower}"
                )
            sub_categories_seen[sc_lower] = item_name

    # Check slot max occupancy
    for slot, count in slot_counts.items():
        max_allowed = SLOT_MAX.get(slot, 1)
        if count > max_allowed:
            items_str = " + ".join(slot_items[slot])
            return (
                False,
                f"Too many items in '{slot}' slot: {items_str} ({count}, max {max_allowed})"
            )

    # Dress + bottom is invalid
    if slot_counts.get("dress", 0) > 0 and slot_counts.get("bottom", 0) > 0:
        return False, "Dress/jumpsuit worn with separate bottom"

    return True, None


def validate_outfit_detailed(items: List[dict]) -> dict:
    """
    Like validate_outfit but returns full diagnostic info for eval reports.
    """
    is_valid, reason = validate_outfit(items)

    slot_assignments = []
    for item in items:
        slot = get_slot(item)
        name = (
            item.get("name")
            or item.get("styling_details", {}).get("name", "unknown")
        )
        sub_cat = (
            item.get("sub_category")
            or item.get("styling_details", {}).get("sub_category", "")
        )
        category = (
            item.get("category")
            or item.get("styling_details", {}).get("category", "")
        )
        slot_assignments.append({
            "name": name,
            "category": category,
            "sub_category": sub_cat,
            "slot": slot or "unassigned",
        })

    return {
        "is_valid": is_valid,
        "reason": reason,
        "slot_assignments": slot_assignments,
    }
