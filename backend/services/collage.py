"""
Collage Service - Editorial flat-lay collage generator.

Creates outfit boards that mimic a body silhouette:
- Items positioned where they'd be worn on the body
- Scarf at neckline, bag at hip, shoes at feet
- Natural overlaps at waist and hem
- Background removal + hanger cropping
- Drop shadows for depth

Output: 1200x1600 portrait canvas (3:4), uploaded to S3.
"""

import logging
import os
import uuid
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import requests
from PIL import Image, ImageFilter

from services.outfit_validator import get_slot
from services.storage_manager import StorageManager

logger = logging.getLogger(__name__)

CANVAS_W = 1200
CANVAS_H = 1600
BACKGROUND_COLOR = (245, 243, 240)

# Slot -> fraction of canvas width for sizing
SLOT_SIZE = {
    "outer_layer": 0.58,
    "dress": 0.52,
    "mid_layer": 0.48,
    "base_top": 0.46,
    "bottom": 0.44,
    "shoes": 0.26,
    "bag": 0.22,
    "accessory": 0.20,
}
DEFAULT_SIZE = 0.38

SHADOW_OFFSET = (6, 10)
SHADOW_BLUR = 14
SHADOW_COLOR = (0, 0, 0, 35)

# Slots that can have hangers
HANGER_SLOTS = {"base_top", "mid_layer", "outer_layer", "dress", "bottom"}


def generate_outfit_collage(
    user_id: str,
    image_urls: List[str],
    items: Optional[List[dict]] = None,
    max_images: int = 6,
) -> Optional[str]:
    if not image_urls:
        logger.warning("No image URLs provided for collage")
        return None

    urls = image_urls[:max_images]

    if not items:
        items = [{"image_url": url, "category": "unknown", "sub_category": ""} for url in urls]
    else:
        items = items[:max_images]
        for i, item in enumerate(items):
            if not item.get("image_url") and i < len(urls):
                item["image_url"] = urls[i]

    from services.bg_removal import remove_backgrounds_parallel
    processed = remove_backgrounds_parallel(items, user_id)

    if not processed:
        logger.warning("All bg removals failed, trying raw download fallback")
        processed = _fallback_download(items, user_id=user_id)

    if not processed:
        logger.error("No images could be processed for collage")
        return None

    # Crop hangers, trim transparency
    cleaned = []
    for item, img in processed:
        slot = get_slot(item)
        img = _crop_hanger(img, slot)
        img = _trim_transparent(img)
        if img.width > 0 and img.height > 0:
            cleaned.append((item, img, slot))

    if not cleaned:
        return None

    # Layout items like a body silhouette
    positions = _layout_silhouette(cleaned)

    # Render
    canvas = _render(positions)

    # Save at high quality
    storage = StorageManager(
        storage_type=os.getenv("STORAGE_TYPE", "local"),
        user_id=user_id,
    )
    filename = f"collage_{uuid.uuid4().hex[:8]}.jpg"

    rgb = Image.new("RGB", canvas.size, BACKGROUND_COLOR)
    rgb.paste(canvas, mask=canvas.split()[3] if canvas.mode == "RGBA" else None)

    if storage.storage_type == "s3":
        buf = BytesIO()
        rgb.save(buf, format="JPEG", quality=92, optimize=True)
        buf.seek(0)
        s3_key = f"{user_id}/collages/{filename}"
        storage.s3_client.upload_fileobj(
            buf, storage.bucket_name, s3_key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )
        url = f"{storage.get_base_url()}/{s3_key}"
    else:
        url = storage.save_image(rgb, filename, subfolder="collages")

    logger.info(f"Generated flat-lay collage: {url} ({len(cleaned)} items)")
    return url


# --- Body silhouette layout ---
#
# The canvas represents a body from shoulders to feet.
# Each slot has a "body zone" — a vertical region on the canvas
# and a horizontal position (center, left, right).
#
# Zone map (% of canvas height):
#   0.05 - 0.35  upper torso (tops, outerwear, mid-layers)
#   0.30 - 0.65  lower torso (bottoms, dresses)
#   0.60 - 0.85  feet (shoes)
#
# Accessories go WHERE they're worn:
#   scarf/jewelry → near neckline (y ~0.08), tucked beside the top
#   belt → at waist (y ~0.32)
#   bag → hip height (y ~0.50), offset to side
#   hat/sunglasses → above top (y ~0.02)

def _layout_silhouette(
    cleaned: List[Tuple[dict, Image.Image, Optional[str]]],
) -> List[Tuple[dict, Image.Image, int, int]]:
    """
    Place items on canvas mimicking a body silhouette.

    Returns list of (item, resized_image, x, y) — top-left pixel coords.
    """
    # Group by slot
    by_slot: Dict[str, List[Tuple[dict, Image.Image]]] = {}
    for item, img, slot in cleaned:
        key = slot or "unknown"
        by_slot.setdefault(key, []).append((item, img))

    positions = []  # (item, resized_img, x, y, z_order)

    # --- Main garments (center column) ---

    # Determine what we have
    has_outer = "outer_layer" in by_slot
    has_mid = "mid_layer" in by_slot
    has_top = "base_top" in by_slot
    has_dress = "dress" in by_slot
    has_bottom = "bottom" in by_slot
    has_shoes = "shoes" in by_slot
    has_bag = "bag" in by_slot
    has_accessory = "accessory" in by_slot

    cx = CANVAS_W // 2  # center x

    if has_dress:
        # Dress occupies the torso zone
        item, img = by_slot["dress"][0]
        w, h = _target_size(img, "dress")
        x = cx - w // 2
        y = int(CANVAS_H * 0.08)
        positions.append((item, img.resize((w, h), Image.Resampling.LANCZOS), x, y, 2))
        bottom_of_torso = y + h
    else:
        bottom_of_torso = int(CANVAS_H * 0.08)

        # Outerwear: behind everything, offset left
        if has_outer:
            item, img = by_slot["outer_layer"][0]
            w, h = _target_size(img, "outer_layer")
            x = cx - w // 2 - int(CANVAS_W * 0.06)
            y = int(CANVAS_H * 0.06)
            positions.append((item, img.resize((w, h), Image.Resampling.LANCZOS), x, y, 0))
            bottom_of_torso = max(bottom_of_torso, y + h)

        # Mid layer: behind top, slight offset
        if has_mid:
            item, img = by_slot["mid_layer"][0]
            w, h = _target_size(img, "mid_layer")
            offset = int(CANVAS_W * 0.04) if has_outer else 0
            x = cx - w // 2 + offset
            y = int(CANVAS_H * 0.07) if has_outer else int(CANVAS_H * 0.06)
            positions.append((item, img.resize((w, h), Image.Resampling.LANCZOS), x, y, 1))
            bottom_of_torso = max(bottom_of_torso, y + h)

        # Top: main center piece
        if has_top:
            item, img = by_slot["base_top"][0]
            w, h = _target_size(img, "base_top")
            x = cx - w // 2
            y_top = int(CANVAS_H * 0.10)
            if has_outer or has_mid:
                # Overlap slightly with layer behind
                y_top = int(CANVAS_H * 0.12)
            positions.append((item, img.resize((w, h), Image.Resampling.LANCZOS), x, y_top, 2))
            bottom_of_torso = max(bottom_of_torso, y_top + h)

        # Bottom: overlaps with top at waist
        if has_bottom:
            item, img = by_slot["bottom"][0]
            w, h = _target_size(img, "bottom")
            x = cx - w // 2
            # Place so top of pants overlaps bottom of top by ~15%
            waist_y = bottom_of_torso - int(h * 0.10)
            # But don't go above the top
            waist_y = max(waist_y, int(CANVAS_H * 0.28))
            positions.append((item, img.resize((w, h), Image.Resampling.LANCZOS), x, waist_y, 3))
            bottom_of_torso = waist_y + h

    # Shoes: below bottom/dress, slight overlap at hem
    if has_shoes:
        item, img = by_slot["shoes"][0]
        w, h = _target_size(img, "shoes")
        shoe_x = cx - w // 2
        shoe_y = bottom_of_torso - int(h * 0.08)
        # Don't let shoes go off canvas
        shoe_y = min(shoe_y, CANVAS_H - h - int(CANVAS_H * 0.04))
        if has_bag:
            # Shift shoes slightly left to make room for bag
            shoe_x = cx - w // 2 - int(CANVAS_W * 0.10)
        positions.append((item, img.resize((w, h), Image.Resampling.LANCZOS), shoe_x, shoe_y, 4))

    # Bag: hip height, offset to the right
    if has_bag:
        item, img = by_slot["bag"][0]
        w, h = _target_size(img, "bag")
        bag_x = cx + int(CANVAS_W * 0.15)
        bag_y = int(CANVAS_H * 0.55)
        if has_shoes:
            # Place bag near the shoes but to the right
            bag_y = bottom_of_torso - int(h * 0.15)
            bag_y = min(bag_y, CANVAS_H - h - int(CANVAS_H * 0.04))
        positions.append((item, img.resize((w, h), Image.Resampling.LANCZOS), bag_x, bag_y, 5))

    # Accessories: placed where they'd be worn
    if has_accessory:
        for idx, (item, img) in enumerate(by_slot["accessory"]):
            w, h = _target_size(img, "accessory")
            resized = img.resize((w, h), Image.Resampling.LANCZOS)

            # First accessory: near neckline, offset to one side
            if idx == 0:
                acc_x = cx + int(CANVAS_W * 0.18)
                acc_y = int(CANVAS_H * 0.06)
            # Second: other side
            elif idx == 1:
                acc_x = cx - int(CANVAS_W * 0.18) - w
                acc_y = int(CANVAS_H * 0.08)
            # More: scatter near top
            else:
                acc_x = cx + int(CANVAS_W * (0.20 if idx % 2 == 0 else -0.25))
                acc_y = int(CANVAS_H * (0.04 + idx * 0.06))

            positions.append((item, resized, acc_x, acc_y, 6))

    # Unknown items: fill remaining space
    for item, img in by_slot.get("unknown", []):
        w, h = _target_size(img, "unknown")
        x = cx - w // 2
        y = int(CANVAS_H * 0.45)
        positions.append((item, img.resize((w, h), Image.Resampling.LANCZOS), x, y, 3))

    # Sort by z-order so back items render first
    positions.sort(key=lambda p: p[4])

    return [(item, img, x, y) for item, img, x, y, _ in positions]


def _target_size(img: Image.Image, slot: str) -> Tuple[int, int]:
    """Calculate target (width, height) for an item based on slot."""
    frac = SLOT_SIZE.get(slot, DEFAULT_SIZE)
    target_w = int(CANVAS_W * frac)
    scale = target_w / max(img.width, 1)
    w = int(img.width * scale)
    h = int(img.height * scale)

    max_h = int(CANVAS_H * 0.42)
    if h > max_h:
        scale = max_h / max(img.height, 1)
        w = int(img.width * scale)
        h = int(img.height * scale)

    return w, h


def _crop_hanger(img: Image.Image, slot: Optional[str]) -> Image.Image:
    """Crop hanger region from garments (top 12% for hung items)."""
    if slot not in HANGER_SLOTS:
        return img
    if img.mode != "RGBA":
        return img

    crop_h = int(img.height * 0.12)
    if crop_h < 10:
        return img

    return img.crop((0, crop_h, img.width, img.height))


def _fallback_download(items: List[dict], user_id: str = "") -> List[Tuple[dict, Image.Image]]:
    results = []
    for item in items:
        url = item.get("image_url") or item.get("image_path", "")
        if not url:
            continue
        try:
            if "s3.us-east-2.amazonaws.com" in url and user_id:
                storage = StorageManager(storage_type="s3", user_id=user_id)
                data = storage.load_file(url)
                if data:
                    img = Image.open(BytesIO(data)).convert("RGBA")
                    results.append((item, img))
                continue
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content)).convert("RGBA")
            results.append((item, img))
        except Exception as e:
            logger.warning(f"Fallback download failed for {url}: {e}")
    return results


def _render(
    positions: List[Tuple[dict, Image.Image, int, int]],
) -> Image.Image:
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), BACKGROUND_COLOR + (255,))

    for item, img, x, y in positions:
        if img.width == 0 or img.height == 0:
            continue
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        shadow = _create_shadow(img)
        _safe_paste(canvas, shadow, x + SHADOW_OFFSET[0], y + SHADOW_OFFSET[1])
        _safe_paste(canvas, img, x, y)

    return canvas


def _safe_paste(canvas: Image.Image, img: Image.Image, x: int, y: int):
    """Paste handling out-of-bounds coordinates."""
    if x + img.width <= 0 or y + img.height <= 0:
        return
    if x >= canvas.width or y >= canvas.height:
        return

    img_x, img_y = 0, 0
    paste_x, paste_y = x, y

    if x < 0:
        img_x = -x
        paste_x = 0
    if y < 0:
        img_y = -y
        paste_y = 0

    right = min(img.width, canvas.width - x)
    bottom = min(img.height, canvas.height - y)

    if right <= img_x or bottom <= img_y:
        return

    cropped = img.crop((img_x, img_y, right, bottom))
    canvas.paste(cropped, (paste_x, paste_y), cropped)


def _trim_transparent(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        return img
    bbox = img.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def _create_shadow(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        return Image.new("RGBA", img.size, (0, 0, 0, 0))

    alpha = img.split()[3]
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow_layer = Image.new("RGBA", img.size, SHADOW_COLOR)
    shadow.paste(shadow_layer, mask=alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=SHADOW_BLUR))
    return shadow
