"""
Web Browsing Service - Extract product listings from sale/collection pages.

Used by the styling agent's browse_url tool. Handles:
1. Shopify collection pages (JSON in page source)
2. JSON-LD structured data (Schema.org)
3. Generic HTML product grids (fallback)

Returns structured product data the agent can reason about.
"""

import json
import re
import logging
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
        "Mobile/15E148 Safari/604.1"
    )
}

MAX_PRODUCTS = 40  # Cap to keep token count reasonable


def browse_url(url: str) -> dict:
    """
    Fetch a URL and extract product listings.

    Returns:
        {
            "url": str,
            "page_title": str,
            "products": [{"name", "price", "sale_price", "image_url", "url", "brand"}],
            "product_count": int,
            "error": str or None
        }
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.Timeout:
        return {"url": url, "products": [], "product_count": 0, "error": "Page took too long to load"}
    except requests.RequestException as e:
        return {"url": url, "products": [], "product_count": 0, "error": f"Could not fetch page: {e}"}

    soup = BeautifulSoup(resp.content, "html.parser")
    page_title = _get_page_title(soup)
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    # Try extraction methods in order of reliability
    products = _try_shopify_api(url, base_url)

    if not products:
        products = _extract_shopify_json(resp.text, base_url)

    if not products:
        products = _extract_json_ld(soup, base_url)

    if not products:
        products = _extract_html_products(soup, url, base_url)

    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for p in products:
        key = p.get("url") or p.get("name", "")
        if key not in seen_urls:
            seen_urls.add(key)
            unique.append(p)
    products = unique[:MAX_PRODUCTS]

    return {
        "url": url,
        "page_title": page_title,
        "products": products,
        "product_count": len(products),
        "error": None,
    }


# ---------------------------------------------------------------------------
# Extraction strategies
# ---------------------------------------------------------------------------

def _try_shopify_api(url: str, base_url: str) -> list[dict]:
    """Try the Shopify collections JSON API endpoint (most reliable for Shopify stores)."""
    # Shopify stores expose /collections/{handle}/products.json
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    if "/collections/" not in path:
        return []

    api_url = f"{base_url}{path}/products.json?limit={MAX_PRODUCTS}"
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        items = data.get("products", [])
        products = []
        for item in items:
            product = _parse_shopify_product(item, base_url)
            if product:
                products.append(product)
        if products:
            logger.info(f"Shopify API extracted {len(products)} products from {api_url}")
        return products
    except Exception:
        return []


def _extract_shopify_json(html: str, base_url: str) -> list[dict]:
    """Extract products from Shopify's embedded JSON in page source."""
    products = []

    # Match both quoted and unquoted key patterns:
    #   "products": [...]  or  var products = [...]
    patterns = [
        r'["\']products["\']\s*:\s*(\[.+?\])\s*[,;}]',
        r'var\s+products\s*=\s*(\[.+?\])\s*;',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    for item in data:
                        product = _parse_shopify_product(item, base_url)
                        if product:
                            products.append(product)
                if products:
                    return products
            except (json.JSONDecodeError, TypeError):
                continue

    # Look for product JSON in <script type="application/json"> tags
    for script in _find_script_tags(html):
        try:
            data = json.loads(script)
        except (json.JSONDecodeError, TypeError):
            continue

        # Handle array of products
        if isinstance(data, list):
            for item in data:
                product = _parse_shopify_product(item, base_url)
                if product:
                    products.append(product)
            if products:
                return products

        # Handle object with products key
        if isinstance(data, dict):
            for key in ("products", "items", "collection"):
                items = data.get(key)
                if isinstance(items, list):
                    for item in items:
                        product = _parse_shopify_product(item, base_url)
                        if product:
                            products.append(product)
                    if products:
                        return products

    return products


def _parse_shopify_product(item: dict, base_url: str) -> Optional[dict]:
    """Parse a single product from Shopify JSON."""
    if not isinstance(item, dict):
        return None

    name = item.get("title") or item.get("name")
    if not name:
        return None

    # Price handling - Shopify stores price in cents sometimes
    price = _extract_price_from_json(item)
    sale_price = None

    # Check for compare_at_price (original price before sale)
    compare_price = item.get("compare_at_price") or item.get("compare_at_price_max")
    if compare_price:
        compare_val = _normalize_price(compare_price)
        if compare_val and price and compare_val > price:
            sale_price = price
            price = compare_val

    # Variants may have better price info
    variants = item.get("variants", [])
    if variants and isinstance(variants, list) and isinstance(variants[0], dict):
        v = variants[0]
        v_price = _normalize_price(v.get("price"))
        v_compare = _normalize_price(v.get("compare_at_price"))
        if v_price:
            if v_compare and v_compare > v_price:
                price = v_compare
                sale_price = v_price
            elif not price:
                price = v_price

    # Image
    image_url = None
    featured_image = item.get("featured_image") or item.get("image")
    if isinstance(featured_image, str):
        image_url = featured_image
    elif isinstance(featured_image, dict):
        image_url = featured_image.get("src") or featured_image.get("url")
    images = item.get("images", [])
    if not image_url and images:
        if isinstance(images[0], str):
            image_url = images[0]
        elif isinstance(images[0], dict):
            image_url = images[0].get("src") or images[0].get("url")

    if image_url and image_url.startswith("//"):
        image_url = "https:" + image_url

    # URL
    product_url = item.get("url") or item.get("handle")
    if product_url and not product_url.startswith("http"):
        if product_url.startswith("/"):
            product_url = base_url + product_url
        else:
            product_url = f"{base_url}/products/{product_url}"

    return _clean_product({
        "name": name,
        "price": price,
        "sale_price": sale_price,
        "image_url": image_url,
        "url": product_url,
        "brand": item.get("vendor") or item.get("brand"),
    })


def _extract_json_ld(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Extract products from JSON-LD structured data."""
    products = []

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue

        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # ItemList with itemListElement
            if data.get("@type") == "ItemList":
                items = data.get("itemListElement", [])
            # Single product
            elif data.get("@type") == "Product":
                items = [data]
            # Graph
            elif "@graph" in data:
                items = data["@graph"]

        for item in items:
            if not isinstance(item, dict):
                continue
            # Handle ItemList entries that wrap a product
            actual = item.get("item", item)
            if not isinstance(actual, dict):
                continue
            if actual.get("@type") not in ("Product", None):
                if actual.get("@type") != "Product":
                    continue

            name = actual.get("name")
            if not name:
                continue

            # Price from offers
            price = None
            sale_price = None
            offers = actual.get("offers")
            if isinstance(offers, dict):
                price = _normalize_price(offers.get("price") or offers.get("highPrice"))
                low = _normalize_price(offers.get("lowPrice"))
                if low and price and low < price:
                    sale_price = low
            elif isinstance(offers, list) and offers:
                price = _normalize_price(offers[0].get("price"))

            # Image
            image_url = actual.get("image")
            if isinstance(image_url, list):
                image_url = image_url[0] if image_url else None
            if isinstance(image_url, dict):
                image_url = image_url.get("url")

            # URL
            product_url = actual.get("url") or item.get("url")
            if product_url and not product_url.startswith("http"):
                product_url = urljoin(base_url, product_url)

            products.append(_clean_product({
                "name": name,
                "price": price,
                "sale_price": sale_price,
                "image_url": image_url,
                "url": product_url,
                "brand": _get_brand_from_json_ld(actual),
            }))

    return products


def _extract_html_products(soup: BeautifulSoup, page_url: str, base_url: str) -> list[dict]:
    """Fallback: extract products from HTML structure."""
    products = []

    # Common product card selectors
    card_selectors = [
        "[class*='product-card']",
        "[class*='product-item']",
        "[class*='product-grid'] > *",
        "[class*='collection-product']",
        "[data-product]",
        ".grid-item",
        ".product",
    ]

    cards = []
    for selector in card_selectors:
        cards = soup.select(selector)
        if len(cards) >= 2:  # Found a grid
            break

    if not cards:
        return products

    for card in cards:
        name = None
        price = None
        sale_price = None
        image_url = None
        product_url = None

        # Name: look for heading or link text
        for tag in card.find_all(["h2", "h3", "h4", "a", "span", "p"]):
            text = tag.get_text(strip=True)
            classes = " ".join(tag.get("class", []))
            if any(kw in classes for kw in ["title", "name", "product-title", "product-name"]):
                name = text
                break
            # Links with meaningful text (not "Add to cart" etc.)
            if tag.name == "a" and len(text) > 3 and not any(skip in text.lower() for skip in ["cart", "add", "buy", "view"]):
                if not name:
                    name = text

        # Price: look for price elements
        price_els = card.select("[class*='price']")
        for el in price_els:
            text = el.get_text(strip=True)
            classes = " ".join(el.get("class", []))
            val = _parse_price_text(text)
            if val:
                if "compare" in classes or "original" in classes or "was" in classes or "regular" in classes:
                    price = val  # Original/compare price
                elif "sale" in classes or "special" in classes or "current" in classes:
                    sale_price = val
                else:
                    if not price:
                        price = val

        # If we only got one price and it's not a sale, just set it as price
        if sale_price and not price:
            price = sale_price
            sale_price = None

        # Image
        img = card.find("img")
        if img:
            image_url = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if image_url and image_url.startswith("//"):
                image_url = "https:" + image_url
            elif image_url and image_url.startswith("/"):
                image_url = base_url + image_url

        # URL
        link = card.find("a", href=True)
        if link:
            href = link["href"]
            if href.startswith("/"):
                product_url = base_url + href
            elif href.startswith("http"):
                product_url = href

        if name:
            products.append(_clean_product({
                "name": name,
                "price": price,
                "sale_price": sale_price,
                "image_url": image_url,
                "url": product_url,
                "brand": None,
            }))

    return products


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_script_tags(html: str) -> list[str]:
    """Extract contents of <script> tags that look like they contain product JSON."""
    results = []
    for match in re.finditer(r"<script[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE):
        content = match.group(1).strip()
        if not content or len(content) < 50:
            continue
        # Only consider scripts that look like JSON or contain product data
        if content.startswith(("{", "[")) or "product" in content.lower()[:200]:
            results.append(content)
    return results


def _get_page_title(soup: BeautifulSoup) -> str:
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def _get_brand_from_json_ld(item: dict) -> Optional[str]:
    brand = item.get("brand")
    if isinstance(brand, str):
        return brand
    if isinstance(brand, dict):
        return brand.get("name")
    return None


def _normalize_price(val) -> Optional[float]:
    """Convert various price representations to float."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        # Shopify sometimes stores price in cents
        if val > 10000:
            return val / 100.0
        return float(val)
    if isinstance(val, str):
        return _parse_price_text(val)
    return None


def _parse_price_text(text: str) -> Optional[float]:
    """Parse a price string like '$49.99' or '49,99 €' to float."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.,]", "", text)
    if not cleaned:
        return None
    # Handle European format: 49,99
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    # Handle thousand separators: 1,299.00
    elif "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_price_from_json(item: dict) -> Optional[float]:
    """Extract price from various JSON shapes."""
    for key in ("price", "price_min", "price_max"):
        val = item.get(key)
        if val is not None:
            p = _normalize_price(val)
            if p:
                return p
    return None


def _clean_product(p: dict) -> dict:
    """Remove None values and clean up a product dict."""
    return {k: v for k, v in p.items() if v is not None}
