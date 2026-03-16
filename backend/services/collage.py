"""
Collage Service - Editorial flat-lay collage generator.

"Stage and Story" framework — treats the canvas as a magazine spread:
- Primary zone: Hero item, generous sizing, slight rotation, off-center
- Secondary zone: Supporting items angled toward the hero, overlapping
- Edge zone: Accent items completing the diagonal, opposing rotations
- Diagonal composition (upper-left → lower-right)
- Background removal + hanger cropping + drop shadows

Output: 1200x1600 portrait canvas (3:4), uploaded to S3.
"""

import logging
import os
import uuid
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import requests
from PIL import Image, ImageEnhance, ImageFilter

from services.outfit_validator import get_slot
from services.storage_manager import StorageManager

logger = logging.getLogger(__name__)

CANVAS_W = 1200
CANVAS_H = 1600
BACKGROUND_COLOR = (245, 243, 240)
SPINE_X = 560  # 40px left of true center for asymmetric editorial feel

# Slot -> fraction of canvas width for sizing
SLOT_SIZE = {
    "outer_layer": 0.68,
    "dress": 0.52,
    "mid_layer": 0.48,
    "base_top": 0.46,
    "bottom": 0.44,
    "shoes": 0.26,
    "bag": 0.22,
    "accessory": 0.28,
}
DEFAULT_SIZE = 0.38

SHADOW_OFFSET = (6, 10)
SHADOW_BLUR = 14
SHADOW_COLOR = (0, 0, 0, 35)

# Rotation ranges per slot type (min_degrees, max_degrees)
# Only bags and accessories rotate — garments and shoes stay upright
ROTATION_RANGE = {
    "outer_layer": (0, 0),
    "dress": (0, 0),
    "mid_layer": (0, 0),
    "base_top": (0, 0),
    "bottom": (0, 0),
    "shoes": (0, 0),
    "bag": (5, 10),
    "accessory": (8, 15),
}
DEFAULT_ROTATION = (0, 0)

# Slots that can have hangers
HANGER_SLOTS = {"base_top", "mid_layer", "outer_layer", "dress", "bottom"}


def _normalize_lighting(cleaned):
    """Normalize lighting across items so they look shot under the same light.

    Two-step approach:
    1. Per-item brightness normalization: adjust each item's brightness toward
       a common target (L=180 in LAB space) so dark/bright items converge
    2. Uniform contrast + saturation boost for product-photo feel
    """
    import numpy as np

    TARGET_L = 180  # Target brightness in LAB L channel (0-255 scale)

    result = []
    for item, img, slot in cleaned:
        adjusted = img

        # Step 1: Per-item brightness normalization via LAB
        try:
            if img.mode == "RGBA":
                # Work on RGB channels only, preserve alpha
                alpha = img.split()[3]
                rgb = img.convert("RGB")
            else:
                alpha = None
                rgb = img

            arr = np.array(rgb).astype(np.float32)
            # Compute mean brightness of non-transparent pixels
            if alpha:
                mask = np.array(alpha) > 128
                if mask.any():
                    # Simple luminance: 0.299R + 0.587G + 0.114B
                    lum = arr[:,:,0] * 0.299 + arr[:,:,1] * 0.587 + arr[:,:,2] * 0.114
                    mean_lum = lum[mask].mean()

                    if mean_lum > 10:  # Avoid division by zero for very dark items
                        # Scale factor to bring mean luminance toward target
                        scale = TARGET_L / mean_lum
                        # Clamp scale to avoid extreme adjustments
                        scale = max(0.7, min(scale, 1.4))
                        arr = arr * scale
                        arr = np.clip(arr, 0, 255)

            adjusted = Image.fromarray(arr.astype(np.uint8), "RGB")
            if alpha:
                adjusted = adjusted.convert("RGBA")
                adjusted.putalpha(alpha)
        except Exception:
            pass  # Fall back to unadjusted image

        # Step 2: Uniform contrast + saturation boost
        adjusted = ImageEnhance.Contrast(adjusted).enhance(1.06)
        adjusted = ImageEnhance.Color(adjusted).enhance(1.15)
        result.append((item, adjusted, slot))
    return result


def generate_outfit_collage(
    user_id: str,
    image_urls: List[str],
    items: Optional[List[dict]] = None,
    max_images: int = 8,
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

    cleaned = _normalize_lighting(cleaned)

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


def _jitter(base: int, item_count: int, slot_index: int, amplitude: int = 35) -> int:
    """Deterministic pseudo-random offset. Same inputs = same output."""
    seed = (item_count * 7 + slot_index * 13) % 31
    offset = (seed - 15) * amplitude // 15
    return base + offset


def _rotation_angle(slot: str, item_count: int, slot_index: int) -> float:
    """Deterministic rotation angle. Adjacent items get opposing directions."""
    min_deg, max_deg = ROTATION_RANGE.get(slot, DEFAULT_ROTATION)
    seed = (item_count * 11 + slot_index * 17) % 37
    angle = min_deg + (max_deg - min_deg) * seed / 36.0
    # Alternate direction: even indices clockwise, odd counter-clockwise
    if slot_index % 2 == 1:
        angle = -angle
    return angle


def _rotate_item(img: Image.Image, angle: float) -> Image.Image:
    """Rotate an RGBA image, expanding canvas to fit, transparent fill."""
    if abs(angle) < 0.5:
        return img
    return img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC,
                      fillcolor=(0, 0, 0, 0))


# --- "Stage and Story" editorial layout ---
#
# "Stage and Story" framework — magazine spread composition:
#
# Three compositional zones:
#   Primary: Hero item — largest/most complex, generous sizing, slight rotation, off-center
#   Secondary: Supporting items angled toward hero, overlapping edges
#   Edge: Accents completing a diagonal, opposing rotations
#
# Diagonal flow: upper-left → lower-right
# Overlap signals relationship (sleeve over waistband, shoe under hem)
# Adjacent items rotate in opposing directions for visual tension

def _layout_silhouette(
    cleaned: List[Tuple[dict, Image.Image, Optional[str]]],
) -> List[Tuple[dict, Image.Image, int, int]]:
    """
    Editorial flat-lay layout using "Stage and Story" framework.

    Arranges items along a diagonal with rotation, intentional overlaps,
    and accessories anchored to their nearest garment.

    Returns list of (item, rotated_image, x, y) — top-left pixel coords.
    """
    n = len(cleaned)  # for deterministic jitter
    slot_idx = 0  # global counter for rotation alternation

    # Group by slot
    by_slot: Dict[str, List[Tuple[dict, Image.Image]]] = {}
    for item, img, slot in cleaned:
        key = slot or "unknown"
        by_slot.setdefault(key, []).append((item, img))

    positions = []  # (item, rotated_img, x, y, z_order)

    has_outer = "outer_layer" in by_slot
    has_mid = "mid_layer" in by_slot
    has_top = "base_top" in by_slot
    has_dress = "dress" in by_slot
    has_bottom = "bottom" in by_slot
    has_shoes = "shoes" in by_slot
    has_bag = "bag" in by_slot
    has_accessory = "accessory" in by_slot

    # Track garment bounds for accessory anchoring
    top_w = 0
    top_y = 160  # y where the top garment starts (for accessory anchoring)
    bottom_of_top = 0
    # Track the hero garment bounds for accessories and bag
    hero_center_x = SPINE_X
    hero_center_y = 300
    hero_right_edge = SPINE_X + 200  # right edge of hero for bag anchoring

    def _place(item, img, slot, x, y, z, si):
        """Resize, rotate, and append to positions."""
        w, h = _target_size(img, slot)
        resized = img.resize((w, h), Image.Resampling.LANCZOS)
        angle = _rotation_angle(slot, n, si)
        rotated = _rotate_item(resized, angle)
        # Adjust position for expanded canvas from rotation
        dx = (rotated.width - w) // 2
        dy = (rotated.height - h) // 2
        final_x = max(x - dx, 5)  # clamp: never go off left edge
        final_y = max(y - dy, 5)  # clamp: never go off top edge
        positions.append((item, rotated, final_x, final_y, z))
        return w, h

    if has_dress:
        # HERO: Dress is the primary item — generous size, slight off-center
        item, img = by_slot["dress"][0]
        w, h = _target_size(img, "dress")
        # Diagonal: upper-left region
        x = _jitter(SPINE_X - w // 2 - 40, n, 0)
        y = _jitter(120, n, 1)
        _place(item, img, "dress", x, y, 2, slot_idx)
        slot_idx += 1
        bottom_of_torso = y + h
        top_w = w
        top_y = y
        bottom_of_top = y + h
        hero_center_x = x + w // 2
        hero_center_y = y + h // 2
        hero_right_edge = x + w
    else:
        bottom_of_torso = 160

        if has_outer:
            # Place top first as hero
            if has_top:
                item, img = by_slot["base_top"][0]
                w, h = _target_size(img, "base_top")
                x = _jitter(SPINE_X - w // 2 - 30, n, 2)
                y = _jitter(160, n, 3)
                _place(item, img, "base_top", x, y, 2, slot_idx)
                slot_idx += 1
                bottom_of_torso = max(bottom_of_torso, y + h)
                top_w = w
                top_y = y
                bottom_of_top = y + h
                hero_center_x = x + w // 2
                hero_center_y = y + h // 2
                hero_right_edge = x + w

            # Outerwear: BEHIND the top, offset right — like laying clothes on a bed
            # The jacket frames the top, peeking out at the shoulders and sides
            item, img = by_slot["outer_layer"][0]
            w, h = _target_size(img, "outer_layer")
            ref_tw = top_w or int(CANVAS_W * 0.46)
            # Center on spine but offset right so jacket peeks from behind the top
            x = _jitter(SPINE_X - w // 2 + int(ref_tw * 0.25), n, 0)
            y = _jitter(60, n, 1)  # Slightly above top so collar peeks
            _place(item, img, "outer_layer", x, y, 1, slot_idx)  # z=1: behind the top
            slot_idx += 1
            # Only use outer for torso reference if no top/mid to define waist
            if not has_top and not has_mid:
                bottom_of_torso = max(bottom_of_torso, y + h)
            if not has_top:
                top_w = w
                top_y = y
                bottom_of_top = y + h
                hero_center_x = x + w // 2
                hero_center_y = y + h // 2
                hero_right_edge = x + w

        else:
            # No outerwear: top is hero, centered on spine
            if has_top:
                item, img = by_slot["base_top"][0]
                w, h = _target_size(img, "base_top")
                x = _jitter(SPINE_X - w // 2 - 30, n, 2)
                y = _jitter(140, n, 3)
                _place(item, img, "base_top", x, y, 2, slot_idx)
                slot_idx += 1
                bottom_of_torso = max(bottom_of_torso, y + h)
                top_w = w
                top_y = y
                bottom_of_top = y + h
                hero_center_x = x + w // 2
                hero_center_y = y + h // 2
                hero_right_edge = x + w

        # Mid layer: secondary, angled toward hero
        if has_mid:
            item, img = by_slot["mid_layer"][0]
            w, h = _target_size(img, "mid_layer")
            if has_outer:
                # Behind outer, peeking out left
                x = _jitter(SPINE_X - w // 2 + 60, n, 6)
                y = _jitter(140, n, 7)
                z = 1
            elif has_top:
                # Over top, offset right along diagonal
                x = _jitter(SPINE_X - w // 2 + 100, n, 6)
                y = _jitter(80, n, 7)
                z = 4
            else:
                # Solo hero
                x = _jitter(SPINE_X - w // 2 - 40, n, 6)
                y = _jitter(120, n, 7)
                z = 2
                hero_center_x = x + w // 2
                hero_center_y = y + h // 2
                hero_right_edge = x + w
            _place(item, img, "mid_layer", x, y, z, slot_idx)
            slot_idx += 1
            bottom_of_torso = max(bottom_of_torso, y + h)
            if not has_top:
                top_w = w
                top_y = y
                bottom_of_top = y + h

        # Bottom: aligned with top on the spine, overlapping at waist
        if has_bottom:
            item, img = by_slot["bottom"][0]
            w, h = _target_size(img, "bottom")
            # Align with top — same spine axis
            x = _jitter(SPINE_X - w // 2 - 30, n, 8)
            # Overlap at waist — pulls bottom up under top like a body
            overlap_frac = 0.22 if has_outer else 0.18
            waist_y = bottom_of_torso - int(h * overlap_frac)
            waist_y = max(waist_y, 420)
            y = _jitter(waist_y, n, 9)
            _place(item, img, "bottom", x, y, 3, slot_idx)
            slot_idx += 1
            bottom_of_torso = y + h
            if not bottom_of_top:
                bottom_of_top = y

    # Shoes: slightly offset from spine (not centered, not far right)
    shoe_x_final = SPINE_X
    shoe_y_final = int(CANVAS_H * 0.75)
    shoe_w_final = 0
    if has_shoes:
        item, img = by_slot["shoes"][0]
        w, h = _target_size(img, "shoes")
        # Offset slightly LEFT of spine (body silhouette feel)
        shoe_x = _jitter(SPINE_X - w // 2 - 30, n, 10)
        shoe_y = bottom_of_torso + 30  # 30px gap below bottom, clear separation
        shoe_y = max(shoe_y, bottom_of_torso + 20)  # enforce minimum gap
        if has_dress:
            shoe_y = max(shoe_y, int(CANVAS_H * 0.78))
        shoe_y = _jitter(shoe_y, n, 11, amplitude=5)  # tiny jitter
        shoe_y = max(shoe_y, bottom_of_torso + 20)  # re-enforce gap after jitter
        # Hard ceiling: shoes must fit on canvas — this always wins
        shoe_y = min(shoe_y, CANVAS_H - h - 40)
        _place(item, img, "shoes", shoe_x, shoe_y, 5, slot_idx)
        slot_idx += 1
        shoe_x_final = shoe_x
        shoe_y_final = shoe_y
        shoe_w_final = w

    # EDGE ZONE: Bag — right side when no outerwear
    bag_on_left = has_bag and has_outer
    if has_bag and not bag_on_left:
        # No outerwear → bag goes RIGHT
        item, img = by_slot["bag"][0]
        w, h = _target_size(img, "bag")
        raw_bag_y = max(bottom_of_top - int(h * 0.2), 450)
        raw_bag_y = min(raw_bag_y, CANVAS_H - h - 60)
        bag_y = _jitter(raw_bag_y, n, 13, amplitude=15)
        bag_y = min(bag_y, CANVAS_H - h - 40)
        bag_x = _jitter(hero_right_edge + 20, n, 12, amplitude=15)
        bag_x = max(10, min(bag_x, CANVAS_W - w - 10))
        _place(item, img, "bag", bag_x, bag_y, 6, slot_idx)
        slot_idx += 1

    # EDGE ZONE: Unified left-side strip packing (bag when on left + all accessories)
    # All left-side items sorted by ideal_y, placed top-to-bottom with guaranteed spacing.
    if has_accessory or bag_on_left:
        left_edge_x = SPINE_X - (top_w // 2 if top_w else int(CANVAS_W * 0.23))
        waist_junction = bottom_of_top if bottom_of_top > 0 else int(top_y + (CANVAS_H * 0.35))

        # Collect all left-side items: (ideal_y, idx, item, img, w, h, z, slot_name, x_calc)
        left_items = []

        # Add bag to unified list when on left
        if bag_on_left:
            item, img = by_slot["bag"][0]
            w, h = _target_size(img, "bag")
            ideal_y = max(bottom_of_top - int(h * 0.2), 450)
            bag_x = _jitter(20, n, 12, amplitude=15)
            bag_x = max(10, min(bag_x, CANVAS_W - w - 10))
            left_items.append((ideal_y, -1, item, img, w, h, 6, "bag", bag_x))

        # Add accessories
        if has_accessory:
            for idx, (item, img) in enumerate(by_slot["accessory"]):
                sub_cat = (item.get("sub_category", "") or "").lower()
                name_lower = (item.get("name", "") or "").lower()
                w, h = _target_size(img, "accessory")

                if "belt" in sub_cat or "belt" in name_lower:
                    ideal_y = waist_junction - h // 2
                    z = 7
                elif "necklace" in sub_cat or "necklace" in name_lower or "pendant" in name_lower or "jewelry" in sub_cat or "jewellery" in sub_cat:
                    ideal_y = top_y + int((bottom_of_top - top_y) * 0.15) if bottom_of_top > top_y else top_y + 60
                    z = 6
                elif "earring" in sub_cat or "earring" in name_lower:
                    ideal_y = top_y - 10
                    z = 6
                elif "scarf" in sub_cat or "scarf" in name_lower:
                    ideal_y = top_y + 40
                    z = 6
                else:
                    ideal_y = waist_junction
                    z = 6
                acc_x = _jitter(left_edge_x - w + 10, n, 20 + idx, amplitude=15)
                acc_x = max(10, acc_x)
                left_items.append((ideal_y, idx, item, img, w, h, z, "accessory", acc_x))

        # Sort by ideal_y (top to bottom)
        left_items.sort(key=lambda e: e[0])

        # Single placement pass with one occupied_bottom tracker
        occupied_bottom = 0
        for ideal_y, idx, item, img, w, h, z, slot_name, item_x in left_items:
            # Apply jitter to ideal_y BEFORE overlap check
            jitter_idx = 13 if slot_name == "bag" else 21 + idx
            jitter_amp = 15 if slot_name == "bag" else 5
            y = _jitter(ideal_y, n, jitter_idx, amplitude=jitter_amp)
            y = max(y, top_y)                       # never above garments
            if occupied_bottom > 0:
                y = max(y, occupied_bottom + 15)     # never overlap previous item
            y = min(y, CANVAS_H - h - 40)            # fit on canvas
            _place(item, img, slot_name, item_x, y, z, slot_idx)
            slot_idx += 1
            occupied_bottom = y + h

    # Unknown items
    for item, img in by_slot.get("unknown", []):
        w, h = _target_size(img, "unknown")
        x = SPINE_X - w // 2
        y = int(CANVAS_H * 0.45)
        _place(item, img, "unknown", x, y, 3, slot_idx)
        slot_idx += 1

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

    max_h_frac = {
        "outer_layer": 0.55,
        "dress": 0.65,
        "mid_layer": 0.50,
        "base_top": 0.40,
        "bottom": 0.36,
        "shoes": 0.25,
        "bag": 0.28,
        "accessory": 0.25,
    }
    max_h = int(CANVAS_H * max_h_frac.get(slot, 0.42))
    if h > max_h:
        scale = max_h / max(img.height, 1)
        w = int(img.width * scale)
        h = int(img.height * scale)

    return w, h


def _crop_hanger(img: Image.Image, slot: Optional[str]) -> Image.Image:
    """Crop the thin hanger hook above the garment — preserve the garment itself.

    Only crops the narrow hook/wire above the garment shoulders. Does NOT
    aggressively crop into the garment — cropped clothing looks worse than
    a visible hanger. The hanger bar (if present) stays; it's a lesser evil
    than cutting off collars and necklines.
    """
    if slot not in HANGER_SLOTS:
        return img
    if img.mode != "RGBA":
        return img

    alpha = img.split()[3]
    width = img.width

    # Find where garment body starts (20%+ of width is opaque = shoulder line)
    garment_threshold = width * 0.20
    garment_start = 0
    for row_y in range(img.height):
        row_data = list(alpha.crop((0, row_y, width, row_y + 1)).getdata())
        opaque_count = sum(1 for px in row_data if px > 128)
        if opaque_count >= garment_threshold:
            garment_start = row_y
            break

    # Only crop the hook ABOVE the garment shoulders — small buffer
    crop_y = max(garment_start - 5, 0)
    # Safety: never crop more than 15%
    max_crop = int(img.height * 0.15)
    crop_y = min(crop_y, max_crop)

    if crop_y < 10:
        return img

    return img.crop((0, crop_y, img.width, img.height))


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


def _color_grade(canvas: Image.Image) -> Image.Image:
    """Subtle editorial color grading — warm tone, slight desaturation."""
    img = ImageEnhance.Color(canvas).enhance(0.92)
    warm = Image.new("RGBA", canvas.size, (255, 248, 235, 14))
    img = Image.alpha_composite(img, warm)
    return img


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

    canvas = _color_grade(canvas)
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
