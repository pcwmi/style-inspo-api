"""
Outfit Photo Item Extraction Service
Identifies individual clothing items in outfit photos using GPT-4o vision,
crops them with bounding boxes, and removes backgrounds using rembg.
"""

import os
import json
import base64
import time
import logging
from io import BytesIO
from typing import Dict, List, Optional, Tuple

from PIL import Image
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# Register HEIF/HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


class OutfitItemExtractor:
    """Extracts individual clothing items from outfit photos."""

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def _encode_image(self, image_bytes: bytes) -> str:
        """Convert image bytes to base64 for GPT-4o vision API."""
        img = Image.open(BytesIO(image_bytes))

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def identify_items(self, image_bytes: bytes) -> List[Dict]:
        """
        Send outfit photo to GPT-4o vision to identify all clothing items
        with bounding box coordinates.

        Returns list of dicts with: name, category, sub_category, colors,
        description, confidence, bbox_pct [x1%, y1%, x2%, y2%]
        """
        start = time.time()
        base64_image = self._encode_image(image_bytes)

        prompt = """Analyze this photo and identify EVERY distinct clothing item and accessory visible.

For each item, provide a bounding box as percentage coordinates (0-100) of the image dimensions.

Return STRICT JSON:
{
  "items": [
    {
      "name": "Black leather ankle boots",
      "category": "footwear",
      "sub_category": "shoes_boots",
      "colors": ["black"],
      "description": "Pointed-toe leather ankle boots with low heel",
      "confidence": 0.95,
      "bbox_pct": [60, 75, 85, 100]
    }
  ]
}

Rules:
1. Include ALL visible items: shoes, bags, jewelry, hats, belts, scarves
2. bbox_pct uses percentage coordinates: [left%, top%, right%, bottom%] from top-left corner
3. Don't include items with confidence < 0.5
4. Focus on PHYSICAL attributes you can see - color, material, cut, silhouette
5. category must be one of: tops, bottoms, dresses, outerwear, footwear, accessories, bags
6. sub_category format examples: tops_blouse, tops_sweater, bottoms_jeans, bottoms_skirt, shoes_boots, shoes_sneakers, dress_midi, outerwear_jacket, accessories_belt, accessories_necklace, bags_crossbody
7. Be precise with bounding boxes - they should tightly frame each item
8. If a person is wearing the outfit, focus on the clothing items, not the person"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1500
        )

        result = json.loads(response.choices[0].message.content)
        items = result.get("items", [])

        elapsed = time.time() - start
        logger.info(f"Identified {len(items)} items in {elapsed:.1f}s")

        return items

    def extract_item(
        self,
        source_image: Image.Image,
        bbox_pct: List[float],
        item_name: str,
        remove_bg: bool = True
    ) -> bytes:
        """
        Crop a single item from the source image using percentage-based
        bounding box coordinates, then optionally remove background.

        Args:
            source_image: PIL Image of the full outfit photo
            bbox_pct: [left%, top%, right%, bottom%] percentage coordinates
            item_name: Name of item (for logging)
            remove_bg: Whether to run rembg background removal

        Returns:
            PNG bytes of the extracted item
        """
        start = time.time()
        width, height = source_image.size

        # Convert percentage coords to pixels
        x1 = int(bbox_pct[0] / 100 * width)
        y1 = int(bbox_pct[1] / 100 * height)
        x2 = int(bbox_pct[2] / 100 * width)
        y2 = int(bbox_pct[3] / 100 * height)

        # Add 15% padding on all sides (prevents cutting off edges)
        pad_x = int((x2 - x1) * 0.15)
        pad_y = int((y2 - y1) * 0.15)
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(width, x2 + pad_x)
        y2 = min(height, y2 + pad_y)

        # Crop
        cropped = source_image.crop((x1, y1, x2, y2))

        if remove_bg:
            try:
                from rembg import remove
                # Convert to bytes for rembg
                buf = BytesIO()
                cropped.save(buf, format="PNG")
                buf.seek(0)
                result_bytes = remove(buf.read())
                elapsed = time.time() - start
                logger.info(f"Extracted '{item_name}' with bg removal in {elapsed:.1f}s")
                return result_bytes
            except Exception as e:
                logger.warning(f"Background removal failed for '{item_name}': {e}. Using cropped image.")

        # Fallback: return cropped image without bg removal
        buf = BytesIO()
        cropped.save(buf, format="PNG")
        elapsed = time.time() - start
        logger.info(f"Extracted '{item_name}' (no bg removal) in {elapsed:.1f}s")
        return buf.getvalue()

    def _bboxes_overlap(self, a: List[float], b: List[float]) -> bool:
        """Check if two percentage-based bounding boxes intersect."""
        return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]

    def _build_reconstruction_prompt(self, analysis: Dict, item_info: Dict, all_items: Optional[List[Dict]] = None) -> str:
        """Build prompt for garment reconstruction entirely from item_info.

        Uses identification-stage data only (from full photo, pre-crop).
        The cropped reference image provides visual details (fabric, pattern, color).
        Analysis data is ignored — it's polluted by overlapping items in the crop.
        """
        name = item_info.get("name", "clothing item")
        description = item_info.get("description", "")
        colors = item_info.get("colors", [])
        color_str = ", ".join(colors) if isinstance(colors, list) else str(colors)

        prompt = (
            f"Product photo of a complete {name}. "
            f"Show the ENTIRE garment from top to bottom, nothing cropped or cut off. "
        )

        if description:
            prompt += f"{description}. "

        if color_str:
            prompt += f"Color: {color_str}. "

        prompt += (
            "Show ONLY this single garment. Do NOT include any other clothing items, "
            "accessories, belts, scarves, bags, or jewelry. "
            "Clean white background. "
            "Flat-lay or ghost mannequin style. "
            "No model, no person, no hanger visible. "
            "Photorealistic product photography. "
            "Preserve the EXACT colors and pattern visible in the reference image. "
            "Do NOT add logos, patterns, or details not present in the reference."
        )

        # Flag overlapping items that are smaller (accessories draped on top)
        if all_items and item_info.get("bbox_pct"):
            bbox = item_info["bbox_pct"]
            bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            for other in all_items:
                if other is item_info:
                    continue
                other_bbox = other.get("bbox_pct")
                if not other_bbox:
                    continue
                other_area = (other_bbox[2] - other_bbox[0]) * (other_bbox[3] - other_bbox[1])
                if other_area < bbox_area and self._bboxes_overlap(bbox, other_bbox):
                    other_name = other.get("name", "item")
                    other_cat = other.get("category", "item")
                    prompt += (
                        f" Ignore the {other_name} visible in the reference image"
                        f" — it is a separate {other_cat} draped on top, NOT part of this garment."
                        f" Do not include it."
                    )

        return prompt

    def reconstruct_garment(
        self,
        item_bytes: bytes,
        analysis: Dict,
        item_info: Dict,
        quality: str = "medium",
        all_items: Optional[List[Dict]] = None,
    ) -> Optional[bytes]:
        """
        Reconstruct a complete garment image from a partial/occluded crop.

        Uses gpt-image-1 images.edit() with the cropped image as visual reference
        and analysis metadata to generate a complete product-style photo.

        Returns PNG bytes of reconstructed garment, or None on failure.
        """
        start = time.time()
        item_name = analysis.get("name", item_info.get("name", "item"))

        try:
            # Composite RGBA onto white background (transparent bg may confuse model)
            img = Image.open(BytesIO(item_bytes))
            if img.mode == 'RGBA':
                white_bg = Image.new('RGB', img.size, (255, 255, 255))
                white_bg.paste(img, mask=img.split()[3])
                buf = BytesIO()
                white_bg.save(buf, format='PNG')
                input_bytes = buf.getvalue()
            else:
                input_bytes = item_bytes

            prompt = self._build_reconstruction_prompt(analysis, item_info, all_items=all_items)

            image_file = BytesIO(input_bytes)
            image_file.name = "garment.png"

            response = self.client.images.edit(
                model="gpt-image-1",
                image=image_file,
                prompt=prompt,
                size="1024x1024",
                quality=quality,
            )

            image_data = response.data[0]

            if hasattr(image_data, 'b64_json') and image_data.b64_json:
                reconstructed_bytes = base64.b64decode(image_data.b64_json)
            elif hasattr(image_data, 'url') and image_data.url:
                import requests
                resp = requests.get(image_data.url)
                reconstructed_bytes = resp.content
            else:
                logger.warning(f"Unexpected response format from images.edit for '{item_name}'")
                return None

            elapsed = time.time() - start
            logger.info(f"Reconstructed '{item_name}' in {elapsed:.1f}s (quality={quality})")
            return reconstructed_bytes

        except Exception as e:
            elapsed = time.time() - start
            logger.warning(f"Garment reconstruction failed for '{item_name}' after {elapsed:.1f}s: {e}")
            return None
