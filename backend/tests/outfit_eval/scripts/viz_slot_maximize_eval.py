#!/usr/bin/env python3
"""
Visualization A/B Test: Single Collage vs Multi-Collage Slot Maximization

Compares two approaches for multi-item outfit visualization:
- Baseline: Single collage of ALL items (346px per item, 1 slot used)
- Treatment: Three collages of 2 items each (525px per item, all 3 slots used)

Hypothesis: Higher per-item resolution (52% more pixels) = better fidelity

Outputs an HTML comparison for manual evaluation.

Usage:
    python tests/outfit_eval/scripts/viz_slot_maximize_eval.py

Does NOT modify production code.
"""

import os
import sys
import uuid
import time
import logging
from datetime import datetime
from io import BytesIO
from typing import List, Dict, Optional, Tuple
from PIL import Image
import requests

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), '.env'))

# Set S3 storage before imports
os.environ['STORAGE_TYPE'] = 's3'

from services.saved_outfits_manager import SavedOutfitsManager
from services.user_profile_manager import UserProfileManager
from services.storage_manager import StorageManager
from services.visualization.providers.runway import RunwayProvider
from services.visualization.providers.base import ImageGenerationRequest

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Collage settings
CANVAS_SIZE = 1080  # Square canvas for Runway
BACKGROUND = (240, 240, 240)  # Neutral gray
PADDING = 10


def download_image(url: str) -> Optional[Image.Image]:
    """Download image from URL and return PIL Image."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, BACKGROUND)
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        return img
    except Exception as e:
        logger.warning(f"Failed to download {url}: {e}")
        return None


def crop_to_fill(img: Image.Image, target_size: int) -> Image.Image:
    """Crop and resize image to fill target square."""
    width_ratio = target_size / img.width
    height_ratio = target_size / img.height
    scale = max(width_ratio, height_ratio)

    new_width = int(img.width * scale)
    new_height = int(img.height * scale)
    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    left = (new_width - target_size) // 2
    top = (new_height - target_size) // 2
    return resized.crop((left, top, left + target_size, top + target_size))


def generate_single_collage(image_urls: List[str]) -> Optional[Image.Image]:
    """
    Generate a single collage of ALL items (current production approach).

    For 6 items: 2x3 grid = 346px per item
    """
    images = []
    for url in image_urls:
        img = download_image(url)
        if img:
            images.append(img)

    if not images:
        return None

    num_images = len(images)

    # Calculate grid size
    if num_images <= 4:
        cols, rows = 2, 2
    elif num_images <= 6:
        cols, rows = 3, 2
    else:
        cols, rows = 3, 3

    # Calculate cell size
    cell_size = (CANVAS_SIZE - (cols + 1) * PADDING) // cols

    # Create canvas
    canvas = Image.new('RGB', (CANVAS_SIZE, CANVAS_SIZE), BACKGROUND)

    # Place images
    for idx, img in enumerate(images):
        if idx >= cols * rows:
            break

        row = idx // cols
        col = idx % cols

        cropped = crop_to_fill(img, cell_size)

        x = PADDING + col * (cell_size + PADDING)
        y = PADDING + row * (cell_size + PADDING)

        canvas.paste(cropped, (x, y))

    return canvas


def generate_slot_collage(image_urls: List[str]) -> Optional[Image.Image]:
    """
    Generate a collage for a single Runway slot (1-3 items).

    Layout adapts to item count:
    - 1 item: centered, 700px
    - 2 items: side by side, 525px each
    - 3 items: 1x3 row, 346px each

    Canvas: 1080x1080 (Runway native)
    """
    images = []
    for url in image_urls[:3]:  # Max 3 items per slot
        img = download_image(url)
        if img:
            images.append(img)

    if not images:
        return None

    num_images = len(images)
    canvas = Image.new('RGB', (CANVAS_SIZE, CANVAS_SIZE), BACKGROUND)

    if num_images == 1:
        # Single item: centered, large
        cell_size = 700
        img = crop_to_fill(images[0], cell_size)
        x = (CANVAS_SIZE - cell_size) // 2
        y = (CANVAS_SIZE - cell_size) // 2
        canvas.paste(img, (x, y))

    elif num_images == 2:
        # 2 items side by side: 525px each
        cell_size = (CANVAS_SIZE - 3 * PADDING) // 2
        y = (CANVAS_SIZE - cell_size) // 2
        for idx, img in enumerate(images):
            cropped = crop_to_fill(img, cell_size)
            x = PADDING + idx * (cell_size + PADDING)
            canvas.paste(cropped, (x, y))

    else:  # 3 items
        # 3 items in a row: 346px each
        cell_size = (CANVAS_SIZE - 4 * PADDING) // 3
        y = (CANVAS_SIZE - cell_size) // 2
        for idx, img in enumerate(images):
            cropped = crop_to_fill(img, cell_size)
            x = PADDING + idx * (cell_size + PADDING)
            canvas.paste(cropped, (x, y))

    return canvas


def generate_multi_collages(image_urls: List[str]) -> List[Image.Image]:
    """
    Distribute items across up to 3 Runway slots for maximum fidelity.

    Distribution strategy (fills 3 slots, puts extras in last slot):
    - 4 items: 2 + 2 (2 collages)
    - 5 items: 2 + 2 + 1 (3 collages)
    - 6 items: 2 + 2 + 2 (3 collages)
    - 7 items: 2 + 2 + 3 (3 collages)
    - 8+ items: 3 + 3 + rest (3 collages)

    Returns list of PIL Images (max 3).
    """
    n = len(image_urls)

    if n <= 3:
        # Just use individual images (no collaging needed)
        collages = []
        for url in image_urls:
            collage = generate_slot_collage([url])
            if collage:
                collages.append(collage)
        return collages

    # Determine distribution
    if n == 4:
        distribution = [2, 2]
    elif n == 5:
        distribution = [2, 2, 1]
    elif n == 6:
        distribution = [2, 2, 2]
    elif n == 7:
        distribution = [2, 2, 3]
    else:  # 8+
        distribution = [3, 3, n - 6]  # First two get 3, last gets remainder

    collages = []
    idx = 0
    for count in distribution:
        slot_urls = image_urls[idx:idx + count]
        collage = generate_slot_collage(slot_urls)
        if collage:
            collages.append(collage)
        idx += count

    return collages[:3]  # Max 3 for Runway


def run_visualization(
    runway: RunwayProvider,
    images: List[str],
    descriptor: str
) -> Tuple[Optional[str], float]:
    """
    Run Runway visualization and return (url, latency).
    """
    request = ImageGenerationRequest(
        garment_images=images,
        prompt_text="",
        style_profile={},
        styling_notes="",
        mode="model"
    )

    start_time = time.time()
    result = runway.generate_image(request, model_descriptor=descriptor)
    latency = time.time() - start_time

    if result.success:
        return result.image_url, latency
    else:
        logger.error(f"Visualization failed: {result.error_message}")
        return None, latency


def get_test_outfits(users: List[str], max_per_user: int = 2) -> List[Dict]:
    """
    Get saved outfits with exactly 6 items for testing.
    (6 items = perfect split into 3 pairs)
    """
    test_outfits = []

    for user_id in users:
        som = SavedOutfitsManager(user_id=user_id)
        outfits = som.get_saved_outfits()

        # Prefer 6 items, accept 5-7
        multi_item = [o for o in outfits if 5 <= len(o.get('outfit_data', {}).get('items', [])) <= 7]

        # Get user descriptor
        profile_manager = UserProfileManager(user_id=user_id)
        profile = profile_manager.get_profile(user_id)
        descriptor = profile.get('model_descriptor', '') if profile else ''

        for outfit in multi_item[:max_per_user]:
            items = outfit.get('outfit_data', {}).get('items', [])
            image_urls = [item.get('image_path') for item in items if item.get('image_path')]

            test_outfits.append({
                'id': outfit.get('id', str(uuid.uuid4())[:8]),
                'user_id': user_id,
                'descriptor': descriptor,
                'items': items,
                'image_urls': image_urls,
                'styling_notes': outfit.get('outfit_data', {}).get('styling_notes', '')
            })

    return test_outfits


def generate_comparison_html(results: List[Dict], output_path: str):
    """
    Generate HTML comparison report.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Visualization A/B: Single vs Multi-Collage Slot Maximization</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        .summary {{
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-stats {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 15px;
        }}
        .stat-box {{
            padding: 15px;
            border-radius: 6px;
        }}
        .stat-box.baseline {{ background: #e3f2fd; }}
        .stat-box.treatment {{ background: #e8f5e9; }}
        .stat-box h4 {{ margin: 0 0 8px 0; font-size: 14px; }}
        .stat-box p {{ margin: 0; font-size: 13px; color: #555; }}
        .outfit-card {{
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 30px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .outfit-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }}
        .outfit-title {{ font-size: 18px; font-weight: 600; color: #333; }}
        .outfit-meta {{ color: #666; font-size: 14px; }}
        .input-comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 25px;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 8px;
        }}
        .input-section h4 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #555;
        }}
        .collage-grid {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .collage-preview {{
            width: 150px;
            height: 150px;
            object-fit: cover;
            border-radius: 6px;
            border: 1px solid #ddd;
        }}
        .collage-preview.large {{
            width: 200px;
            height: 200px;
        }}
        .items-list {{
            font-size: 12px;
            line-height: 1.5;
            max-height: 200px;
            overflow-y: auto;
        }}
        .items-list li {{ margin-bottom: 3px; }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .viz-column {{
            text-align: center;
        }}
        .viz-column h3 {{
            margin: 0 0 15px 0;
            padding: 10px;
            border-radius: 6px;
            font-size: 14px;
        }}
        .viz-column.baseline h3 {{ background: #e3f2fd; color: #1565c0; }}
        .viz-column.treatment h3 {{ background: #e8f5e9; color: #2e7d32; }}
        .viz-image {{
            width: 100%;
            max-width: 450px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}
        .viz-meta {{
            margin-top: 10px;
            font-size: 12px;
            color: #666;
        }}
        .rating-section {{
            margin-top: 20px;
            padding: 15px;
            background: #fafafa;
            border-radius: 8px;
        }}
        .rating-section h4 {{ margin: 0 0 10px 0; font-size: 14px; }}
        .rating-buttons {{
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }}
        .rating-btn {{
            padding: 8px 16px;
            border: 2px solid #ddd;
            border-radius: 6px;
            background: #fff;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }}
        .rating-btn:hover {{ border-color: #999; }}
        .rating-btn.selected {{ border-color: #4CAF50; background: #E8F5E9; }}
        .fidelity-checks {{
            display: flex;
            gap: 20px;
            margin: 15px 0;
            font-size: 13px;
        }}
        .fidelity-checks label {{ display: flex; gap: 5px; align-items: center; }}
        .notes-input {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            resize: vertical;
        }}
        .error {{ color: #d32f2f; font-style: italic; }}
        .pixel-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .pixel-badge.low {{ background: #ffecb3; color: #f57f17; }}
        .pixel-badge.high {{ background: #c8e6c9; color: #2e7d32; }}
    </style>
</head>
<body>
    <h1>Visualization A/B: Single vs Multi-Collage Slot Maximization</h1>

    <div class="summary">
        <strong>Generated:</strong> {timestamp}<br>
        <strong>Outfits tested:</strong> {len(results)}<br><br>
        <strong>Hypothesis:</strong> Higher per-item resolution produces higher fidelity visualizations.

        <div class="summary-stats">
            <div class="stat-box baseline">
                <h4>BASELINE: Single Collage (Current)</h4>
                <p>All items in one 2x3 grid collage</p>
                <p><span class="pixel-badge low">346px per item</span> &middot; Uses 1 of 3 Runway slots</p>
            </div>
            <div class="stat-box treatment">
                <h4>TREATMENT: Multi-Collage (New)</h4>
                <p>Items split into 3 collages (2 items each)</p>
                <p><span class="pixel-badge high">525px per item</span> &middot; Uses all 3 Runway slots</p>
                <p><strong>+52% more pixels per item</strong></p>
            </div>
        </div>
    </div>
"""

    for idx, result in enumerate(results, 1):
        outfit = result['outfit']
        baseline = result.get('baseline', {})
        treatment = result.get('treatment', {})
        single_collage_url = result.get('single_collage_url', '')
        multi_collage_urls = result.get('multi_collage_urls', [])

        items_html = "\n".join([f"<li>{item.get('name', 'Unknown item')}</li>" for item in outfit['items']])

        baseline_img = f'<img src="{baseline.get("url", "")}" class="viz-image" />' if baseline.get('url') else '<p class="error">Generation failed</p>'
        treatment_img = f'<img src="{treatment.get("url", "")}" class="viz-image" />' if treatment.get('url') else '<p class="error">Generation failed</p>'

        multi_collages_html = "\n".join([
            f'<img src="{url}" class="collage-preview" alt="Pair collage {i+1}" />'
            for i, url in enumerate(multi_collage_urls)
        ])

        html += f"""
    <div class="outfit-card" id="outfit-{idx}">
        <div class="outfit-header">
            <div>
                <div class="outfit-title">Outfit {idx}: {len(outfit['items'])} items</div>
                <div class="outfit-meta">User: {outfit['user_id']} | ID: {outfit['id'][:8]}</div>
            </div>
        </div>

        <div class="input-comparison">
            <div class="input-section">
                <h4>BASELINE INPUT: Single Collage <span class="pixel-badge low">346px/item</span></h4>
                <img src="{single_collage_url}" class="collage-preview large" alt="Single collage" />
            </div>
            <div class="input-section">
                <h4>TREATMENT INPUT: 3 Pair Collages <span class="pixel-badge high">525px/item</span></h4>
                <div class="collage-grid">
                    {multi_collages_html}
                </div>
            </div>
        </div>

        <div style="padding: 10px; background: #f9f9f9; margin-bottom: 15px; border-radius: 6px;">
            <strong>Items:</strong>
            <ol class="items-list" style="margin: 5px 0 0 20px; columns: 2;">
                {items_html}
            </ol>
        </div>

        <div class="comparison-grid">
            <div class="viz-column baseline">
                <h3>BASELINE: Single Collage (1 slot)</h3>
                {baseline_img}
                <div class="viz-meta">
                    Latency: {baseline.get('latency', 0):.1f}s
                </div>
            </div>
            <div class="viz-column treatment">
                <h3>TREATMENT: Multi-Collage (3 slots)</h3>
                {treatment_img}
                <div class="viz-meta">
                    Latency: {treatment.get('latency', 0):.1f}s
                </div>
            </div>
        </div>

        <div class="rating-section">
            <h4>Which visualization shows better FIDELITY?</h4>
            <div class="rating-buttons">
                <button class="rating-btn" onclick="rate({idx}, 'baseline')">Single Collage (baseline)</button>
                <button class="rating-btn" onclick="rate({idx}, 'multi')">Multi-Collage (treatment)</button>
                <button class="rating-btn" onclick="rate({idx}, 'tie')">No difference</button>
            </div>

            <div class="fidelity-checks">
                <label><input type="checkbox" id="pattern-{idx}"> Pattern/texture more visible</label>
                <label><input type="checkbox" id="detail-{idx}"> Fine details (buttons, hardware) clearer</label>
                <label><input type="checkbox" id="color-{idx}"> Colors more accurate</label>
            </div>

            <textarea class="notes-input" placeholder="Notes: What differences do you see in fidelity?" rows="2" id="notes-{idx}"></textarea>
        </div>
    </div>
"""

    html += """
    <script>
        const ratings = {};

        function rate(outfitIdx, choice) {
            ratings[outfitIdx] = {
                choice: choice,
                pattern: document.getElementById('pattern-' + outfitIdx).checked,
                detail: document.getElementById('detail-' + outfitIdx).checked,
                color: document.getElementById('color-' + outfitIdx).checked,
                notes: document.getElementById('notes-' + outfitIdx).value
            };

            // Update button styles
            const buttons = document.querySelectorAll(`#outfit-${outfitIdx} .rating-btn`);
            buttons.forEach(btn => btn.classList.remove('selected'));
            event.target.classList.add('selected');

            // Log for easy copy
            console.log('Ratings:', JSON.stringify(ratings, null, 2));
        }
    </script>
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)

    logger.info(f"HTML report saved to: {output_path}")


def main():
    """Run the visualization A/B evaluation."""
    logger.info("=" * 70)
    logger.info("Visualization A/B Test: Single Collage vs Multi-Collage Slot Max")
    logger.info("=" * 70)

    # Initialize Runway
    runway = RunwayProvider()
    if not runway.is_configured():
        logger.error("RUNWAY_API_KEY not set. Cannot run evaluation.")
        return

    # Get test outfits (3 total with 5-7 items)
    test_outfits = get_test_outfits(['peichin', 'dana'], max_per_user=2)[:3]

    if not test_outfits:
        logger.error("No test outfits found with 5-7 items")
        return

    logger.info(f"Found {len(test_outfits)} test outfits")

    # Storage for collage uploads
    storage = StorageManager(storage_type='s3', user_id='eval')

    results = []

    for idx, outfit in enumerate(test_outfits, 1):
        logger.info(f"\n--- Outfit {idx}/{len(test_outfits)}: {outfit['id'][:8]} ({len(outfit['items'])} items) ---")

        image_urls = outfit['image_urls']
        descriptor = outfit['descriptor']

        # === BASELINE: Single collage ===
        logger.info("Generating BASELINE: single collage (346px/item)...")
        single_collage = generate_single_collage(image_urls)

        if not single_collage:
            logger.error("Failed to generate single collage")
            continue

        single_filename = f"eval_single_{uuid.uuid4().hex[:8]}.jpg"
        single_collage_url = storage.save_image(single_collage, single_filename, subfolder="eval")
        logger.info(f"Single collage uploaded: {single_collage_url}")

        logger.info("Running BASELINE visualization...")
        baseline_url, baseline_latency = run_visualization(runway, [single_collage_url], descriptor)
        logger.info(f"Baseline: {'success' if baseline_url else 'FAILED'}, {baseline_latency:.1f}s")

        # Small delay
        time.sleep(3)

        # === TREATMENT: Multi-collage ===
        logger.info("Generating TREATMENT: multi-collage (525px/item)...")
        multi_collages = generate_multi_collages(image_urls)

        if not multi_collages:
            logger.error("Failed to generate multi-collages")
            continue

        # Upload each collage
        multi_collage_urls = []
        for i, collage in enumerate(multi_collages):
            filename = f"eval_multi_{uuid.uuid4().hex[:8]}_{i+1}.jpg"
            url = storage.save_image(collage, filename, subfolder="eval")
            multi_collage_urls.append(url)
            logger.info(f"Multi-collage {i+1} uploaded: {url}")

        logger.info(f"Running TREATMENT visualization with {len(multi_collage_urls)} collages...")
        treatment_url, treatment_latency = run_visualization(runway, multi_collage_urls, descriptor)
        logger.info(f"Treatment: {'success' if treatment_url else 'FAILED'}, {treatment_latency:.1f}s")

        results.append({
            'outfit': outfit,
            'single_collage_url': single_collage_url,
            'multi_collage_urls': multi_collage_urls,
            'baseline': {
                'url': baseline_url,
                'latency': baseline_latency
            },
            'treatment': {
                'url': treatment_url,
                'latency': treatment_latency
            }
        })

        # Delay between outfits
        if idx < len(test_outfits):
            time.sleep(3)

    # Generate HTML report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"tests/outfit_eval/results/viz_slot_maximize_{timestamp}.html"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    generate_comparison_html(results, output_path)

    logger.info("\n" + "=" * 70)
    logger.info(f"Evaluation complete! {len(results)} outfits tested.")
    logger.info(f"HTML report: {output_path}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
