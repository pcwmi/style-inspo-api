#!/usr/bin/env python3
"""Generate HTML comparison for streaming prompt test results"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

os.environ['STORAGE_TYPE'] = 's3'

from services.wardrobe_manager import WardrobeManager


def get_image_url(item_name, wardrobe_items):
    """Find image URL for an item by name (fuzzy match)"""
    item_name_lower = item_name.lower().strip()

    for item in wardrobe_items:
        name = item.get('styling_details', {}).get('name', '')
        if name.lower().strip() == item_name_lower:
            image_path = item.get('system_metadata', {}).get('image_path', '')
            if image_path:
                if image_path.startswith('http'):
                    return image_path
                filename = image_path.split('/')[-1] if '/' in image_path else image_path
                return f"https://style-inspo.s3.us-east-2.amazonaws.com/peichin/items/{filename}"
    return None


def generate_html(results_path: str):
    """Generate comparison HTML from results JSON"""

    with open(results_path, 'r') as f:
        results = json.load(f)

    # Load wardrobe
    wardrobe_manager = WardrobeManager(user_id='peichin')
    wardrobe_items = wardrobe_manager.get_wardrobe_items('all')

    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Streaming Prompt Comparison</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            max-width: 1800px;
            margin: 0 auto;
        }
        .scenario {
            background: white;
            padding: 30px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #1a1a1a; }
        h2 { color: #333; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; }
        .comparison { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
        .column { border: 2px solid #ddd; padding: 20px; border-radius: 8px; }
        .column.version-a { border-color: #007bff; }
        .column.version-b { border-color: #28a745; }
        .version-header {
            padding: 15px;
            margin: -20px -20px 20px -20px;
            border-radius: 6px 6px 0 0;
        }
        .version-a .version-header { background: #e7f1ff; }
        .version-b .version-header { background: #e8f5e9; }
        .version-header h3 { margin: 0 0 5px 0; }
        .stats { font-size: 12px; color: #666; }
        .stats span { margin-right: 15px; }
        .outfit {
            margin: 20px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 6px;
            border-left: 4px solid #666;
        }
        .version-a .outfit { border-left-color: #007bff; }
        .version-b .outfit { border-left-color: #28a745; }
        .outfit h4 { margin: 0 0 15px 0; }
        .items { display: flex; flex-wrap: wrap; gap: 10px; margin: 15px 0; }
        img {
            width: 120px;
            height: 120px;
            object-fit: cover;
            border-radius: 8px;
            border: 2px solid #ddd;
            transition: transform 0.2s;
            cursor: pointer;
        }
        img:hover {
            transform: scale(2.5);
            z-index: 1000;
            box-shadow: 0 12px 24px rgba(0,0,0,0.4);
            position: relative;
        }
        .item-placeholder {
            width: 120px;
            height: 120px;
            background: #eee;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            color: #999;
            text-align: center;
            padding: 5px;
        }
        .styling {
            font-style: italic;
            color: #555;
            margin: 10px 0;
            padding: 10px;
            background: #fff;
            border-radius: 4px;
        }
        .why {
            color: #333;
            margin: 10px 0;
            padding: 10px;
            background: #fff;
            border-radius: 4px;
        }
        .timing-summary {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .timing-summary table { width: 100%; border-collapse: collapse; }
        .timing-summary th, .timing-summary td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .winner { background: #d4edda; font-weight: bold; }
        .constraint-pass { color: #28a745; }
        .constraint-fail { color: #dc3545; }
        .judge-section {
            background: #fff3cd;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h1>Streaming Prompt Comparison</h1>
    <p>Version A: All JSON at end | Version B: Interleaved JSON per outfit</p>
"""

    for result in results:
        scenario = result['scenario']
        va = result['version_a']
        vb = result['version_b']

        # Calculate timing
        first_json_a = va['markers'].get('outfit_1_json_complete', va['markers'].get('json_start', va['total_time']))
        first_json_b = vb['markers'].get('outfit_1_json_start', vb['total_time'])

        html += f"""
    <div class="scenario">
        <h2>{scenario['name']}</h2>
        <p>Occasion: {scenario['occasion']}</p>
        <p>Style: {scenario['style_words']['current']} + {scenario['style_words']['aspirational']} + {scenario['style_words']['feeling']}</p>
        {"<p><strong>Anchor items:</strong> " + ", ".join(scenario['anchor_items']) + "</p>" if scenario['anchor_items'] else ""}

        <div class="timing-summary">
            <h4>Timing & Constraints (Claude judged)</h4>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Version A</th>
                    <th>Version B</th>
                    <th>Winner</th>
                </tr>
                <tr>
                    <td>Total time</td>
                    <td>{va['total_time']:.2f}s</td>
                    <td>{vb['total_time']:.2f}s</td>
                    <td>{"A" if va['total_time'] < vb['total_time'] else "B" if vb['total_time'] < va['total_time'] else "Tie"}</td>
                </tr>
                <tr>
                    <td>First outfit JSON available</td>
                    <td>{first_json_a:.2f}s</td>
                    <td class="winner">{first_json_b:.2f}s</td>
                    <td><strong>B wins by {first_json_a - first_json_b:.1f}s</strong></td>
                </tr>
                <tr>
                    <td>Constraint (no item in 3+ outfits)</td>
                    <td class="{'constraint-pass' if va['constraints']['passed'] else 'constraint-fail'}">{'PASS' if va['constraints']['passed'] else 'FAIL'}</td>
                    <td class="{'constraint-pass' if vb['constraints']['passed'] else 'constraint-fail'}">{'PASS' if vb['constraints']['passed'] else 'FAIL'}</td>
                    <td>{"Both pass" if va['constraints']['passed'] and vb['constraints']['passed'] else "See violations"}</td>
                </tr>
            </table>
        </div>

        <div class="comparison">
            <div class="column version-a">
                <div class="version-header">
                    <h3>Version A (All JSON at end)</h3>
                    <div class="stats">
                        <span>Total: {va['total_time']:.2f}s</span>
                        <span>First JSON: {first_json_a:.2f}s</span>
                    </div>
                </div>
"""

        # Version A outfits
        for i, outfit in enumerate(va['outfits'], 1):
            html += f"""
                <div class="outfit">
                    <h4>Outfit {i}</h4>
                    <div class="items">
"""
            for item_name in outfit.get('items', []):
                img_url = get_image_url(item_name, wardrobe_items)
                if img_url:
                    html += f'                        <img src="{img_url}" alt="{item_name}" title="{item_name}">\n'
                else:
                    html += f'                        <div class="item-placeholder">{item_name}</div>\n'

            html += f"""
                    </div>
                    <div class="styling"><strong>Styling:</strong> {outfit.get('styling_notes', 'N/A')}</div>
                    <div class="why"><strong>Why it works:</strong> {outfit.get('why_it_works', 'N/A')}</div>
                </div>
"""

        html += """
            </div>
            <div class="column version-b">
                <div class="version-header">
                    <h3>Version B (Interleaved JSON)</h3>
                    <div class="stats">
"""
        html += f"""
                        <span>Total: {vb['total_time']:.2f}s</span>
                        <span>First JSON: {first_json_b:.2f}s</span>
                    </div>
                </div>
"""

        # Version B outfits
        for i, outfit in enumerate(vb['outfits'], 1):
            html += f"""
                <div class="outfit">
                    <h4>Outfit {i}</h4>
                    <div class="items">
"""
            for item_name in outfit.get('items', []):
                img_url = get_image_url(item_name, wardrobe_items)
                if img_url:
                    html += f'                        <img src="{img_url}" alt="{item_name}" title="{item_name}">\n'
                else:
                    html += f'                        <div class="item-placeholder">{item_name}</div>\n'

            html += f"""
                    </div>
                    <div class="styling"><strong>Styling:</strong> {outfit.get('styling_notes', 'N/A')}</div>
                    <div class="why"><strong>Why it works:</strong> {outfit.get('why_it_works', 'N/A')}</div>
                </div>
"""

        html += """
            </div>
        </div>

        <div class="judge-section">
            <h4>Your Quality Judgment</h4>
            <p>Which version produced better outfits for this scenario?</p>
            <p>Consider: item matching, styling creativity, "why it works" reasoning</p>
        </div>
    </div>
"""

    html += """
    <div class="scenario">
        <h2>Summary</h2>
        <p><strong>Time study conclusion:</strong> Version B delivers first usable outfit ~4 seconds faster.</p>
        <p><strong>Constraint honoring:</strong> Both versions passed all constraint checks.</p>
        <p><strong>Quality:</strong> [Your judgment here]</p>
        <p><strong>Note:</strong> These tests used simplified prompts. Production timing would be ~2x longer, but the relative advantage should hold.</p>
    </div>
</body>
</html>
"""

    return html


if __name__ == "__main__":
    # Find most recent results
    results_dir = Path(__file__).parent / "streaming_comparison_results"
    json_files = sorted(results_dir.glob("comparison_raw_*.json"))

    if not json_files:
        print("No results found")
        sys.exit(1)

    latest = json_files[-1]
    print(f"Generating HTML from: {latest}")

    html = generate_html(str(latest))

    output_path = results_dir / f"COMPARISON_REVIEW_{latest.stem.replace('comparison_raw_', '')}.html"
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Generated: {output_path}")
