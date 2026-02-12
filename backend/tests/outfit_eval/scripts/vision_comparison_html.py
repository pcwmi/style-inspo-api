#!/usr/bin/env python3
"""Generate HTML comparison of text-only vs vision-informed outfit generation."""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

os.environ['STORAGE_TYPE'] = 's3'

from dotenv import load_dotenv
load_dotenv()

from services.style_engine import StyleGenerationEngine
from services.wardrobe_manager import WardrobeManager


def get_image_url(item_name, wardrobe_items):
    """Find image URL for an item by name (fuzzy match)."""
    item_name_lower = item_name.lower().strip()
    for item in wardrobe_items:
        name = item.get('styling_details', {}).get('name', '')
        if name.lower().strip() == item_name_lower:
            return item.get('system_metadata', {}).get('image_path', '')
    # Fuzzy fallback
    for item in wardrobe_items:
        name = item.get('styling_details', {}).get('name', '')
        if item_name_lower in name.lower() or name.lower() in item_name_lower:
            return item.get('system_metadata', {}).get('image_path', '')
    return ''


def generate_html(results, wardrobe_items, output_path):
    """Generate side-by-side HTML comparison."""

    html = """<!DOCTYPE html>
<html>
<head>
    <title>Vision A/B Test Comparison</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px; background: #f5f5f5;
        }
        h1 { text-align: center; color: #333; }
        .stats {
            display: flex; justify-content: center; gap: 40px;
            margin: 20px 0; padding: 15px; background: white; border-radius: 8px;
        }
        .stat { text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #2196F3; }
        .stat-label { font-size: 12px; color: #666; }

        .comparison { margin: 30px 0; }
        .outfit-row {
            display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
            margin: 20px 0; background: white; border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;
        }
        .outfit-card { padding: 20px; }
        .outfit-card.control { border-right: 1px solid #eee; }
        .outfit-card.treatment { background: #f8fff8; }

        .variant-label {
            display: inline-block; padding: 4px 12px; border-radius: 20px;
            font-size: 12px; font-weight: bold; margin-bottom: 15px;
        }
        .control .variant-label { background: #e3f2fd; color: #1565c0; }
        .treatment .variant-label { background: #e8f5e9; color: #2e7d32; }

        .outfit-number {
            font-size: 14px; color: #999; margin-bottom: 10px;
            border-bottom: 1px solid #eee; padding-bottom: 10px;
        }

        .item-images {
            display: flex; flex-wrap: wrap; gap: 10px; margin: 15px 0;
        }
        .item-image {
            width: 80px; height: 80px; object-fit: cover; border-radius: 8px;
            border: 1px solid #ddd;
        }
        .item-image:hover { transform: scale(2); z-index: 100; position: relative; }

        .item-names {
            font-size: 14px; color: #333; margin: 10px 0;
            line-height: 1.6;
        }
        .item-names span {
            display: inline-block; background: #f0f0f0; padding: 2px 8px;
            border-radius: 4px; margin: 2px;
        }

        .section-label {
            font-size: 11px; color: #999; text-transform: uppercase;
            margin-top: 15px; margin-bottom: 5px;
        }
        .styling-notes, .why-works, .physical {
            font-size: 13px; color: #555; line-height: 1.5;
            background: #fafafa; padding: 10px; border-radius: 6px;
            margin: 5px 0;
        }
        .physical { background: #fff3e0; border-left: 3px solid #ff9800; }
        .physical strong { color: #e65100; }

        .no-physical {
            font-style: italic; color: #999; font-size: 12px;
            padding: 10px; background: #fafafa; border-radius: 6px;
        }
    </style>
</head>
<body>
    <h1>🧪 Vision A/B Test: Text-Only vs Vision-Informed</h1>

    <div class="stats">
        <div class="stat">
            <div class="stat-value">25</div>
            <div class="stat-label">Wardrobe Items</div>
        </div>
        <div class="stat">
            <div class="stat-value">3</div>
            <div class="stat-label">Outfits per Variant</div>
        </div>
    </div>
"""

    control_outfits = results.get('TEXT-ONLY (Control)', [])
    treatment_outfits = results.get('VISION (Treatment)', [])

    max_outfits = max(len(control_outfits), len(treatment_outfits))

    html += '<div class="comparison">'

    for i in range(max_outfits):
        html += f'<div class="outfit-row">'

        # Control (Text-Only)
        html += '<div class="outfit-card control">'
        html += '<span class="variant-label">📝 TEXT-ONLY (Control)</span>'
        html += f'<div class="outfit-number">Outfit {i+1}</div>'

        if i < len(control_outfits):
            outfit = control_outfits[i]
            items = outfit.get('items', [])

            # Images
            html += '<div class="item-images">'
            for item_name in items:
                img_url = get_image_url(item_name, wardrobe_items)
                if img_url:
                    html += f'<img class="item-image" src="{img_url}" alt="{item_name}" title="{item_name}">'
            html += '</div>'

            # Item names
            html += '<div class="item-names">'
            for item_name in items:
                html += f'<span>{item_name}</span>'
            html += '</div>'

            # Styling notes
            html += '<div class="section-label">Styling Notes</div>'
            html += f'<div class="styling-notes">{outfit.get("styling_notes", "N/A")}</div>'

            # Why it works
            html += '<div class="section-label">Why It Works</div>'
            html += f'<div class="why-works">{outfit.get("why_it_works", "N/A")}</div>'

            # Physical sensibility (text-only doesn't have this)
            html += '<div class="section-label">Physical Sensibility</div>'
            html += '<div class="no-physical">Not included in text-only prompt</div>'

        html += '</div>'

        # Treatment (Vision)
        html += '<div class="outfit-card treatment">'
        html += '<span class="variant-label">🖼️ VISION (Treatment)</span>'
        html += f'<div class="outfit-number">Outfit {i+1}</div>'

        if i < len(treatment_outfits):
            outfit = treatment_outfits[i]
            items = outfit.get('items', [])

            # Images
            html += '<div class="item-images">'
            for item_name in items:
                img_url = get_image_url(item_name, wardrobe_items)
                if img_url:
                    html += f'<img class="item-image" src="{img_url}" alt="{item_name}" title="{item_name}">'
            html += '</div>'

            # Item names
            html += '<div class="item-names">'
            for item_name in items:
                html += f'<span>{item_name}</span>'
            html += '</div>'

            # Styling notes
            html += '<div class="section-label">Styling Notes</div>'
            html += f'<div class="styling-notes">{outfit.get("styling_notes", "N/A")}</div>'

            # Why it works
            html += '<div class="section-label">Why It Works</div>'
            html += f'<div class="why-works">{outfit.get("why_it_works", "N/A")}</div>'

            # Physical sensibility
            principles = outfit.get('constitution_principles', {})
            phys = principles.get('physical_sensibility', '')
            html += '<div class="section-label">Physical Sensibility</div>'
            if phys:
                html += f'<div class="physical"><strong>✓</strong> {phys}</div>'
            else:
                html += '<div class="no-physical">Not provided</div>'

        html += '</div>'
        html += '</div>'  # outfit-row

    html += '</div>'  # comparison
    html += '</body></html>'

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ HTML saved to: {output_path}")
    return output_path


def run_comparison_and_generate_html(num_items: int = 25):
    """Run comparison and generate HTML."""

    # Load wardrobe
    wm = WardrobeManager(user_id='peichin')
    all_items = wm.wardrobe_data.get('items', [])
    print(f"📦 Total wardrobe items: {len(all_items)}")

    # Filter to items with S3 images
    items_with_images = [
        item for item in all_items
        if item.get('system_metadata', {}).get('image_path', '').startswith('http')
    ][:num_items]
    print(f"🖼️  Using {len(items_with_images)} items with images")

    user_profile = {
        'three_words': {'current': 'casual', 'aspirational': 'polished', 'feeling': 'chic'}
    }
    occasion = 'casual coffee with friends followed by some errands'
    weather = 'mild'
    temp_range = '60-70F'

    results = {}

    for variant_name, prompt_version in [
        ("TEXT-ONLY (Control)", "baseline_v1"),
        ("VISION (Treatment)", "vision_v1")
    ]:
        print(f"\n🧪 Running {variant_name}...")

        engine = StyleGenerationEngine(
            api_key=os.getenv('OPENAI_API_KEY'),
            model='gpt-4o',
            temperature=0.7,
            max_tokens=2000,
            prompt_version=prompt_version
        )

        result = engine.generate_outfit_combinations(
            user_profile=user_profile,
            available_items=items_with_images,
            styling_challenges=[],
            occasion=occasion,
            weather_condition=weather,
            temperature_range=temp_range,
            user_id='peichin'
        )

        # Extract outfits
        if isinstance(result, dict):
            outfits = result.get('outfits', [])
        else:
            outfits = result

        # Convert to dicts if needed
        parsed_outfits = []
        for outfit in outfits:
            if hasattr(outfit, '__dict__'):
                o = outfit.__dict__
            else:
                o = outfit

            # Extract item names
            items = o.get('items', [])
            if items and isinstance(items[0], dict):
                item_names = [item.get('styling_details', {}).get('name', 'Unknown') for item in items]
            else:
                item_names = items

            parsed_outfits.append({
                'items': item_names,
                'styling_notes': o.get('styling_notes', ''),
                'why_it_works': o.get('why_it_works', ''),
                'constitution_principles': o.get('constitution_principles', {})
            })

        results[variant_name] = parsed_outfits
        print(f"  ✅ Generated {len(parsed_outfits)} outfits")

    # Generate HTML
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = Path(__file__).parent.parent / f'results/vision_comparison_{timestamp}.html'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_html(results, items_with_images, str(output_path))

    return str(output_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--items', type=int, default=25, help='Number of items to use')
    args = parser.parse_args()

    output = run_comparison_and_generate_html(args.items)
    print(f"\n🌐 Open in browser: file://{output}")
