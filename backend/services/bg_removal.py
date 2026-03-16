"""
Background Removal Service - rembg wrapper with S3 caching.

Removes backgrounds from wardrobe item images for editorial flat-lay collages.
Caches results in S3 to avoid re-processing the same items.
"""

import hashlib
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from typing import List, Optional, Tuple

import requests
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)


def remove_background(image: Image.Image) -> Image.Image:
    """
    Remove background from a PIL image using rembg.

    Returns RGBA image with transparent background.
    Falls back to original (converted to RGBA) on failure.
    """
    try:
        from rembg import remove, new_session
        # u2net is the best general model for wardrobe photos
        # (isnet-general-use tested — worse on messy backgrounds)
        session = new_session("u2net")

        input_buf = BytesIO()
        image.save(input_buf, format="PNG")
        input_bytes = input_buf.getvalue()

        output_bytes = remove(input_bytes, session=session)
        result = Image.open(BytesIO(output_bytes)).convert("RGBA")
        result = _clean_alpha(result)
        return result

    except Exception as e:
        logger.warning(f"rembg failed, using original image: {e}")
        return image.convert("RGBA")


def _clean_alpha(img: Image.Image) -> Image.Image:
    """Clean up alpha channel after bg removal — threshold, erode, feather.

    Two-pass approach:
    1. Hard threshold to kill semi-transparent fringe
    2. Morphological erosion (2px) to eat into halo edges
    3. Gentle feather to smooth jagged edges without reintroducing halo
    """
    if img.mode != "RGBA":
        return img
    alpha = img.split()[3]
    # Pass 1: hard threshold — kill semi-transparent fringe
    alpha = alpha.point(lambda x: 0 if x < 30 else (255 if x > 220 else x))
    # Pass 2: erode mask inward by 2px to eat halo remnants
    alpha = alpha.filter(ImageFilter.MinFilter(3))
    alpha = alpha.filter(ImageFilter.MinFilter(3))
    # Pass 3: gentle feather for smooth edges (not enough to reintroduce halo)
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=0.8))
    # Final threshold to keep edges crisp after blur
    alpha = alpha.point(lambda x: 0 if x < 20 else 255)
    img.putalpha(alpha)
    return img


def _url_to_cache_key(image_url: str) -> str:
    """Generate a stable cache key from an image URL."""
    return hashlib.sha256(image_url.encode()).hexdigest()[:16] + "_v3"


def _download_image(url: str, user_id: Optional[str] = None) -> Optional[Image.Image]:
    """Download image from URL, using S3 client for S3 URLs."""
    try:
        if "s3.us-east-2.amazonaws.com" in url and user_id:
            from services.storage_manager import StorageManager
            storage = StorageManager(storage_type="s3", user_id=user_id)
            data = storage.load_file(url)
            if data:
                return Image.open(BytesIO(data))
            return None
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except Exception as e:
        logger.warning(f"Failed to download {url}: {e}")
        return None


def remove_background_cached(image_url: str, user_id: str) -> Optional[Image.Image]:
    """
    Remove background with S3 caching.

    Checks for cached bg-removed PNG at {user_id}/bg_removed/{hash}.png.
    On cache miss, downloads original, runs rembg, caches result.
    Returns RGBA PIL Image or None on total failure.
    """
    from services.storage_manager import StorageManager

    cache_key = _url_to_cache_key(image_url)
    cache_filename = f"{cache_key}.png"

    storage = StorageManager(
        storage_type=os.getenv("STORAGE_TYPE", "local"),
        user_id=user_id,
    )

    # Check cache
    if storage.storage_type == "s3":
        cache_url = f"{storage.get_base_url()}/{user_id}/bg_removed/{cache_filename}"
        if storage.file_exists(cache_url):
            logger.info(f"bg_removal cache hit: {cache_key}")
            try:
                cached_bytes = storage.load_file(cache_url)
                if cached_bytes:
                    return Image.open(BytesIO(cached_bytes)).convert("RGBA")
            except Exception as e:
                logger.warning(f"Cache read failed, regenerating: {e}")
    else:
        cache_path = os.path.join("wardrobe_photos", user_id, "bg_removed", cache_filename)
        if os.path.exists(cache_path):
            logger.info(f"bg_removal cache hit (local): {cache_key}")
            try:
                return Image.open(cache_path).convert("RGBA")
            except Exception as e:
                logger.warning(f"Local cache read failed: {e}")

    # Cache miss — download and process
    original = _download_image(image_url, user_id=user_id)
    if not original:
        return None

    result = remove_background(original)

    # Save to cache
    try:
        # Save as PNG to preserve transparency
        buf = BytesIO()
        result.save(buf, format="PNG")
        buf.seek(0)

        if storage.storage_type == "s3":
            s3_key = f"{user_id}/bg_removed/{cache_filename}"
            storage.s3_client.upload_fileobj(
                buf,
                storage.bucket_name,
                s3_key,
                ExtraArgs={"ContentType": "image/png"},
            )
            logger.info(f"Cached bg-removed image to S3: {s3_key}")
        else:
            cache_dir = os.path.join("wardrobe_photos", user_id, "bg_removed")
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, cache_filename)
            with open(cache_path, "wb") as f:
                f.write(buf.getvalue())
            logger.info(f"Cached bg-removed image locally: {cache_path}")

    except Exception as e:
        logger.warning(f"Failed to cache bg-removed image: {e}")

    return result


def remove_backgrounds_parallel(
    items: List[dict],
    user_id: str,
    max_workers: int = 4,
) -> List[Tuple[dict, Image.Image]]:
    """
    Remove backgrounds from multiple items in parallel.

    Args:
        items: List of item dicts, each with 'image_url' (or 'image_path') key.
        user_id: For S3 cache path.
        max_workers: Thread pool size.

    Returns:
        List of (item_dict, RGBA_image) tuples for successfully processed items.
    """
    results = []

    def process_item(item):
        url = item.get("image_url") or item.get("image_path", "")
        if not url:
            return None
        img = remove_background_cached(url, user_id)
        if img:
            return (item, img)
        return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_item, item): item for item in items}
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                item = futures[future]
                logger.warning(f"bg removal failed for item: {e}")

    # Preserve original ordering
    url_order = {
        (item.get("image_url") or item.get("image_path", "")): i
        for i, item in enumerate(items)
    }
    results.sort(key=lambda r: url_order.get(r[0].get("image_url") or r[0].get("image_path", ""), 999))

    return results


def warm_up_model():
    """
    Pre-load the rembg model so first request isn't slow.
    Call this at app startup.
    """
    try:
        from rembg import new_session
        session = new_session("u2net")
        logger.info("rembg model warmed up successfully")
    except Exception as e:
        logger.warning(f"rembg warm-up failed (will load on first use): {e}")
