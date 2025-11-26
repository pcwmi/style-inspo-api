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
        Extract product image and metadata from URL using Open Graph tags

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

            # Extract Open Graph tags
            og_image = soup.find('meta', property='og:image')
            og_title = soup.find('meta', property='og:title')
            og_price = soup.find('meta', property='og:price:amount')

            if not og_image:
                return False, None, "No product image found (no Open Graph tags)"

            data = {
                'image_url': og_image['content'],
                'title': og_title['content'] if og_title else None,
                'price': float(og_price['content']) if og_price else None,
                'brand': self._extract_brand(soup),
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

    def _extract_brand(self, soup: BeautifulSoup) -> Optional[str]:
        """Attempt to extract brand name from page"""
        # Try Open Graph brand
        og_brand = soup.find('meta', property='og:brand')
        if og_brand:
            return og_brand['content']

        # Try schema.org markup
        schema_brand = soup.find('span', {'itemprop': 'brand'})
        if schema_brand:
            return schema_brand.text.strip()

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
