"""
Enhance wardrobe items with fal.ai studio-quality product photos.

For each garment item: runs fal.ai enhancement, updates the wardrobe image
(visible in closet), and caches the bg-removed version (fast collages).

Usage:
    python scripts/enhance_wardrobe.py peichin          # enhance all uncached
    python scripts/enhance_wardrobe.py peichin --force   # re-enhance everything
    python scripts/enhance_wardrobe.py peichin --dry-run  # just show what would be enhanced
"""

import os
import sys
import argparse
import logging
from io import BytesIO

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Ensure S3 storage
os.environ.setdefault('STORAGE_TYPE', 's3')

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

ENHANCE_CATEGORIES = {"tops", "bottoms", "dresses", "outerwear", "one-pieces", "scarves"}


def enhance_user_wardrobe(user_id: str, force: bool = False, dry_run: bool = False):
    """Enhance all garment items for a user."""
    from services.wardrobe_manager import WardrobeManager
    from services.storage_manager import StorageManager
    from services.bg_removal import (
        _url_to_cache_key, _download_image, _enhance_garment_fal,
        remove_background,
    )

    wm = WardrobeManager(user_id=user_id)
    items = wm.get_wardrobe_items(filter_type="all")
    storage = StorageManager(storage_type=os.getenv("STORAGE_TYPE", "s3"), user_id=user_id)

    # Filter to garment categories only
    garments = []
    for item in items:
        cat = item.get("styling_details", {}).get("category", "").lower()
        sub = item.get("styling_details", {}).get("sub_category", "").lower()
        name = item.get("styling_details", {}).get("name", "")
        if cat in ENHANCE_CATEGORIES or "scarf" in sub or "scarf" in name.lower():
            garments.append(item)

    logger.info(f"Found {len(garments)} garment items out of {len(items)} total for {user_id}")

    enhanced_count = 0
    skipped_count = 0
    failed_count = 0

    for item in garments:
        item_name = item.get("styling_details", {}).get("name", "Unknown")
        item_id = item.get("id", "")
        image_url = item.get("system_metadata", {}).get("image_url", "") or item.get("system_metadata", {}).get("image_path", "")

        if not image_url:
            logger.info(f"  SKIP {item_name}: no image URL")
            skipped_count += 1
            continue

        # Check if enhanced cache already exists
        cache_key = _url_to_cache_key(image_url)
        cache_filename = f"{cache_key}_enhanced.png"

        if not force and storage.storage_type == "s3":
            cache_url = f"{storage.get_base_url()}/{user_id}/bg_removed/{cache_filename}"
            if storage.file_exists(cache_url):
                logger.info(f"  CACHED {item_name}")
                skipped_count += 1
                continue

        if dry_run:
            logger.info(f"  WOULD ENHANCE {item_name} ({item_id})")
            enhanced_count += 1
            continue

        logger.info(f"  ENHANCING {item_name}...")

        try:
            # Download original
            original = _download_image(image_url, user_id=user_id)
            if not original:
                logger.info(f"    FAILED: could not download image")
                failed_count += 1
                continue

            # Run fal.ai enhancement
            buf = BytesIO()
            original.save(buf, format="JPEG", quality=90)
            enhanced_bytes = _enhance_garment_fal(buf.getvalue())

            if not enhanced_bytes:
                logger.info(f"    FAILED: fal.ai enhancement returned nothing")
                failed_count += 1
                continue

            # 1. Update wardrobe item image (visible in closet)
            from PIL import Image
            enhanced_img = Image.open(BytesIO(enhanced_bytes))
            img_buf = BytesIO()
            enhanced_img.save(img_buf, format="JPEG", quality=92)
            img_buf.seek(0)
            img_buf.name = f"{item_name.replace(' ', '_')}_enhanced.jpg"

            new_path = wm.update_item_image(item_id, img_buf)
            if new_path:
                logger.info(f"    Updated wardrobe image -> {new_path}")
            else:
                logger.info(f"    WARNING: failed to update wardrobe image")

            # 2. Cache bg-removed version (fast collages)
            bg_removed = remove_background(enhanced_img)
            out_buf = BytesIO()
            bg_removed.save(out_buf, format="PNG")
            out_buf.seek(0)

            if storage.storage_type == "s3":
                # Cache under BOTH old and new image URLs
                # (old URL for existing references, new URL for future)
                for url in [image_url, new_path]:
                    if url:
                        key = _url_to_cache_key(url)
                        s3_key = f"{user_id}/bg_removed/{key}_enhanced.png"
                        out_buf.seek(0)
                        storage.s3_client.upload_fileobj(
                            out_buf, storage.bucket_name, s3_key,
                            ExtraArgs={"ContentType": "image/png"},
                        )
                logger.info(f"    Cached bg-removed version")

            enhanced_count += 1
            logger.info(f"    DONE")

        except Exception as e:
            logger.info(f"    ERROR: {e}")
            failed_count += 1

    logger.info(f"\nSummary: {enhanced_count} enhanced, {skipped_count} skipped (cached), {failed_count} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhance wardrobe items with fal.ai")
    parser.add_argument("user_id", help="User ID to enhance")
    parser.add_argument("--force", action="store_true", help="Re-enhance even if cached")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be enhanced")
    args = parser.parse_args()

    enhance_user_wardrobe(args.user_id, force=args.force, dry_run=args.dry_run)
