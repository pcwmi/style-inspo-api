#!/usr/bin/env python3
"""
G8 (GUARD): garment image-enhancement routing.

The collage pipeline studio-ifies garments via fal.ai but deliberately skips
shoes/jewelry (generative models distort logos/small details). This locks that
routing rule so a refactor can't silently start enhancing shoes (or stop
enhancing tops). Pure logic test — no creds, no network.

Run:
    python tests/sms_eval/scripts/test_image_enhance_routing.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from services.bg_removal import ENHANCE_CATEGORIES  # noqa: E402


def _should_enhance(category="", sub_category="", item_name=""):
    """Mirror of the routing predicate in remove_background_enhanced()."""
    cat = (category or "").lower()
    sub = (sub_category or "").lower()
    name = (item_name or "").lower()
    return cat in ENHANCE_CATEGORIES or "scarf" in sub or "scarf" in name


CASES = [
    # (category, sub_category, item_name, expected_enhance)
    ("tops", "", "white poplin shirt", True),
    ("bottoms", "", "wide-leg jeans", True),
    ("dresses", "", "slip dress", True),
    ("outerwear", "", "chore jacket", True),
    ("accessories", "scarf", "silk scarf", True),   # scarves enhance
    ("shoes", "", "white cowboy boots", False),     # shoes never enhance
    ("shoes", "", "nike cortez", False),
    ("accessories", "bag", "black hobo bag", False),
    ("accessories", "jewelry", "gold pendant", False),
]


def main():
    failures = 0
    for cat, sub, name, expected in CASES:
        got = _should_enhance(cat, sub, name)
        ok = got == expected
        failures += not ok
        print(f"  [{'OK' if ok else 'XX'}] {cat:12s} {name:22s} enhance={got} want={expected}")
    print(f"\nG8 routing: {len(CASES) - failures}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
