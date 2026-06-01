"""Constrained edit detection for multi-turn outfit changes.

This module is deterministic. It gives the agent a scoped operation when the
user says variants of "only change X" so prior outfit pieces stay locked.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


EDIT_SCOPE_MARKERS = (
    "only",
    "just",
    "rest looks good",
    "everything else",
    "keep the rest",
    "keep everything",
    "swap",
    "change the",
    "different",
)

CATEGORY_KEYWORDS = {
    "outerwear": ("jacket", "coat", "blazer", "trench", "bomber", "cardigan", "outerwear"),
    "shoes": ("shoe", "shoes", "sneaker", "sneakers", "boot", "boots", "sandal", "sandals", "loafer", "loafers"),
    "bag": ("bag", "purse", "tote", "crossbody", "clutch"),
    "bottom": ("jeans", "pants", "trousers", "skirt", "shorts", "bottom"),
    "top": ("top", "shirt", "tee", "t-shirt", "sweater", "blouse", "tank", "cashmere"),
    "dress": ("dress",),
    "accessory": ("earring", "earrings", "necklace", "belt", "scarf", "hat", "bracelet", "accessory"),
}

LABEL_PATTERNS = (
    (re.compile(r"\bday\s*([1-9])\b", re.IGNORECASE), lambda match: f"Day {match.group(1)}"),
    (re.compile(r"\btravel\b", re.IGNORECASE), lambda match: "travel"),
    (re.compile(r"\bdinner\b", re.IGNORECASE), lambda match: "dinner"),
    (re.compile(r"\bhike|hiking\b", re.IGNORECASE), lambda match: "hike"),
)


def infer_item_category(item_name: str, fallback: str = "") -> str:
    """Infer a broad category from an item name when metadata is missing."""
    text = f"{item_name} {fallback}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return fallback or "item"


def infer_outfit_label(text: Optional[str], fallback_index: int) -> str:
    """Extract an SMS-friendly outfit label from styling text."""
    normalized = text or ""
    day_match = re.search(r"\bday\s*([1-9])\b", normalized, re.IGNORECASE)
    if day_match:
        return f"Day {day_match.group(1)}"
    if re.search(r"\bdinner\b", normalized, re.IGNORECASE):
        return "Dinner"
    if re.search(r"\btravel\b", normalized, re.IGNORECASE):
        return "Travel"
    if re.search(r"\bhike|hiking\b", normalized, re.IGNORECASE):
        return "Hike"
    return f"Outfit {fallback_index}"


def _detect_target_categories(message: str) -> List[str]:
    text = message.lower()
    return [
        category
        for category, keywords in CATEGORY_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]


def _find_target_outfit(message: str, active_pack: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    outfits = active_pack.get("outfits") or []
    if not outfits:
        return None

    text = message.lower()
    for pattern, label_factory in LABEL_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue
        label = label_factory(match).lower()
        for outfit in outfits:
            outfit_label = (outfit.get("label") or "").lower()
            if outfit_label == label or label in outfit_label or outfit_label in label:
                return outfit

    if len(outfits) == 1:
        return outfits[0]

    if "first" in text:
        return outfits[0]
    if "last" in text:
        return outfits[-1]

    return None


def build_constrained_edit_hint(message: str, active_pack: Dict[str, Any]) -> str:
    """Build a scoped edit instruction for the agent, or return empty string."""
    if not active_pack:
        return ""

    text = message.lower()
    if not any(marker in text for marker in EDIT_SCOPE_MARKERS):
        return ""

    target_categories = _detect_target_categories(message)
    if not target_categories:
        return ""

    outfit = _find_target_outfit(message, active_pack)
    if not outfit:
        labels = [o.get("label") for o in active_pack.get("outfits", []) if o.get("label")]
        if not labels:
            return ""
        return (
            "Constrained edit context: the user appears to be asking for a narrow edit, "
            f"but the target outfit is ambiguous. Ask which outfit they mean from: {', '.join(labels)}. "
            "Do not rebuild the full pack until they clarify."
        )

    items = outfit.get("items") or []
    locked_names = []
    editable_names = []
    for item in items:
        name = item.get("name") or ""
        category = infer_item_category(name, item.get("category", ""))
        if category in target_categories:
            editable_names.append(name)
        else:
            locked_names.append(name)

    if not locked_names:
        return ""

    label = outfit.get("label") or "the selected outfit"
    editable = ", ".join(target_categories)
    locked = ", ".join(locked_names)
    replace = ", ".join(editable_names) if editable_names else editable

    return (
        f"Constrained edit context: the user asked for a narrow {editable} change on {label}. "
        f"Only replace: {replace}. Keep these exact items locked: {locked}. "
        "Do not rewrite other days or rebuild the full pack unless the user explicitly asks for a broader change."
    )
