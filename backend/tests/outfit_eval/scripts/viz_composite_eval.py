#!/usr/bin/env python3
"""
Visualization A/B Test: Smart Selection vs Pre-Composite

Compares two approaches for multi-item outfit visualization:
- Baseline: First 2 + Last 1 images (current production smart selection)
- Treatment: Flat-lay collage of ALL items

Outputs an HTML comparison for manual evaluation.

Usage:
    python tests/outfit_eval/scripts/viz_composite_eval.py

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

# Set S3 storage before imports
os.environ['STORAGE_TYPE'] = 's3'

from services.saved_outfits_manager import SavedOutfitsManager
from services.user_profile_manager import UserProfileManager
from services.storage_manager import StorageManager
from services.visualization.providers.runway import RunwayProvider
from services.visualization.providers.base import ImageGenerationRequest

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flat-lay collage settings
FLATLAY_CANVAS_SIZE = 1080  # Square canvas for Runway
FLATLAY_BACKGROUND = (240, 240, 240)  # Neutral gray
FLATLAY_PADDING = 10


def download_image(url: str) -> Optional[Image.Image]:
    """Download image from URL and return PIL Image."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, FLATLAY_BACKGROUND)
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


def generate_flatlay_collage(image_urls: List[str]) -> Optional[Image.Image]:
    """
    Generate a flat-lay collage of ALL outfit items.

    Layout: 3x3 grid (fits up to 9 items)
    Canvas: 1080x1080 (Runway native)
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
    cell_size = (FLATLAY_CANVAS_SIZE - (cols + 1) * FLATLAY_PADDING) // cols

    # Create canvas
    canvas = Image.new('RGB', (FLATLAY_CANVAS_SIZE, FLATLAY_CANVAS_SIZE), FLATLAY_BACKGROUND)

    # Place images
    for idx, img in enumerate(images):
        if idx >= cols * rows:
            break

        row = idx // cols
        col = idx % cols

        cropped = crop_to_fill(img, cell_size)

        x = FLATLAY_PADDING + col * (cell_size + FLATLAY_PADDING)
        y = FLATLAY_PADDING + row * (cell_size + FLATLAY_PADDING)

        canvas.paste(cropped, (x, y))

    return canvas


def smart_select_images(image_urls: List[str]) -> List[str]:
    """
    Smart selection: first 2 + last 1 (current production approach).
    """
    if len(image_urls) <= 3:
        return image_urls
    return image_urls[:2] + [image_urls[-1]]


def run_visualization(
    runway: RunwayProvider,
    images: List[str],
    descriptor: str,
    is_composite: bool = False
) -> Tuple[Optional[str], float]:
    """
    Run Runway visualization and return (url, latency).

    Args:
        runway: RunwayProvider instance
        images: List of image URLs (or single composite URL)
        descriptor: Model descriptor
        is_composite: If True, images is a single composite
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


def get_test_outfits(users: List[str], max_per_user: int = 3) -> List[Dict]:
    """
    Get saved outfits with 5+ items for testing.
    """
    test_outfits = []

    for user_id in users:
        som = SavedOutfitsManager(user_id=user_id)
        outfits = som.get_saved_outfits()

        # Filter to 5+ items
        multi_item = [o for o in outfits if len(o.get('outfit_data', {}).get('items', [])) >= 5]

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
    <title>Visualization A/B: Smart Selection vs Pre-Composite</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1400px;
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
        .input-section {{
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 20px;
            margin-bottom: 25px;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 8px;
        }}
        .flatlay-preview {{
            width: 300px;
            height: 300px;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid #ddd;
        }}
        .items-list {{
            font-size: 13px;
            line-height: 1.6;
        }}
        .items-list h4 {{ margin: 0 0 10px 0; color: #555; }}
        .items-list li {{ margin-bottom: 4px; }}
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
            max-width: 400px;
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
        .notes-input {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            resize: vertical;
        }}
        .error {{ color: #d32f2f; font-style: italic; }}
        .descriptor-preview {{
            font-size: 12px;
            color: #888;
            margin-top: 5px;
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
    </style>
</head>
<body>
    <h1>Visualization A/B Test: Smart Selection vs Pre-Composite</h1>

    <div class="summary">
        <strong>Generated:</strong> {timestamp}<br>
        <strong>Outfits tested:</strong> {len(results)}<br>
        <strong>Approach A (Baseline):</strong> First 2 + Last 1 images → Runway<br>
        <strong>Approach B (Treatment):</strong> Flat-lay collage of ALL items → Runway
    </div>
"""

    for idx, result in enumerate(results, 1):
        outfit = result['outfit']
        baseline = result.get('baseline', {})
        treatment = result.get('treatment', {})
        flatlay_url = result.get('flatlay_url', '')

        items_html = "\n".join([f"<li>{item.get('name', 'Unknown item')}</li>" for item in outfit['items']])

        baseline_img = f'<img src="{baseline.get("url", "")}" class="viz-image" />' if baseline.get('url') else '<p class="error">Generation failed</p>'
        treatment_img = f'<img src="{treatment.get("url", "")}" class="viz-image" />' if treatment.get('url') else '<p class="error">Generation failed</p>'

        descriptor_preview = (outfit['descriptor'][:80] + '...') if len(outfit['descriptor']) > 80 else outfit['descriptor']

        html += f"""
    <div class="outfit-card" id="outfit-{idx}">
        <div class="outfit-header">
            <div>
                <div class="outfit-title">Outfit {idx}: {len(outfit['items'])} items</div>
                <div class="outfit-meta">User: {outfit['user_id']} | ID: {outfit['id'][:8]}</div>
                <div class="descriptor-preview">Descriptor: {descriptor_preview or '(none)'}</div>
            </div>
        </div>

        <div class="input-section">
            <div>
                <img src="{flatlay_url}" class="flatlay-preview" alt="Flat-lay of all items" />
                <div style="text-align: center; font-size: 12px; color: #666; margin-top: 5px;">
                    Flat-lay input ({len(outfit['items'])} items)
                </div>
            </div>
            <div class="items-list">
                <h4>Items in outfit:</h4>
                <ol>{items_html}</ol>
            </div>
        </div>

        <div class="comparison-grid">
            <div class="viz-column baseline">
                <h3>BASELINE: Smart Selection (3 images)</h3>
                {baseline_img}
                <div class="viz-meta">
                    Latency: {baseline.get('latency', 0):.1f}s |
                    Images sent: {baseline.get('num_images', 0)}
                </div>
            </div>
            <div class="viz-column treatment">
                <h3>TREATMENT: Pre-Composite (1 flat-lay)</h3>
                {treatment_img}
                <div class="viz-meta">
                    Latency: {treatment.get('latency', 0):.1f}s |
                    Images sent: 1 (composite of {len(outfit['items'])})
                </div>
            </div>
        </div>

        <div class="rating-section">
            <h4>Which visualization is better?</h4>
            <div class="rating-buttons">
                <button class="rating-btn" onclick="rate({idx}, 'baseline')">Baseline (3 images)</button>
                <button class="rating-btn" onclick="rate({idx}, 'treatment')">Pre-Composite</button>
                <button class="rating-btn" onclick="rate({idx}, 'tie')">Tie / No difference</button>
            </div>
            <textarea class="notes-input" placeholder="Notes (optional): What items are visible? Any quality differences?" rows="2" id="notes-{idx}"></textarea>
        </div>
    </div>
"""

    html += """
    <script>
        const ratings = {};

        function rate(outfitIdx, choice) {
            ratings[outfitIdx] = {
                choice: choice,
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
    logger.info("=" * 60)
    logger.info("Visualization A/B Test: Smart Selection vs Pre-Composite")
    logger.info("=" * 60)

    # Initialize Runway
    runway = RunwayProvider()
    if not runway.is_configured():
        logger.error("RUNWAY_API_KEY not set. Cannot run evaluation.")
        return

    # Get test outfits (5 total: 3 from peichin, 2 from dana)
    test_outfits = get_test_outfits(['peichin', 'dana'], max_per_user=3)[:5]

    if not test_outfits:
        logger.error("No test outfits found with 5+ items")
        return

    logger.info(f"Found {len(test_outfits)} test outfits")

    # Storage for collage uploads
    storage = StorageManager(storage_type='s3', user_id='eval')

    results = []

    for idx, outfit in enumerate(test_outfits, 1):
        logger.info(f"\n--- Outfit {idx}/{len(test_outfits)}: {outfit['id'][:8]} ({len(outfit['items'])} items) ---")

        image_urls = outfit['image_urls']
        descriptor = outfit['descriptor']

        # Generate flat-lay collage
        logger.info("Generating flat-lay collage...")
        flatlay = generate_flatlay_collage(image_urls)

        if not flatlay:
            logger.error("Failed to generate flat-lay collage")
            continue

        # Upload collage to S3
        flatlay_filename = f"eval_flatlay_{uuid.uuid4().hex[:8]}.jpg"
        flatlay_url = storage.save_image(flatlay, flatlay_filename, subfolder="eval")
        logger.info(f"Flat-lay uploaded: {flatlay_url}")

        # Run baseline (smart selection: first 2 + last 1)
        logger.info("Running BASELINE visualization (smart selection)...")
        baseline_images = smart_select_images(image_urls)
        baseline_url, baseline_latency = run_visualization(runway, baseline_images, descriptor)
        logger.info(f"Baseline: {'success' if baseline_url else 'FAILED'}, {baseline_latency:.1f}s")

        # Small delay between API calls
        time.sleep(2)

        # Run treatment (pre-composite flat-lay)
        logger.info("Running TREATMENT visualization (pre-composite)...")
        treatment_url, treatment_latency = run_visualization(runway, [flatlay_url], descriptor, is_composite=True)
        logger.info(f"Treatment: {'success' if treatment_url else 'FAILED'}, {treatment_latency:.1f}s")

        results.append({
            'outfit': outfit,
            'flatlay_url': flatlay_url,
            'baseline': {
                'url': baseline_url,
                'latency': baseline_latency,
                'num_images': len(baseline_images)
            },
            'treatment': {
                'url': treatment_url,
                'latency': treatment_latency,
                'num_images': 1
            }
        })

        # Delay between outfits
        if idx < len(test_outfits):
            time.sleep(3)

    # Generate HTML report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"tests/outfit_eval/results/viz_composite_eval_{timestamp}.html"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    generate_comparison_html(results, output_path)

    logger.info("\n" + "=" * 60)
    logger.info(f"Evaluation complete! {len(results)} outfits tested.")
    logger.info(f"HTML report: {output_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
