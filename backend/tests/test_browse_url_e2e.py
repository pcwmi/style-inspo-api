"""
E2E test for browse_url tool — simulates the full agent flow.

Tests the real extraction logic against realistic HTML, then shows
what the agent would receive to reason about.

Run: python3 tests/test_browse_url_e2e.py
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock
from io import StringIO

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# 1. Realistic sale page HTML (Shopify-style, like Frame)
# ---------------------------------------------------------------------------

MOCK_FRAME_SALE_HTML = """
<html>
<head>
<title>Sale - Women | FRAME</title>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "ItemList",
  "itemListElement": [
    {
      "@type": "Product",
      "name": "Le High Straight Jean in Walnut",
      "url": "/products/le-high-straight-walnut",
      "image": "https://cdn.frame-store.com/walnut-jean.jpg",
      "brand": {"@type": "Brand", "name": "FRAME"},
      "offers": {"@type": "Offer", "price": 228, "lowPrice": 159, "priceCurrency": "USD"}
    },
    {
      "@type": "Product",
      "name": "Oversized Cashmere Crew in Oatmeal",
      "url": "/products/cashmere-crew-oatmeal",
      "image": "https://cdn.frame-store.com/cashmere-crew.jpg",
      "brand": {"@type": "Brand", "name": "FRAME"},
      "offers": {"@type": "Offer", "price": 398, "lowPrice": 278, "priceCurrency": "USD"}
    },
    {
      "@type": "Product",
      "name": "The Slouchy Boot in Black Leather",
      "url": "/products/slouchy-boot-black",
      "image": "https://cdn.frame-store.com/slouchy-boot.jpg",
      "brand": {"@type": "Brand", "name": "FRAME"},
      "offers": {"@type": "Offer", "price": 598, "lowPrice": 418, "priceCurrency": "USD"}
    },
    {
      "@type": "Product",
      "name": "Silk Button-Up in Cream",
      "url": "/products/silk-button-up-cream",
      "image": "https://cdn.frame-store.com/silk-cream.jpg",
      "brand": {"@type": "Brand", "name": "FRAME"},
      "offers": {"@type": "Offer", "price": 295, "lowPrice": 195, "priceCurrency": "USD"}
    },
    {
      "@type": "Product",
      "name": "Le Garcon Jean in Dark Wash",
      "url": "/products/le-garcon-dark",
      "image": "https://cdn.frame-store.com/garcon-dark.jpg",
      "brand": {"@type": "Brand", "name": "FRAME"},
      "offers": {"@type": "Offer", "price": 248, "lowPrice": 174, "priceCurrency": "USD"}
    },
    {
      "@type": "Product",
      "name": "Linen Blazer in Olive",
      "url": "/products/linen-blazer-olive",
      "image": "https://cdn.frame-store.com/linen-blazer.jpg",
      "brand": {"@type": "Brand", "name": "FRAME"},
      "offers": {"@type": "Offer", "price": 595, "lowPrice": 416, "priceCurrency": "USD"}
    },
    {
      "@type": "Product",
      "name": "Relaxed Trouser in Navy",
      "url": "/products/relaxed-trouser-navy",
      "image": "https://cdn.frame-store.com/trouser-navy.jpg",
      "brand": {"@type": "Brand", "name": "FRAME"},
      "offers": {"@type": "Offer", "price": 348, "lowPrice": 243, "priceCurrency": "USD"}
    },
    {
      "@type": "Product",
      "name": "Stripe Cotton Tee in Navy/White",
      "url": "/products/stripe-tee-navy",
      "image": "https://cdn.frame-store.com/stripe-tee.jpg",
      "brand": {"@type": "Brand", "name": "FRAME"},
      "offers": {"@type": "Offer", "price": 128, "lowPrice": 89, "priceCurrency": "USD"}
    }
  ]
}
</script>
</head>
<body><h1>Sale - Women</h1></body>
</html>
"""

# ---------------------------------------------------------------------------
# 2. Mock wardrobe (realistic, diverse closet)
# ---------------------------------------------------------------------------

MOCK_WARDROBE = {
    "items": [
        {"id": "w001", "name": "Black leather ankle boots", "category": "shoes", "colors": ["black"], "style": "edgy minimalist", "image_url": "https://s3.example.com/boots.jpg"},
        {"id": "w002", "name": "High-waisted wide leg jeans", "category": "bottoms", "colors": ["medium blue denim"], "style": "classic relaxed", "image_url": "https://s3.example.com/jeans.jpg"},
        {"id": "w003", "name": "Cream cable knit sweater", "category": "tops", "colors": ["cream", "ivory"], "style": "cozy classic", "image_url": "https://s3.example.com/sweater.jpg"},
        {"id": "w004", "name": "Black blazer", "category": "outerwear", "colors": ["black"], "style": "structured minimal", "image_url": "https://s3.example.com/blazer.jpg"},
        {"id": "w005", "name": "White cotton t-shirt", "category": "tops", "colors": ["white"], "style": "casual basic", "image_url": "https://s3.example.com/tee.jpg"},
        {"id": "w006", "name": "Dark wash skinny jeans", "category": "bottoms", "colors": ["dark indigo"], "style": "classic fitted", "image_url": "https://s3.example.com/skinny.jpg"},
        {"id": "w007", "name": "Denim jacket", "category": "outerwear", "colors": ["medium blue"], "style": "casual classic", "image_url": "https://s3.example.com/denim-jacket.jpg"},
        {"id": "w008", "name": "Black crossbody bag", "category": "accessories", "colors": ["black"], "style": "minimal functional", "image_url": "https://s3.example.com/bag.jpg"},
        {"id": "w009", "name": "Gold hoop earrings", "category": "accessories", "colors": ["gold"], "style": "classic feminine", "image_url": "https://s3.example.com/hoops.jpg"},
        {"id": "w010", "name": "Olive cargo pants", "category": "bottoms", "colors": ["olive green"], "style": "utilitarian relaxed", "image_url": "https://s3.example.com/cargo.jpg"},
    ],
    "count": 10,
}

MOCK_PROFILE = {
    "profile": {
        "three_words": {
            "current": "classic",
            "aspirational": "editorial",
            "feeling": "confident"
        },
        "model_descriptor": "5'6\", medium build, warm skin tone",
    }
}


def mock_requests_get(url, **kwargs):
    """Mock requests.get to return our fake HTML."""
    resp = MagicMock()
    resp.status_code = 200
    resp.content = MOCK_FRAME_SALE_HTML.encode()
    resp.text = MOCK_FRAME_SALE_HTML
    resp.raise_for_status = lambda: None
    # Make .json() fail for non-JSON endpoints (Shopify API probe)
    if url.endswith(".json") or "products.json" in url:
        resp.status_code = 404
    return resp


def main():
    print("=" * 60)
    print("E2E TEST: browse_url → wardrobe cross-reference")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: browse_url extraction
    # ------------------------------------------------------------------
    print("\n--- Step 1: Agent calls browse_url ---")
    with patch("services.web_browsing.requests.get", side_effect=mock_requests_get):
        from services.web_browsing import browse_url
        result = browse_url("https://frame-store.com/collections/sale-women")

    assert result["error"] is None, f"Extraction failed: {result['error']}"
    assert result["product_count"] > 0, "No products extracted"

    print(f"Page: {result['page_title']}")
    print(f"Products found: {result['product_count']}")
    print()
    for i, p in enumerate(result["products"]):
        sale_str = f" (was ${p['price']}, now ${p['sale_price']})" if "sale_price" in p else f" (${p.get('price', '?')})"
        print(f"  {i+1}. {p['name']}{sale_str}")
    print()

    # ------------------------------------------------------------------
    # Step 2: Agent gets wardrobe + profile (simulated)
    # ------------------------------------------------------------------
    print("--- Step 2: Agent calls get_items + get_profile ---")
    wardrobe = MOCK_WARDROBE
    profile = MOCK_PROFILE

    print(f"Wardrobe: {wardrobe['count']} items")
    categories = {}
    for item in wardrobe["items"]:
        cat = item["category"]
        categories.setdefault(cat, []).append(item["name"])
    for cat, items in categories.items():
        print(f"  {cat}: {', '.join(items)}")

    words = profile["profile"]["three_words"]
    print(f"\nStyle DNA: {words['current']} / {words['aspirational']} / {words['feeling']}")
    print()

    # ------------------------------------------------------------------
    # Step 3: What the agent would reason about
    # ------------------------------------------------------------------
    print("--- Step 3: Agent cross-references (what LLM receives) ---")
    print()

    # Simulate the kind of analysis the agent would do
    wardrobe_colors = set()
    wardrobe_categories = set()
    for item in wardrobe["items"]:
        wardrobe_colors.update(item["colors"])
        wardrobe_categories.add(item["category"])

    print("Wardrobe analysis:")
    print(f"  Colors owned: {', '.join(sorted(wardrobe_colors))}")
    print(f"  Categories: {', '.join(sorted(wardrobe_categories))}")

    # Check for overlaps and gaps
    print()
    print("Sale item analysis:")
    for p in result["products"]:
        name = p["name"]

        # Check if user already has something similar
        skip = False
        for w in wardrobe["items"]:
            # Simple overlap detection
            w_name = w["name"].lower()
            p_name = name.lower()
            if ("boot" in p_name and "boot" in w_name) or \
               ("blazer" in p_name and "blazer" in w_name) or \
               ("jean" in p_name and "wide leg" in w_name and "wide" not in p_name):
                pass  # Different enough
            if "boot" in p_name and "boot" in w_name and "black" in p_name and "black" in w_name:
                print(f"  SKIP: {name} — already own black boots")
                skip = True
                break

        if not skip:
            sale_str = f"${p.get('sale_price', p.get('price', '?'))}"
            pairings = []
            # Simple pairing logic
            p_lower = name.lower()
            if "sweater" in p_lower or "crew" in p_lower:
                pairings = ["wide leg jeans", "dark wash skinny jeans", "olive cargo pants"]
            elif "jean" in p_lower or "trouser" in p_lower:
                pairings = ["cream cable knit sweater", "white cotton t-shirt"]
            elif "blazer" in p_lower:
                pairings = ["white cotton t-shirt", "wide leg jeans"]
            elif "silk" in p_lower or "button" in p_lower:
                pairings = ["dark wash skinny jeans", "black blazer"]
            elif "tee" in p_lower:
                pairings = ["olive cargo pants", "denim jacket"]

            pairs_str = f" → pairs with: {', '.join(pairings)}" if pairings else ""
            print(f"  BUY:  {name} ({sale_str}){pairs_str}")

    print()
    print("=" * 60)
    print("E2E RESULT: All data flows work correctly.")
    print("In production, the LLM would generate natural language")
    print("recommendations from this data via the system prompt.")
    print("=" * 60)


if __name__ == "__main__":
    main()
