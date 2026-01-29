"""
Collage Service - Generate grid collages from item images.

Creates 2x2 or 2x3 grids of wardrobe item images for SMS/MMS output.
Downloads images from S3 URLs, arranges in grid, uploads result to S3.
"""

import os
import uuid
import logging
import requests
from io import BytesIO
from typing import List, Optional, Tuple
from PIL import Image

from services.storage_manager import StorageManager

logger = logging.getLogger(__name__)

# Grid size per cell - tight grid like homepage, no padding
CELL_SIZE = 200
PADDING = 2  # Minimal gap
BACKGROUND_COLOR = (245, 243, 240)  # Warm off-white like homepage


def generate_outfit_collage(
    user_id: str,
    image_urls: List[str],
    max_images: int = 6
) -> Optional[str]:
    """
    Generate a grid collage from item images.

    - Downloads images from S3/HTTP URLs
    - Arranges in 2x2 or 2x3 grid depending on count
    - Uploads result to S3
    - Returns public URL

    Args:
        user_id: User identifier (for S3 path)
        image_urls: List of image URLs (S3 or HTTP)
        max_images: Maximum images to include (default 6)

    Returns:
        S3 URL of generated collage, or None if failed
    """
    if not image_urls:
        logger.warning("No image URLs provided for collage")
        return None

    # Limit images
    urls = image_urls[:max_images]
    num_images = len(urls)

    # Download images
    images = []
    for url in urls:
        img = _download_image(url)
        if img:
            images.append(img)

    if not images:
        logger.error("No images could be downloaded for collage")
        return None

    # Determine grid layout
    cols, rows = _calculate_grid_size(len(images))

    # Create collage
    collage = _create_grid_collage(images, cols, rows)

    # Upload to S3
    storage = StorageManager(
        storage_type=os.getenv("STORAGE_TYPE", "local"),
        user_id=user_id
    )

    filename = f"collage_{uuid.uuid4().hex[:8]}.jpg"
    url = storage.save_image(collage, filename, subfolder="collages")

    logger.info(f"Generated collage: {url} ({len(images)} images, {cols}x{rows} grid)")
    return url


def _download_image(url: str) -> Optional[Image.Image]:
    """
    Download image from URL.

    Handles both S3 URLs and regular HTTP URLs.
    """
    try:
        if not url:
            return None

        # Download via HTTP
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        img = Image.open(BytesIO(response.content))

        # Convert to RGB if needed (PNG with transparency, etc.)
        if img.mode in ('RGBA', 'P', 'LA'):
            # Create white background
            background = Image.new('RGB', img.size, BACKGROUND_COLOR)
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        return img

    except Exception as e:
        logger.warning(f"Failed to download image {url}: {e}")
        return None


def _calculate_grid_size(num_images: int) -> Tuple[int, int]:
    """
    Calculate optimal grid size for given number of images.

    Returns (cols, rows)
    """
    if num_images <= 2:
        return (2, 1)  # 2 images side by side
    elif num_images <= 4:
        return (2, 2)  # 2x2 grid
    else:
        return (3, 2)  # 3x2 grid for 5-6 images


def _create_grid_collage(
    images: List[Image.Image],
    cols: int,
    rows: int
) -> Image.Image:
    """
    Create a tight grid collage from images.

    Images are cropped to fill cells completely (no empty space).
    """
    # Calculate canvas size - tight grid with minimal padding
    width = cols * CELL_SIZE + (cols + 1) * PADDING
    height = rows * CELL_SIZE + (rows + 1) * PADDING

    # Create canvas
    canvas = Image.new('RGB', (width, height), BACKGROUND_COLOR)

    # Place images in grid
    for idx, img in enumerate(images):
        if idx >= cols * rows:
            break

        row = idx // cols
        col = idx % cols

        # Crop image to fill cell exactly
        cropped = _crop_to_fill(img, CELL_SIZE, CELL_SIZE)

        # Calculate position
        x = PADDING + col * (CELL_SIZE + PADDING)
        y = PADDING + row * (CELL_SIZE + PADDING)

        canvas.paste(cropped, (x, y))

    return canvas


def _crop_to_fill(img: Image.Image, target_width: int, target_height: int) -> Image.Image:
    """
    Crop and resize image to fill target dimensions exactly (no empty space).
    Centers the crop on the image.
    """
    # Calculate scale to FILL (not fit) - use max ratio so image covers entire cell
    width_ratio = target_width / img.width
    height_ratio = target_height / img.height
    scale = max(width_ratio, height_ratio)

    # Resize to cover
    new_width = int(img.width * scale)
    new_height = int(img.height * scale)
    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Crop to exact target size (center crop)
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height

    return resized.crop((left, top, right, bottom))
