#!/usr/bin/env python3
"""
Reconstruction Overlap A/B Eval

For each test image:
1. Identify all items + bounding boxes (GPT-4o)
2. Find items with overlapping bboxes
3. For overlapping items, reconstruct twice:
   - Baseline: all_items=None (no overlap awareness)
   - Treatment: all_items=items (overlap-aware prompt)
4. Generate side-by-side HTML comparison

Usage:
    # From local directory:
    python tests/outfit_eval/scripts/reconstruction_overlap_eval.py [image_dir] [max_images]

    # From user visualizations:
    python tests/outfit_eval/scripts/reconstruction_overlap_eval.py --users anneka,peichin [max_per_user]
"""

import os
import sys
import base64
import time
import logging
import requests as http_requests
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from PIL import Image

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), '.env'))

os.environ['STORAGE_TYPE'] = 's3'

from services.image_extractor import OutfitItemExtractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def image_to_data_uri(img_bytes: bytes) -> str:
    """Convert image bytes to a data URI for embedding in HTML."""
    b64 = base64.b64encode(img_bytes).decode('utf-8')
    return f"data:image/png;base64,{b64}"


def load_user_viz_images(users: List[str], max_per_user: int = 5) -> List[Tuple[str, bytes]]:
    """Load visualized outfit images from S3 for given users.

    Returns list of (label, image_bytes) tuples.
    """
    from services.saved_outfits_manager import SavedOutfitsManager

    images = []
    for user in users:
        mgr = SavedOutfitsManager(user_id=user)
        outfits = mgr.get_saved_outfits(enrich_with_current_images=False)
        viz_outfits = [o for o in outfits if o.get("visualization_url")]
        # Prefer outfits with more items (more layering)
        viz_outfits.sort(key=lambda o: len(o.get("outfit_data", {}).get("items", [])), reverse=True)
        viz_outfits = viz_outfits[:max_per_user]

        for o in viz_outfits:
            url = o["visualization_url"]
            items = o.get("outfit_data", {}).get("items", [])
            item_names = [i.get("name", "?") for i in items]
            label = f"{user}: {', '.join(item_names[:3])}{'...' if len(item_names) > 3 else ''}"
            try:
                resp = http_requests.get(url, timeout=15)
                resp.raise_for_status()
                images.append((label, resp.content))
                logger.info(f"Downloaded viz for {user}: {len(items)} items — {url.split('/')[-1]}")
            except Exception as e:
                logger.warning(f"Failed to download {url}: {e}")
    return images


def pil_to_bytes(img: Image.Image, fmt: str = "JPEG") -> bytes:
    buf = BytesIO()
    if img.mode == 'RGBA' and fmt == 'JPEG':
        img = img.convert('RGB')
    img.save(buf, format=fmt)
    return buf.getvalue()


def run_eval_from_dir(image_dir: str, max_images: int = 5):
    """Load images from a local directory and run eval."""
    image_dir = Path(image_dir)
    image_files = sorted([
        f for f in image_dir.iterdir()
        if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.heic', '.heif')
    ])[:max_images]

    if not image_files:
        logger.error(f"No images found in {image_dir}")
        return

    images = [(f.name, f.read_bytes()) for f in image_files]
    run_eval(images)


def run_eval(images: List[Tuple[str, bytes]]):
    """Run reconstruction eval on a list of (label, image_bytes) tuples."""
    extractor = OutfitItemExtractor()

    logger.info(f"Running eval on {len(images)} images")

    results = []  # Per-image results

    for label, image_bytes in images:
        logger.info(f"\n{'='*60}\nProcessing: {label}\n{'='*60}")
        source_image = Image.open(BytesIO(image_bytes))

        # Thumbnail the source for HTML embedding
        thumb = source_image.copy()
        thumb.thumbnail((400, 400), Image.Resampling.LANCZOS)
        source_data_uri = image_to_data_uri(pil_to_bytes(thumb))

        # Step 1: Identify items
        items = extractor.identify_items(image_bytes)
        logger.info(f"Found {len(items)} items: {[i['name'] for i in items]}")

        # Step 2: Find overlapping pairs
        overlaps = []
        if len(items) >= 2:
            for i, a in enumerate(items):
                bbox_a = a.get("bbox_pct")
                if not bbox_a:
                    continue
                area_a = (bbox_a[2] - bbox_a[0]) * (bbox_a[3] - bbox_a[1])
                for j, b in enumerate(items):
                    if j <= i:
                        continue
                    bbox_b = b.get("bbox_pct")
                    if not bbox_b:
                        continue
                    if extractor._bboxes_overlap(bbox_a, bbox_b):
                        area_b = (bbox_b[2] - bbox_b[0]) * (bbox_b[3] - bbox_b[1])
                        if area_a >= area_b:
                            overlaps.append({"target": a, "occluder": b})
                        else:
                            overlaps.append({"target": b, "occluder": a})

        # Build set of items that have overlaps (these get A/B)
        items_with_overlaps = set()
        for o in overlaps:
            items_with_overlaps.add(o["target"]["name"])

        logger.info(f"Found {len(overlaps)} overlap pairs, {len(items_with_overlaps)} items with overlaps")
        for o in overlaps:
            logger.info(f"  {o['target']['name']} occluded by {o['occluder']['name']}")

        # Step 3: Reconstruct ALL items
        # - Items with overlaps: baseline (no awareness) vs treatment (overlap-aware)
        # - Items without overlaps: single reconstruction only
        comparisons = []

        for item_info in items:
            item_name = item_info["name"]
            has_overlap = item_name in items_with_overlaps

            logger.info(f"\nReconstructing '{item_name}' {'(A/B — has overlaps)' if has_overlap else '(single — no overlaps)'}...")

            # Extract/crop the item
            item_bytes = extractor.extract_item(
                source_image, item_info["bbox_pct"], item_name, remove_bg=True
            )
            crop_data_uri = image_to_data_uri(item_bytes)
            analysis = {"name": item_name}

            if has_overlap:
                # A/B: baseline vs treatment
                logger.info(f"  Baseline (no overlap awareness)...")
                baseline_prompt = extractor._build_reconstruction_prompt(analysis, item_info, all_items=None)
                baseline_bytes = extractor.reconstruct_garment(
                    item_bytes=item_bytes, analysis=analysis, item_info=item_info,
                    all_items=None,
                )

                logger.info(f"  Treatment (overlap-aware)...")
                treatment_prompt = extractor._build_reconstruction_prompt(analysis, item_info, all_items=items)
                treatment_bytes = extractor.reconstruct_garment(
                    item_bytes=item_bytes, analysis=analysis, item_info=item_info,
                    all_items=items,
                )

                occluders = [o["occluder"]["name"] for o in overlaps if o["target"]["name"] == item_name]
                comparisons.append({
                    "target_name": item_name,
                    "has_overlap": True,
                    "occluders": occluders,
                    "crop_uri": crop_data_uri,
                    "baseline_uri": image_to_data_uri(baseline_bytes) if baseline_bytes else None,
                    "treatment_uri": image_to_data_uri(treatment_bytes) if treatment_bytes else None,
                    "baseline_prompt": baseline_prompt,
                    "treatment_prompt": treatment_prompt,
                })
            else:
                # Single reconstruction (no overlap, so baseline == treatment)
                logger.info(f"  Reconstructing...")
                prompt = extractor._build_reconstruction_prompt(analysis, item_info, all_items=items)
                reconstructed_bytes = extractor.reconstruct_garment(
                    item_bytes=item_bytes, analysis=analysis, item_info=item_info,
                    all_items=items,
                )

                comparisons.append({
                    "target_name": item_name,
                    "has_overlap": False,
                    "occluders": [],
                    "crop_uri": crop_data_uri,
                    "baseline_uri": image_to_data_uri(reconstructed_bytes) if reconstructed_bytes else None,
                    "treatment_uri": None,
                    "baseline_prompt": prompt,
                    "treatment_prompt": None,
                })

        results.append({
            "filename": label,
            "source_uri": source_data_uri,
            "items": items,
            "overlaps": overlaps,
            "comparisons": comparisons,
        })

    # Generate HTML
    generate_html(results)


def generate_html(results: List[Dict]):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(__file__).parent.parent / "results" / f"reconstruction_overlap_{timestamp}.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_comparisons = sum(len(r["comparisons"]) for r in results)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reconstruction Overlap Eval — {timestamp}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #faf9f7; color: #1a1a1a; padding: 24px; max-width: 1400px; margin: 0 auto; }}
  h1 {{ font-size: 26px; font-weight: 600; margin-bottom: 4px; }}
  .subtitle {{ color: #666; font-size: 14px; margin-bottom: 32px; }}
  .image-section {{ margin-bottom: 48px; border: 1px solid #e5e0da; border-radius: 12px; background: white; overflow: hidden; }}
  .image-header {{ padding: 16px 20px; border-bottom: 1px solid #f0ebe5; display: flex; align-items: center; gap: 16px; }}
  .image-header img {{ width: 300px; height: auto; object-fit: contain; border-radius: 8px; }}
  .image-header h2 {{ font-size: 18px; }}
  .image-header .meta {{ color: #888; font-size: 13px; }}
  .no-overlaps {{ padding: 20px; color: #999; font-style: italic; }}
  .comparison {{ display: grid; grid-template-columns: 200px 1fr 1fr; gap: 0; border-top: 1px solid #f0ebe5; }}
  .comparison.single {{ grid-template-columns: 200px 1fr; }}
  .comparison + .comparison {{ border-top: 1px solid #e5e0da; }}
  .comp-crop {{ padding: 16px; border-right: 1px solid #f0ebe5; display: flex; flex-direction: column; align-items: center; gap: 8px; }}
  .comp-crop img {{ width: 160px; aspect-ratio: 3/4; object-fit: contain; border-radius: 6px; background: repeating-conic-gradient(#f0f0f0 0% 25%, white 0% 50%) 50% / 12px 12px; }}
  .comp-col {{ padding: 16px; text-align: center; }}
  .comp-col:last-child {{ border-left: 1px solid #f0ebe5; }}
  .comparison.single .comp-col:last-child {{ border-left: none; }}
  .comp-col img {{ width: 100%; max-width: 320px; aspect-ratio: 1; object-fit: contain; border-radius: 8px; background: white; border: 1px solid #eee; }}
  .label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; padding: 3px 10px; border-radius: 4px; display: inline-block; }}
  .label.crop {{ background: #f0ebe5; color: #8b7355; }}
  .label.baseline {{ background: #e8e8e8; color: #555; }}
  .label.treatment {{ background: #c5705d; color: white; }}
  .item-name {{ font-size: 14px; font-weight: 600; margin-bottom: 4px; }}
  .occluder-info {{ font-size: 12px; color: #c5705d; margin-bottom: 8px; }}
  .prompt-toggle {{ font-size: 11px; color: #888; cursor: pointer; margin-top: 8px; }}
  .prompt-text {{ display: none; font-size: 11px; color: #666; margin-top: 6px; text-align: left; padding: 8px; background: #f8f8f8; border-radius: 4px; max-height: 150px; overflow-y: auto; word-break: break-word; }}
  .failed {{ color: #c5705d; font-style: italic; padding: 40px 0; }}
</style>
</head>
<body>
<h1>Overlap-Aware Reconstruction Eval</h1>
<p class="subtitle">{len(results)} images &middot; {total_comparisons} comparisons &middot; {timestamp}</p>
"""

    for r in results:
        items_str = ", ".join(i["name"] for i in r["items"])
        html += f"""
<div class="image-section">
  <div class="image-header">
    <img src="{r['source_uri']}" alt="source">
    <div>
      <h2>{r['filename']}</h2>
      <div class="meta">{len(r['items'])} items: {items_str}</div>
      <div class="meta">{len(r['items'])} items total, {len(r['overlaps'])} overlap pairs</div>
    </div>
  </div>
"""
        for idx, c in enumerate(r["comparisons"]):
            uid = f"{r['filename']}_{idx}"
            baseline_img = f'<img src="{c["baseline_uri"]}" alt="result">' if c["baseline_uri"] else '<div class="failed">Failed</div>'

            if c["has_overlap"]:
                # A/B row: crop | baseline | treatment
                occluders = ", ".join(c["occluders"])
                treatment_img = f'<img src="{c["treatment_uri"]}" alt="treatment">' if c["treatment_uri"] else '<div class="failed">Failed</div>'

                html += f"""
  <div class="comparison">
    <div class="comp-crop">
      <span class="label crop">Crop</span>
      <div class="item-name">{c['target_name']}</div>
      <div class="occluder-info">Overlapped by: {occluders}</div>
      <img src="{c['crop_uri']}" alt="crop">
    </div>
    <div class="comp-col">
      <span class="label baseline">Baseline</span><br>
      {baseline_img}
      <div class="prompt-toggle" onclick="document.getElementById('bp-{uid}').style.display=document.getElementById('bp-{uid}').style.display==='block'?'none':'block'">Show prompt</div>
      <div class="prompt-text" id="bp-{uid}">{c['baseline_prompt']}</div>
    </div>
    <div class="comp-col">
      <span class="label treatment">Overlap-Aware</span><br>
      {treatment_img}
      <div class="prompt-toggle" onclick="document.getElementById('tp-{uid}').style.display=document.getElementById('tp-{uid}').style.display==='block'?'none':'block'">Show prompt</div>
      <div class="prompt-text" id="tp-{uid}">{c['treatment_prompt']}</div>
    </div>
  </div>
"""
            else:
                # Single row: crop | reconstruction
                html += f"""
  <div class="comparison single">
    <div class="comp-crop">
      <span class="label crop">Crop</span>
      <div class="item-name">{c['target_name']}</div>
      <img src="{c['crop_uri']}" alt="crop">
    </div>
    <div class="comp-col">
      <span class="label baseline">Reconstructed</span><br>
      {baseline_img}
      <div class="prompt-toggle" onclick="document.getElementById('bp-{uid}').style.display=document.getElementById('bp-{uid}').style.display==='block'?'none':'block'">Show prompt</div>
      <div class="prompt-text" id="bp-{uid}">{c['baseline_prompt']}</div>
    </div>
  </div>
"""
        html += "</div>\n"

    html += """
</body>
</html>"""

    output_path.write_text(html)
    logger.info(f"\nHTML report saved to: {output_path}")
    print(f"\n✓ Open: file://{output_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--users":
        users = sys.argv[2].split(",") if len(sys.argv) > 2 else ["anneka", "peichin"]
        max_per_user = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        images = load_user_viz_images(users, max_per_user)
        run_eval(images)
    else:
        image_dir = sys.argv[1] if len(sys.argv) > 1 else "/Users/peichin/Downloads/Clothing"
        max_images = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        run_eval_from_dir(image_dir, max_images)
