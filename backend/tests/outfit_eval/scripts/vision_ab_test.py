#!/usr/bin/env python3
"""Vision A/B Test: Run multiple scenarios and generate HTML comparison.

Fair test: Both variants get the same metadata. Vision also gets images.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

os.environ['STORAGE_TYPE'] = 's3'

from dotenv import load_dotenv
load_dotenv()

from services.style_engine import StyleGenerationEngine
from services.wardrobe_manager import WardrobeManager


# Test scenarios
SCENARIOS = [
    {
        "id": "casual_coffee",
        "name": "Casual Coffee with Friends",
        "occasion": "casual coffee with friends followed by some errands",
        "weather": "mild",
        "temperature": "60-70°F",
        "style_profile": {
            "three_words": {"current": "casual", "aspirational": "polished", "feeling": "chic"}
        }
    },
    {
        "id": "work_meeting",
        "name": "Work Meeting + Drinks",
        "occasion": "important client presentation followed by drinks with girlfriends",
        "weather": "cool",
        "temperature": "55-65°F",
        "style_profile": {
            "three_words": {"current": "casual", "aspirational": "polished", "feeling": "confident"}
        }
    },
    {
        "id": "date_night",
        "name": "Date Night Dinner",
        "occasion": "dinner date at upscale restaurant",
        "weather": "evening, indoor",
        "temperature": "68-72°F",
        "style_profile": {
            "three_words": {"current": "classic", "aspirational": "relaxed", "feeling": "playful"}
        }
    }
]


def get_image_url(item_name: str, wardrobe_items: List[Dict]) -> str:
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


def run_generation(engine: StyleGenerationEngine, scenario: Dict, items: List[Dict], user_id: str) -> Dict:
    """Run outfit generation and capture metrics."""
    import time
    start = time.time()

    result = engine.generate_outfit_combinations(
        user_profile=scenario["style_profile"],
        available_items=items,
        styling_challenges=[],
        occasion=scenario["occasion"],
        weather_condition=scenario["weather"],
        temperature_range=scenario["temperature"],
        user_id=user_id
    )

    elapsed = time.time() - start

    # Extract outfits
    if isinstance(result, dict):
        outfits = result.get('outfits', [])
    else:
        outfits = result

    # Get metrics from the engine's last AI response
    usage = {}
    cost = 0
    latency = elapsed
    image_count = 0

    if hasattr(engine, '_last_ai_response') and engine._last_ai_response:
        ai_resp = engine._last_ai_response
        usage = ai_resp.usage if hasattr(ai_resp, 'usage') else {}
        latency = ai_resp.latency_seconds if hasattr(ai_resp, 'latency_seconds') else elapsed
        cost = engine.ai_provider.calculate_cost(usage) if usage else 0
        image_count = usage.get('image_count', 0)

    # Parse outfits
    parsed = []
    for outfit in outfits:
        if hasattr(outfit, '__dict__'):
            o = outfit.__dict__
        else:
            o = outfit

        items_list = o.get('items', [])
        if items_list and isinstance(items_list[0], dict):
            item_names = [item.get('styling_details', {}).get('name', 'Unknown') for item in items_list]
        else:
            item_names = items_list

        parsed.append({
            'items': item_names,
            'styling_notes': o.get('styling_notes', ''),
            'why_it_works': o.get('why_it_works', ''),
            'constitution_principles': o.get('constitution_principles', {})
        })

    return {
        'outfits': parsed,
        'latency': latency,
        'cost': cost,
        'tokens': usage.get('total_tokens', 0) if usage else 0,
        'image_count': image_count
    }


def generate_html(all_results: Dict, wardrobe_items: List[Dict], output_path: str):
    """Generate comprehensive HTML comparison."""

    html = """<!DOCTYPE html>
<html>
<head>
    <title>Vision A/B Test - Fair Comparison</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5; padding: 20px; line-height: 1.5;
        }
        .header {
            text-align: center; padding: 30px; background: white;
            border-radius: 12px; margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        h1 { color: #1a1a2e; margin-bottom: 10px; }
        .subtitle { color: #666; font-size: 14px; }

        .summary-stats {
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;
        }
        .stat-value { font-size: 24px; font-weight: bold; color: #2196F3; }
        .stat-label { font-size: 11px; color: #666; text-transform: uppercase; }

        .scenario {
            background: white; border-radius: 12px; margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;
        }
        .scenario-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 20px;
        }
        .scenario-title { font-size: 18px; font-weight: 600; }
        .scenario-details { font-size: 13px; opacity: 0.9; margin-top: 5px; }

        .metrics-row {
            display: grid; grid-template-columns: 1fr 1fr;
            border-bottom: 1px solid #eee;
        }
        .metrics {
            padding: 15px 20px; display: flex; gap: 30px; align-items: center;
        }
        .metrics.control { background: #f8f9ff; border-right: 1px solid #eee; }
        .metrics.treatment { background: #f8fff8; }
        .metric { text-align: center; }
        .metric-value { font-size: 18px; font-weight: bold; }
        .metric-label { font-size: 10px; color: #666; text-transform: uppercase; }
        .variant-badge {
            padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600;
        }
        .control .variant-badge { background: #e3f2fd; color: #1565c0; }
        .treatment .variant-badge { background: #e8f5e9; color: #2e7d32; }

        .outfits-grid {
            display: grid; grid-template-columns: 1fr 1fr;
        }
        .outfit-column { padding: 20px; }
        .outfit-column.control { border-right: 1px solid #eee; }

        .outfit-card {
            border: 1px solid #e0e0e0; border-radius: 10px;
            margin-bottom: 20px; overflow: hidden;
        }
        .outfit-header {
            background: #fafafa; padding: 10px 15px;
            font-weight: 600; font-size: 13px; color: #333;
            border-bottom: 1px solid #e0e0e0;
        }
        .outfit-body { padding: 15px; }

        .item-images {
            display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px;
        }
        .item-img {
            width: 70px; height: 70px; object-fit: cover; border-radius: 8px;
            border: 1px solid #ddd; transition: transform 0.2s;
        }
        .item-img:hover { transform: scale(2.5); z-index: 100; position: relative; }

        .item-names {
            display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 12px;
        }
        .item-name {
            background: #f0f0f0; padding: 3px 8px; border-radius: 4px;
            font-size: 11px; color: #333;
        }

        .section { margin-top: 12px; }
        .section-label {
            font-size: 10px; color: #999; text-transform: uppercase;
            margin-bottom: 4px; font-weight: 600;
        }
        .section-content {
            font-size: 12px; color: #444; line-height: 1.6;
            background: #fafafa; padding: 10px; border-radius: 6px;
        }
        .physical-sensibility {
            background: #fff3e0; border-left: 3px solid #ff9800;
        }
        .physical-sensibility strong { color: #e65100; }
        .no-physical {
            font-style: italic; color: #999; font-size: 11px;
            padding: 10px; background: #fafafa; border-radius: 6px;
        }

        .legend {
            display: flex; justify-content: center; gap: 30px;
            padding: 15px; background: #fafafa; margin-top: 10px;
            border-radius: 8px; font-size: 12px;
        }
        .legend-item { display: flex; align-items: center; gap: 8px; }
        .legend-color {
            width: 12px; height: 12px; border-radius: 3px;
        }
        .legend-color.control { background: #e3f2fd; }
        .legend-color.treatment { background: #e8f5e9; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 GPT-5.1: CoT Text vs CoT + Vision</h1>
        <p class="subtitle">Both variants receive identical metadata. Vision also receives wardrobe images.</p>
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color control"></div>
                <span><strong>Control:</strong> Text metadata only</span>
            </div>
            <div class="legend-item">
                <div class="legend-color treatment"></div>
                <span><strong>Treatment:</strong> Text metadata + Images</span>
            </div>
        </div>
    </div>
"""

    # Calculate totals
    total_control_cost = sum(r['control']['cost'] for r in all_results.values())
    total_treatment_cost = sum(r['treatment']['cost'] for r in all_results.values())
    total_control_latency = sum(r['control']['latency'] for r in all_results.values())
    total_treatment_latency = sum(r['treatment']['latency'] for r in all_results.values())

    html += f"""
    <div class="summary-stats">
        <div class="stat-card">
            <div class="stat-value">{len(all_results)}</div>
            <div class="stat-label">Scenarios</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{len(all_results) * 3 * 2}</div>
            <div class="stat-label">Total Outfits</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${total_control_cost + total_treatment_cost:.3f}</div>
            <div class="stat-label">Total Cost</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{total_control_latency + total_treatment_latency:.1f}s</div>
            <div class="stat-label">Total Time</div>
        </div>
    </div>
"""

    # Generate scenario sections
    for scenario_id, results in all_results.items():
        scenario = results['scenario']
        control = results['control']
        treatment = results['treatment']

        style = scenario['style_profile']['three_words']

        html += f"""
    <div class="scenario">
        <div class="scenario-header">
            <div class="scenario-title">📍 {scenario['name']}</div>
            <div class="scenario-details">
                {scenario['occasion']} | {scenario['weather']}, {scenario['temperature']} |
                Style: {style['current']} → {style['aspirational']}, feeling {style['feeling']}
            </div>
        </div>

        <div class="metrics-row">
            <div class="metrics control">
                <span class="variant-badge">📝 CoT TEXT-ONLY</span>
                <div class="metric">
                    <div class="metric-value">{control['latency']:.1f}s</div>
                    <div class="metric-label">Latency</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${control['cost']:.4f}</div>
                    <div class="metric-label">Cost</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{control['tokens']}</div>
                    <div class="metric-label">Tokens</div>
                </div>
            </div>
            <div class="metrics treatment">
                <span class="variant-badge">🖼️ CoT + VISION</span>
                <div class="metric">
                    <div class="metric-value">{treatment['latency']:.1f}s</div>
                    <div class="metric-label">Latency</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${treatment['cost']:.4f}</div>
                    <div class="metric-label">Cost</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{treatment['tokens']}</div>
                    <div class="metric-label">Tokens</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{treatment['image_count']}</div>
                    <div class="metric-label">Images</div>
                </div>
            </div>
        </div>

        <div class="outfits-grid">
            <div class="outfit-column control">
"""

        # Control outfits
        for i, outfit in enumerate(control['outfits'][:3]):
            html += _render_outfit_card(f"Outfit {i+1}", outfit, wardrobe_items, is_vision=False)

        html += """
            </div>
            <div class="outfit-column treatment">
"""

        # Treatment outfits
        for i, outfit in enumerate(treatment['outfits'][:3]):
            html += _render_outfit_card(f"Outfit {i+1}", outfit, wardrobe_items, is_vision=True)

        html += """
            </div>
        </div>
    </div>
"""

    html += """
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ HTML saved to: {output_path}")
    return output_path


def _render_outfit_card(title: str, outfit: Dict, wardrobe_items: List[Dict], is_vision: bool) -> str:
    """Render a single outfit card."""
    items = outfit.get('items', [])

    html = f"""
                <div class="outfit-card">
                    <div class="outfit-header">{title}</div>
                    <div class="outfit-body">
                        <div class="item-images">
"""
    for item_name in items:
        img_url = get_image_url(item_name, wardrobe_items)
        if img_url:
            html += f'                            <img class="item-img" src="{img_url}" alt="{item_name}" title="{item_name}">\n'

    html += """                        </div>
                        <div class="item-names">
"""
    for item_name in items:
        html += f'                            <span class="item-name">{item_name}</span>\n'

    html += f"""                        </div>

                        <div class="section">
                            <div class="section-label">Styling Notes</div>
                            <div class="section-content">{outfit.get('styling_notes', 'N/A')}</div>
                        </div>

                        <div class="section">
                            <div class="section-label">Why It Works</div>
                            <div class="section-content">{outfit.get('why_it_works', 'N/A')}</div>
                        </div>

                        <div class="section">
                            <div class="section-label">Physical Sensibility</div>
"""

    principles = outfit.get('constitution_principles', {})
    phys = principles.get('physical_sensibility', '')

    if phys:
        html += f'                            <div class="section-content physical-sensibility"><strong>✓</strong> {phys}</div>\n'
    elif is_vision:
        html += '                            <div class="no-physical">Not provided in response</div>\n'
    else:
        html += '                            <div class="no-physical">Not included in text-only prompt</div>\n'

    html += """                        </div>
                    </div>
                </div>
"""
    return html


def main(num_items: int = 25, user_id: str = 'peichin'):
    """Run the full A/B test."""
    print("=" * 60)
    print(f"🧪 Vision A/B Test - Fair Comparison (user: {user_id})")
    print("=" * 60)

    # Load wardrobe
    wm = WardrobeManager(user_id=user_id)
    all_items = wm.wardrobe_data.get('items', [])
    print(f"📦 Total wardrobe items: {len(all_items)}")

    # Filter to items with S3 images
    items_with_images = [
        item for item in all_items
        if item.get('system_metadata', {}).get('image_path', '').startswith('http')
    ][:num_items]
    print(f"🖼️  Using {len(items_with_images)} items with images\n")

    all_results = {}

    for scenario in SCENARIOS:
        print(f"\n{'─' * 60}")
        print(f"📍 Scenario: {scenario['name']}")
        print(f"{'─' * 60}")

        scenario_results = {'scenario': scenario}

        # Run control (CoT text-only - uses ===JSON OUTPUT=== format)
        print("\n  📝 Running CoT TEXT-ONLY (Control)...")
        engine_control = StyleGenerationEngine(
            api_key=os.getenv('OPENAI_API_KEY'),
            model='gpt-5.1',
            temperature=0.7,
            max_tokens=4000,
            prompt_version='chain_of_thought_v1'
        )
        scenario_results['control'] = run_generation(
            engine_control, scenario, items_with_images, user_id
        )
        print(f"     ✅ {len(scenario_results['control']['outfits'])} outfits | "
              f"{scenario_results['control']['latency']:.1f}s | "
              f"${scenario_results['control']['cost']:.4f}")

        # Run treatment (CoT + vision)
        print("\n  🖼️  Running CoT + VISION (Treatment)...")
        engine_vision = StyleGenerationEngine(
            api_key=os.getenv('OPENAI_API_KEY'),
            model='gpt-5.1',
            temperature=0.7,
            max_tokens=4000,
            prompt_version='vision_cot_v1'
        )
        scenario_results['treatment'] = run_generation(
            engine_vision, scenario, items_with_images, user_id
        )
        print(f"     ✅ {len(scenario_results['treatment']['outfits'])} outfits | "
              f"{scenario_results['treatment']['latency']:.1f}s | "
              f"${scenario_results['treatment']['cost']:.4f} | "
              f"{scenario_results['treatment']['image_count']} images")

        all_results[scenario['id']] = scenario_results

    # Generate HTML
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = Path(__file__).parent.parent / f'results/vision_ab_test_{user_id}_{timestamp}.html'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_html(all_results, items_with_images, str(output_path))

    print(f"\n{'=' * 60}")
    print(f"✅ A/B Test Complete!")
    print(f"🌐 Open: file://{output_path}")
    print(f"{'=' * 60}")

    return str(output_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--items', type=int, default=25, help='Number of items to use')
    parser.add_argument('--user', type=str, default='peichin', help='User ID to test')
    args = parser.parse_args()

    main(args.items, args.user)
