"""Generate HTML review for A/B test results comparing baseline vs chain-of-thought prompts"""
import json
import os
import sys
from pathlib import Path
from collections import defaultdict

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

# Set storage to S3
os.environ['STORAGE_TYPE'] = 's3'

from services.wardrobe_manager import WardrobeManager

def get_image_url(item_name, wardrobe_items):
    """Find image URL for an item by name"""
    for item in wardrobe_items:
        name = item.get('styling_details', {}).get('name', '')
        if name == item_name:
            image_path = item.get('system_metadata', {}).get('image_path', '')
            if image_path:
                # Extract just the filename if it's a full path
                if '/' in image_path:
                    filename = image_path.split('/')[-1]
                else:
                    filename = image_path
                return f"https://style-inspo.s3.us-east-2.amazonaws.com/peichin/items/{filename}"
    return None

def main():
    # Find the most recent eval directory
    results_dir = Path(__file__).parent.parent / "results"
    eval_dirs = sorted([d for d in results_dir.iterdir() if d.is_dir() and d.name.startswith('eval_')],
                      key=lambda x: x.name, reverse=True)

    if not eval_dirs:
        print("No eval directories found!")
        return

    latest_eval = eval_dirs[0]
    print(f"Using results from: {latest_eval.name}")

    # Load results
    raw_results_path = latest_eval / "raw_results.json"
    with open(raw_results_path) as f:
        results = json.load(f)

    # Load wardrobe from S3
    print("Loading wardrobe from S3...")
    wm = WardrobeManager(user_id='peichin')
    wardrobe_data = wm.load_wardrobe_data()
    wardrobe_items = wardrobe_data.get('items', [])
    print(f"Loaded {len(wardrobe_items)} items")

    # Group results by scenario and prompt_version
    grouped = defaultdict(lambda: {'baseline_v1': [], 'chain_of_thought_v1': []})
    for result in results:
        scenario_name = result['scenario_name']
        prompt_version = result.get('prompt_version', 'baseline_v1')
        for outfit in result['outfits']:
            grouped[scenario_name][prompt_version].append({
                'items': outfit['items'],
                'styling_notes': outfit.get('styling_notes', ''),
                'why_it_works': outfit.get('why_it_works', ''),
                'reasoning': outfit.get('reasoning', None)
            })

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A/B Test: Baseline vs Chain-of-Thought</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f8f9fa;
            padding: 20px;
            margin: 0;
        }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{ font-size: 32px; margin: 0 0 10px 0; }}
        .metadata {{ color: #666; font-size: 14px; }}
        .scenario-section {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .scenario-title {{
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e9ecef;
        }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 20px;
        }}
        .prompt-column {{
            border: 2px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            background: #f8f9fa;
        }}
        .prompt-label {{
            font-weight: 600;
            font-size: 16px;
            margin-bottom: 15px;
            padding: 10px;
            background: white;
            border-radius: 6px;
            text-align: center;
        }}
        .baseline-label {{ border-left: 4px solid #0d6efd; }}
        .cot-label {{ border-left: 4px solid #198754; }}
        .outfit-card {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid #dee2e6;
        }}
        .outfit-number {{
            font-weight: 600;
            color: #495057;
            margin-bottom: 10px;
            font-size: 14px;
        }}
        .items-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 10px 0;
        }}
        .item-image {{
            width: 70px;
            height: 70px;
            object-fit: cover;
            border-radius: 6px;
            border: 1px solid #dee2e6;
            transition: transform 0.2s;
        }}
        .item-image:hover {{
            transform: scale(1.5);
            z-index: 100;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}
        .item-placeholder {{
            width: 70px;
            height: 70px;
            background: #e9ecef;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 9px;
            text-align: center;
            padding: 4px;
            color: #6c757d;
        }}
        .detail-section {{
            font-size: 13px;
            margin: 10px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 3px solid #6c757d;
        }}
        .detail-label {{
            font-weight: 600;
            color: #495057;
            margin-bottom: 5px;
        }}
        .reasoning-box {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 6px;
            padding: 10px;
            margin: 10px 0;
            font-size: 12px;
            color: #856404;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
        }}
        @media (max-width: 1200px) {{
            .comparison-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 A/B Test: Baseline vs Chain-of-Thought Prompts</h1>
        <div class="metadata">
            <strong>User:</strong> peichin |
            <strong>Wardrobe Items:</strong> {len(wardrobe_items)} |
            <strong>Scenarios:</strong> {len(grouped)} |
            <strong>Test Run:</strong> {latest_eval.name}
        </div>
    </div>
"""

    # Generate sections for each scenario
    for scenario_name, prompts in grouped.items():
        baseline_outfits = prompts['baseline_v1']
        cot_outfits = prompts['chain_of_thought_v1']

        html += f"""
    <div class="scenario-section">
        <div class="scenario-title">📝 {scenario_name}</div>
        <div class="comparison-grid">
"""

        # Baseline column
        html += """
            <div class="prompt-column">
                <div class="prompt-label baseline-label">Baseline Prompt</div>
"""
        for i, outfit in enumerate(baseline_outfits, 1):
            html += f"""
                <div class="outfit-card">
                    <div class="outfit-number">Outfit {i}</div>
                    <div class="items-container">
"""
            for item_name in outfit['items']:
                image_url = get_image_url(item_name, wardrobe_items)
                if image_url:
                    html += f'<img src="{image_url}" alt="{item_name}" class="item-image" title="{item_name}">'
                else:
                    html += f'<div class="item-placeholder">{item_name}</div>'

            html += f"""
                    </div>
                    <div class="detail-section">
                        <div class="detail-label">Styling Notes:</div>
                        {outfit['styling_notes']}
                    </div>
                    <div class="detail-section">
                        <div class="detail-label">Why It Works:</div>
                        {outfit['why_it_works']}
                    </div>
                </div>
"""
        html += """
            </div>
"""

        # Chain-of-Thought column
        html += """
            <div class="prompt-column">
                <div class="prompt-label cot-label">Chain-of-Thought Prompt</div>
"""
        for i, outfit in enumerate(cot_outfits, 1):
            html += f"""
                <div class="outfit-card">
                    <div class="outfit-number">Outfit {i}</div>
                    <div class="items-container">
"""
            for item_name in outfit['items']:
                image_url = get_image_url(item_name, wardrobe_items)
                if image_url:
                    html += f'<img src="{image_url}" alt="{item_name}" class="item-image" title="{item_name}">'
                else:
                    html += f'<div class="item-placeholder">{item_name}</div>'

            html += f"""
                    </div>
"""
            if outfit.get('reasoning'):
                html += f"""
                    <div class="reasoning-box">
                        <div class="detail-label">🧠 Reasoning Process:</div>
                        {outfit['reasoning'][:500]}{'...' if len(outfit['reasoning']) > 500 else ''}
                    </div>
"""

            html += f"""
                    <div class="detail-section">
                        <div class="detail-label">Styling Notes:</div>
                        {outfit['styling_notes']}
                    </div>
                    <div class="detail-section">
                        <div class="detail-label">Why It Works:</div>
                        {outfit['why_it_works']}
                    </div>
                </div>
"""
        html += """
            </div>
        </div>
    </div>
"""

    html += """
</body>
</html>
"""

    # Save HTML
    output_path = latest_eval / "AB_TEST_REVIEW.html"
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ HTML saved to: {output_path}")
    print(f"📂 Open in browser: file://{output_path}")

if __name__ == '__main__':
    main()
