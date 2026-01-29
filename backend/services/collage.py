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

# Grid size per cell
CELL_SIZE = 300
PADDING = 10
BACKGROUND_COLOR = (255, 255, 255)  # White


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
    Create a grid collage from images.

    Images are resized to fit cells while maintaining aspect ratio.
    """
    # Calculate canvas size
    width = cols * CELL_SIZE + (cols + 1) * PADDING
    height = rows * CELL_SIZE + (rows + 1) * PADDING

    # Create white canvas
    canvas = Image.new('RGB', (width, height), BACKGROUND_COLOR)

    # Place images in grid
    for idx, img in enumerate(images):
        if idx >= cols * rows:
            break

        row = idx // cols
        col = idx % cols

        # Resize image to fit cell (maintain aspect ratio)
        resized = _resize_to_fit(img, CELL_SIZE, CELL_SIZE)

        # Calculate position (center in cell)
        x = col * CELL_SIZE + (col + 1) * PADDING + (CELL_SIZE - resized.width) // 2
        y = row * CELL_SIZE + (row + 1) * PADDING + (CELL_SIZE - resized.height) // 2

        canvas.paste(resized, (x, y))

    return canvas


def _resize_to_fit(img: Image.Image, max_width: int, max_height: int) -> Image.Image:
    """
    Resize image to fit within bounds while maintaining aspect ratio.
    """
    # Calculate scale to fit within bounds
    width_ratio = max_width / img.width
    height_ratio = max_height / img.height
    scale = min(width_ratio, height_ratio)

    # Don't upscale
    if scale >= 1:
        return img

    new_width = int(img.width * scale)
    new_height = int(img.height * scale)

    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
