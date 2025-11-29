"""
Product Extractor - Extract product images and metadata from URLs or screenshots
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, Tuple
from PIL import Image
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class ProductExtractor:
    """Extract product information from URLs or screenshots"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15'
        }

    def extract_from_url(self, url: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Extract product image and metadata from URL using multiple methods:
        1. Open Graph tags (primary)
        2. Schema.org/JSON-LD markup (fallback)
        3. Common e-commerce patterns (fallback)
        4. Page title and image selectors (fallback)

        Returns: (success, data, error_message)
        data = {
            'image_url': str,
            'title': str,
            'price': float or None,
            'brand': str or None
        }
        """
        try:
            # Fetch page
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try method 1: Open Graph tags
            og_image = soup.find('meta', property='og:image')
            og_title = soup.find('meta', property='og:title')
            og_price = soup.find('meta', property='og:price:amount')

            image_url = None
            title = None
            price = None

            if og_image:
                image_url = og_image.get('content')
            if og_title:
                title = og_title.get('content')
            if og_price:
                try:
                    price = float(og_price.get('content'))
                except (ValueError, TypeError):
                    pass

            # If Open Graph didn't work, try fallback methods
            if not image_url:
                # Try method 2: Schema.org/JSON-LD
                image_url = self._extract_image_from_schema(soup)
                
                # Try method 3: Common e-commerce image patterns
                if not image_url:
                    image_url = self._extract_image_from_selectors(soup)

            if not title:
                # Try h1 tag
                h1 = soup.find('h1')
                if h1:
                    title = h1.get_text(strip=True)
                # Fallback to page title
                if not title:
                    title_tag = soup.find('title')
                    if title_tag:
                        title = title_tag.get_text(strip=True)

            if not price:
                # Try extracting price from various patterns
                price = self._extract_price(soup)

            # Must have at least an image to proceed
            if not image_url:
                return False, None, "No product image found"

            # Ensure image URL is absolute
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            elif image_url.startswith('/'):
                from urllib.parse import urljoin
                image_url = urljoin(url, image_url)

            data = {
                'image_url': image_url,
                'title': title or 'Product',
                'price': price,
                'brand': self._extract_brand(soup, url),
                'source_url': url
            }

            return True, data, None

        except requests.Timeout:
            return False, None, "Request timed out"
        except requests.RequestException as e:
            return False, None, f"Network error: {str(e)}"
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            return False, None, "Could not extract product information"

    def _extract_image_from_schema(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract image from Schema.org/JSON-LD markup"""
        # Try JSON-LD script tags
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Handle Product schema
                    if data.get('@type') == 'Product' or 'Product' in str(data.get('@type', '')):
                        image = data.get('image')
                        if isinstance(image, str):
                            return image
                        elif isinstance(image, list) and len(image) > 0:
                            return image[0] if isinstance(image[0], str) else image[0].get('url')
                        elif isinstance(image, dict):
                            return image.get('url') or image.get('@id')
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue

        # Try schema.org itemprop
        schema_image = soup.find('img', {'itemprop': 'image'})
        if schema_image:
            return schema_image.get('src') or schema_image.get('data-src')

        return None

    def _extract_image_from_selectors(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product image using common e-commerce CSS selectors"""
        # Common patterns for product images
        selectors = [
            'img.product-image',
            'img[class*="product"]',
            'img[class*="main"]',
            'img[data-product-image]',
            '.product-image img',
            '.product-main-image img',
            '[data-testid*="product-image"] img',
            '[data-testid*="image"] img',
        ]

        for selector in selectors:
            try:
                img = soup.select_one(selector)
                if img:
                    src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                    if src and not src.startswith('data:'):  # Skip data URIs
                        return src
            except Exception:
                continue

        # Fallback: find largest image that looks like a product image
        images = soup.find_all('img')
        product_images = []
        for img in images:
            src = img.get('src') or img.get('data-src')
            if not src or src.startswith('data:'):
                continue
            # Check if it might be a product image (not a logo, icon, etc.)
            alt = (img.get('alt') or '').lower()
            classes = ' '.join(img.get('class', [])).lower()
            if any(keyword in alt or keyword in classes for keyword in ['product', 'item', 'main', 'hero']):
                # Prefer larger images (check width/height if available)
                width = img.get('width')
                if width:
                    try:
                        product_images.append((int(width), src))
                    except ValueError:
                        product_images.append((0, src))
                else:
                    product_images.append((0, src))

        if product_images:
            # Sort by width (largest first) and return the first one
            product_images.sort(reverse=True)
            return product_images[0][1]

        return None

    def _extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price from various patterns"""
        # Try schema.org price
        price_elem = soup.find('span', {'itemprop': 'price'})
        if price_elem:
            try:
                price_text = price_elem.get('content') or price_elem.get_text(strip=True)
                return self._parse_price(price_text)
            except (ValueError, AttributeError):
                pass

        # Try common price selectors
        price_selectors = [
            '.price',
            '[class*="price"]',
            '[data-price]',
            '[itemprop="price"]',
        ]

        for selector in price_selectors:
            try:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get('content') or price_elem.get('data-price') or price_elem.get_text(strip=True)
                    price = self._parse_price(price_text)
                    if price:
                        return price
            except Exception:
                continue

        return None

    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price string to float"""
        if not price_text:
            return None
        # Remove currency symbols and whitespace
        import re
        # Extract numbers and decimal point
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if price_match:
            try:
                return float(price_match.group())
            except ValueError:
                pass
        return None

    def _extract_brand(self, soup: BeautifulSoup, url: str = '') -> Optional[str]:
        """Attempt to extract brand name from page"""
        # Try Open Graph brand
        og_brand = soup.find('meta', property='og:brand')
        if og_brand:
            return og_brand.get('content')

        # Try schema.org markup
        schema_brand = soup.find('span', {'itemprop': 'brand'})
        if schema_brand:
            return schema_brand.get_text(strip=True)

        # Try extracting from URL domain (more reliable than title, so try this first)
        if url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = parsed.netloc
                
                if not domain:
                    # If netloc is empty, try to extract from path or full URL
                    logger.warning(f"Empty netloc for URL: {url}")
                else:
                    # Remove www. and common TLDs, get main brand name
                    domain = domain.replace('www.', '').split('.')[0]
                    
                    if domain:
                        # Handle hyphenated domains like "frame-store" -> "Frame" or "balzac-paris" -> "Balzac Paris"
                        if '-' in domain:
                            parts = domain.split('-')
                            # For multi-word brands, try to format properly
                            # "balzac-paris" -> "Balzac Paris"
                            # "frame-store" -> "Frame" (first part only, as store is generic)
                            if len(parts) > 1:
                                # Check if second part is generic (store, shop, com, etc.)
                                generic_suffixes = ['store', 'shop', 'com', 'net', 'org', 'co', 'io']
                                if parts[1].lower() in generic_suffixes:
                                    # Just use first part: "frame-store" -> "Frame"
                                    brand_part = parts[0]
                                    return brand_part.capitalize()
                                else:
                                    # Use both parts: "balzac-paris" -> "Balzac Paris"
                                    return ' '.join(p.capitalize() for p in parts)
                            else:
                                return parts[0].capitalize()
                        
                        # Handle camelCase domains: "jennikayne" -> "Jenni Kayne"
                        # Simple heuristic: split on case changes
                        import re
                        # Split on uppercase letters (but keep them)
                        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', domain)
                        if len(words) > 1:
                            # Multiple words detected: "jennikayne" -> ["jenni", "kayne"]
                            return ' '.join(w.capitalize() for w in words)
                        
                        # Handle known brand patterns that need special formatting
                        brand_mappings = {
                            'lebonmarche': 'Le Bon Marché',
                            'jennikayne': 'Jenni Kayne',
                        }
                        if domain.lower() in brand_mappings:
                            return brand_mappings[domain.lower()]
                        
                        # Capitalize first letter for simple domains
                        return domain.capitalize()
            except Exception as e:
                logger.error(f"Error extracting brand from URL {url}: {e}")
                # Continue to try title extraction as fallback
                pass

        # Try extracting from page title (fallback if domain extraction didn't work)
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            # Look for common patterns like "BRAND - Product" or "Product | BRAND"
            # Common separators: |, -, –, —
            for separator in [' | ', ' - ', ' – ', ' — ']:
                if separator in title_text:
                    parts = title_text.split(separator)
                    # Brand is usually AFTER the separator (parts[-1]), check that first
                    # Only check parts[0] if parts[-1] doesn't match criteria
                    for part in [parts[-1], parts[0]]:  # Check last part first
                        part_clean = part.strip()
                        # If it's short and looks like a brand name, use it
                        if len(part_clean) < 30 and not part_clean.lower().startswith(('shop', 'buy', 'product')):
                            return part_clean

        return None

    def download_image(self, image_url: str) -> Tuple[bool, Optional[Image.Image], Optional[str]]:
        """
        Download image from URL

        Returns: (success, PIL.Image, error_message)
        """
        try:
            response = requests.get(image_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            image = Image.open(BytesIO(response.content))
            return True, image, None

        except Exception as e:
            logger.error(f"Image download error: {str(e)}")
            return False, None, f"Could not download image: {str(e)}"
