#!/usr/bin/env python3
"""Universal HTML generator for outfit evaluation results"""
import json
import re
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

# Set storage to S3
os.environ['STORAGE_TYPE'] = 's3'

from services.wardrobe_manager import WardrobeManager

def parse_outfit_string(outfit_str):
    """Parse OutfitCombination string representation"""
    items_match = re.search(r"items=\[(.*?)\], styling_notes=", outfit_str, re.DOTALL)
    if not items_match:
        return None

    items_str = items_match.group(1)
    item_names = re.findall(r"'name': '([^']+)'", items_str)

    notes_match = re.search(r"styling_notes='([^']*)'", outfit_str)
    styling_notes = notes_match.group(1) if notes_match else ""

    why_match = re.search(r"why_it_works='([^']*)'", outfit_str)
    why_it_works = why_match.group(1) if why_match else ""

    return {
        'items': item_names,
        'styling_notes': styling_notes,
        'why_it_works': why_it_works
    }

def get_image_url(item_name, wardrobe_items):
    """Find image URL for an item by name"""
    for item in wardrobe_items:
        name = item.get('styling_details', {}).get('name', '')
        if name == item_name:
            image_path = item.get('system_metadata', {}).get('image_path', '')
            if image_path:
                if image_path.startswith('http'):
                    return image_path
                filename = image_path.split('/')[-1] if '/' in image_path else image_path
                return f"https://style-inspo.s3.us-east-2.amazonaws.com/peichin/items/{filename}"
    return None

def detect_eval_type(results):
    """Detect if this is A/B test (multiple models/prompts per scenario) or single model"""
    scenario_models = {}
    for r in results:
        scenario_id = r['scenario_id']
        model_id = r['model_id']
        if scenario_id not in scenario_models:
            scenario_models[scenario_id] = set()
        scenario_models[scenario_id].add(model_id)

    # If any scenario has multiple models, it's an A/B test
    is_ab_test = any(len(models) > 1 for models in scenario_models.values())
    return 'ab_test' if is_ab_test else 'single_model'

def group_results(results, eval_type):
    """Group results by scenario and model"""
    if eval_type == 'ab_test':
        scenarios = {}
        for r in results:
            scenario_name = r['scenario_name']
            model_name = r['model_name']

            if scenario_name not in scenarios:
                scenarios[scenario_name] = {}

            parsed_outfits = []
            for outfit_str in r['outfits']:
                parsed = parse_outfit_string(outfit_str)
                if parsed:
                    parsed_outfits.append(parsed)

            scenarios[scenario_name][model_name] = {
                'outfits': parsed_outfits,
                'model_id': r['model_id'],
                'latency': r.get('latency_seconds', 0),
                'cost': r.get('cost_usd', 0),
                'reasoning': r.get('reasoning')
            }
        return scenarios
    else:
        # Single model: group by scenario only
        scenarios = {}
        for r in results:
            scenario_name = r['scenario_name']

            parsed_outfits = []
            for outfit_str in r['outfits']:
                parsed = parse_outfit_string(outfit_str)
                if parsed:
                    parsed_outfits.append(parsed)

            scenarios[scenario_name] = {
                'model_name': r['model_name'],
                'outfits': parsed_outfits,
                'latency': r.get('latency_seconds', 0),
                'cost': r.get('cost_usd', 0),
                'reasoning': r.get('reasoning')
            }
        return scenarios

def generate_ab_test_html(scenarios, wardrobe_items, eval_name):
    """Generate side-by-side A/B test HTML"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Eval Review: {eval_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #f5f5f5; padding: 20px; max-width: 1800px; margin: 0 auto; }}
        .scenario {{ background: white; padding: 30px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #1a1a1a; }}
        h2 {{ color: #333; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; }}
        .comparison {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }}
        .column {{ border: 2px solid #ddd; padding: 20px; border-radius: 8px; }}
        .model-header {{ background: #f8f9fa; padding: 15px; margin: -20px -20px 20px -20px; border-radius: 6px 6px 0 0; }}
        .model-header h3 {{ margin: 0 0 5px 0; }}
        .model-stats {{ font-size: 12px; color: #666; }}
        .outfit {{ margin: 20px 0; padding: 20px; background: #fafafa; border-radius: 6px; border-left: 4px solid #007bff; }}
        .outfit-header {{ margin-bottom: 15px; }}
        .items {{ display: flex; flex-wrap: wrap; gap: 15px; margin: 15px 0; }}
        .item-container {{ position: relative; }}
        img {{
            width: 200px;
            height: 200px;
            object-fit: cover;
            border-radius: 8px;
            border: 2px solid #ddd;
            transition: transform 0.2s, z-index 0s;
            cursor: pointer;
        }}
        img:hover {{
            transform: scale(2.2);
            z-index: 1000;
            box-shadow: 0 12px 24px rgba(0,0,0,0.4);
            border-color: #007bff;
        }}
        .item-placeholder {{
            width: 200px;
            height: 200px;
            background: #e9ecef;
            border-radius: 8px;
            font-size: 12px;
            padding: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            border: 2px solid #ddd;
            color: #666;
        }}
        .notes {{ font-size: 14px; margin: 10px 0; line-height: 1.6; }}
        .notes strong {{ color: #495057; }}
        .rating-section {{
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }}
        .rating-stars {{
            display: flex;
            gap: 5px;
            margin: 8px 0;
        }}
        .star {{
            font-size: 28px;
            cursor: pointer;
            color: #ddd;
            transition: color 0.2s;
            user-select: none;
        }}
        .star:hover, .star.active {{
            color: #ffc107;
        }}
        .notes-input {{
            width: 100%;
            min-height: 70px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: inherit;
            font-size: 14px;
            margin-top: 5px;
            resize: vertical;
        }}
        .notes-input:focus {{
            outline: none;
            border-color: #007bff;
        }}
        .rating-label {{
            font-weight: 600;
            font-size: 13px;
            color: #495057;
            margin-bottom: 5px;
        }}
        .reasoning {{
            background: #e8f4f8;
            padding: 20px;
            margin: 20px 0;
            border-radius: 6px;
            border-left: 4px solid #0d6efd;
            white-space: pre-wrap;
            font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.6;
            max-height: 600px;
            overflow-y: auto;
        }}
        .reasoning-title {{
            font-weight: bold;
            color: #0d6efd;
            margin-bottom: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            font-size: 14px;
        }}
    </style>
    <script>
        function setRating(outfitId, rating) {{
            const stars = document.querySelectorAll('#outfit-' + outfitId + ' .star');
            stars.forEach((star, index) => {{
                if (index < rating) {{
                    star.classList.add('active');
                }} else {{
                    star.classList.remove('active');
                }}
            }});
            localStorage.setItem('rating-' + outfitId, rating);
        }}

        function saveNotes(outfitId) {{
            const notes = document.getElementById('notes-' + outfitId).value;
            localStorage.setItem('notes-' + outfitId, notes);
        }}

        function loadSavedData() {{
            document.querySelectorAll('.outfit').forEach(outfit => {{
                const outfitId = outfit.id.replace('outfit-', '');
                const savedRating = localStorage.getItem('rating-' + outfitId);
                const savedNotes = localStorage.getItem('notes-' + outfitId);

                if (savedRating) {{
                    setRating(outfitId, parseInt(savedRating));
                }}
                if (savedNotes) {{
                    const notesInput = document.getElementById('notes-' + outfitId);
                    if (notesInput) {{
                        notesInput.value = savedNotes;
                    }}
                }}
            }});
        }}

        window.addEventListener('load', loadSavedData);
    </script>
</head>
<body>
    <h1>📊 Outfit Evaluation Review</h1>
    <p><strong>Evaluation:</strong> {eval_name}</p>
"""

    for scenario_name, models_data in scenarios.items():
        html += f"""
    <div class="scenario">
        <h2>📝 {scenario_name}</h2>
        <div class="comparison">
"""
        for model_name, data in models_data.items():
            html += f"""
            <div class="column">
                <div class="model-header">
                    <h3>{model_name}</h3>
                    <div class="model-stats">
                        Latency: {data['latency']:.1f}s | Cost: ${data['cost']:.4f}
                    </div>
                </div>
"""
            # Add reasoning section if available
            if data.get('reasoning'):
                html += f"""
                <div class="reasoning">
                    <div class="reasoning-title">🧠 Chain-of-Thought Reasoning</div>
                    {data['reasoning']}
                </div>
"""
            html += """
"""
            for i, outfit in enumerate(data['outfits'], 1):
                outfit_id = f"{scenario_name.replace(' ', '_')}_{data['model_id']}_{i}".replace('(', '').replace(')', '').replace(',', '').replace(':', '')

                html += f"""
                <div class="outfit" id="outfit-{outfit_id}">
                    <div class="outfit-header">
                        <strong>Outfit {i}</strong>
                    </div>
                    <div class="items">
"""
                for item_name in outfit['items']:
                    url = get_image_url(item_name, wardrobe_items)
                    if url:
                        html += f'<div class="item-container"><img src="{url}" title="{item_name}" alt="{item_name}"></div>'
                    else:
                        html += f'<div class="item-placeholder">{item_name}</div>'

                html += f"""
                    </div>
                    <div class="notes"><strong>Styling:</strong> {outfit['styling_notes']}</div>
                    <div class="notes"><strong>Why it works:</strong> {outfit['why_it_works']}</div>
                    <div class="rating-section">
                        <div class="rating-label">Your Rating:</div>
                        <div class="rating-stars">
                            <span class="star" onclick="setRating('{outfit_id}', 1)">★</span>
                            <span class="star" onclick="setRating('{outfit_id}', 2)">★</span>
                            <span class="star" onclick="setRating('{outfit_id}', 3)">★</span>
                            <span class="star" onclick="setRating('{outfit_id}', 4)">★</span>
                            <span class="star" onclick="setRating('{outfit_id}', 5)">★</span>
                        </div>
                        <div class="rating-label">Notes:</div>
                        <textarea class="notes-input" id="notes-{outfit_id}" placeholder="Add your feedback here..." onblur="saveNotes('{outfit_id}')"></textarea>
                    </div>
                </div>
"""
            html += """
            </div>
"""
        html += """
        </div>
    </div>
"""

    html += """
</body>
</html>
"""
    return html

def generate_single_model_html(scenarios, wardrobe_items, eval_name):
    """Generate single-column HTML for single model eval"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Eval Review: {eval_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #f5f5f5; padding: 20px; max-width: 1200px; margin: 0 auto; }}
        .scenario {{ background: white; padding: 30px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #1a1a1a; }}
        h2 {{ color: #333; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; }}
        .model-info {{ background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
        .outfit {{ margin: 20px 0; padding: 20px; background: #fafafa; border-radius: 6px; border-left: 4px solid #007bff; }}
        .outfit-header {{ margin-bottom: 15px; }}
        .items {{ display: flex; flex-wrap: wrap; gap: 15px; margin: 15px 0; }}
        img {{
            width: 200px;
            height: 200px;
            object-fit: cover;
            border-radius: 8px;
            border: 2px solid #ddd;
            transition: transform 0.2s;
            cursor: pointer;
        }}
        img:hover {{
            transform: scale(2.2);
            z-index: 1000;
            box-shadow: 0 12px 24px rgba(0,0,0,0.4);
            border-color: #007bff;
        }}
        .item-placeholder {{
            width: 200px;
            height: 200px;
            background: #e9ecef;
            border-radius: 8px;
            font-size: 12px;
            padding: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            border: 2px solid #ddd;
        }}
        .notes {{ font-size: 14px; margin: 10px 0; line-height: 1.6; }}
        .rating-section {{
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }}
        .rating-stars {{
            display: flex;
            gap: 5px;
            margin: 8px 0;
        }}
        .star {{
            font-size: 28px;
            cursor: pointer;
            color: #ddd;
            transition: color 0.2s;
        }}
        .star:hover, .star.active {{
            color: #ffc107;
        }}
        .notes-input {{
            width: 100%;
            min-height: 70px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: inherit;
            font-size: 14px;
            margin-top: 5px;
        }}
        .rating-label {{
            font-weight: 600;
            font-size: 13px;
            color: #495057;
        }}
        .reasoning {{
            background: #e8f4f8;
            padding: 20px;
            margin: 20px 0;
            border-radius: 6px;
            border-left: 4px solid #0d6efd;
            white-space: pre-wrap;
            font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.6;
            max-height: 600px;
            overflow-y: auto;
        }}
        .reasoning-title {{
            font-weight: bold;
            color: #0d6efd;
            margin-bottom: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            font-size: 14px;
        }}
    </style>
    <script>
        function setRating(outfitId, rating) {{
            const stars = document.querySelectorAll('#outfit-' + outfitId + ' .star');
            stars.forEach((star, index) => {{
                if (index < rating) {{
                    star.classList.add('active');
                }} else {{
                    star.classList.remove('active');
                }}
            }});
            localStorage.setItem('rating-' + outfitId, rating);
        }}

        function saveNotes(outfitId) {{
            const notes = document.getElementById('notes-' + outfitId).value;
            localStorage.setItem('notes-' + outfitId, notes);
        }}

        function loadSavedData() {{
            document.querySelectorAll('.outfit').forEach(outfit => {{
                const outfitId = outfit.id.replace('outfit-', '');
                const savedRating = localStorage.getItem('rating-' + outfitId);
                const savedNotes = localStorage.getItem('notes-' + outfitId);

                if (savedRating) {{
                    setRating(outfitId, parseInt(savedRating));
                }}
                if (savedNotes) {{
                    const notesInput = document.getElementById('notes-' + outfitId);
                    if (notesInput) {{
                        notesInput.value = savedNotes;
                    }}
                }}
            }});
        }}

        window.addEventListener('load', loadSavedData);
    </script>
</head>
<body>
    <h1>📊 Outfit Evaluation Review</h1>
    <p><strong>Evaluation:</strong> {eval_name}</p>
"""

    for scenario_name, data in scenarios.items():
        html += f"""
    <div class="scenario">
        <h2>📝 {scenario_name}</h2>
        <div class="model-info">
            <strong>Model:</strong> {data['model_name']} |
            <strong>Latency:</strong> {data['latency']:.1f}s |
            <strong>Cost:</strong> ${data['cost']:.4f}
        </div>
"""
        # Add reasoning section if available
        if data.get('reasoning'):
            html += f"""
        <div class="reasoning">
            <div class="reasoning-title">🧠 Chain-of-Thought Reasoning</div>
            {data['reasoning']}
        </div>
"""
        html += """
"""
        for i, outfit in enumerate(data['outfits'], 1):
            outfit_id = f"{scenario_name.replace(' ', '_')}_{i}".replace('(', '').replace(')', '').replace(':', '')

            html += f"""
        <div class="outfit" id="outfit-{outfit_id}">
            <div class="outfit-header">
                <strong>Outfit {i}</strong>
            </div>
            <div class="items">
"""
            for item_name in outfit['items']:
                url = get_image_url(item_name, wardrobe_items)
                if url:
                    html += f'<img src="{url}" title="{item_name}" alt="{item_name}">'
                else:
                    html += f'<div class="item-placeholder">{item_name}</div>'

            html += f"""
            </div>
            <div class="notes"><strong>Styling:</strong> {outfit['styling_notes']}</div>
            <div class="notes"><strong>Why it works:</strong> {outfit['why_it_works']}</div>
            <div class="rating-section">
                <div class="rating-label">Your Rating:</div>
                <div class="rating-stars">
                    <span class="star" onclick="setRating('{outfit_id}', 1)">★</span>
                    <span class="star" onclick="setRating('{outfit_id}', 2)">★</span>
                    <span class="star" onclick="setRating('{outfit_id}', 3)">★</span>
                    <span class="star" onclick="setRating('{outfit_id}', 4)">★</span>
                    <span class="star" onclick="setRating('{outfit_id}', 5)">★</span>
                </div>
                <div class="rating-label">Notes:</div>
                <textarea class="notes-input" id="notes-{outfit_id}" placeholder="Add your feedback here..." onblur="saveNotes('{outfit_id}')"></textarea>
            </div>
        </div>
"""
        html += """
    </div>
"""

    html += """
</body>
</html>
"""
    return html

def main():
    results_dir = Path(__file__).parent.parent / "results"

    # Get eval directory from argument or find latest
    if len(sys.argv) > 1:
        eval_name = sys.argv[1]
        eval_dir = results_dir / eval_name
        if not eval_dir.exists():
            print(f"❌ Error: {eval_name} not found!")
            return
    else:
        eval_dirs = sorted([d for d in results_dir.iterdir() if d.is_dir() and d.name.startswith('eval_')],
                          key=lambda x: x.name, reverse=True)
        if not eval_dirs:
            print("❌ No eval directories found!")
            return
        eval_dir = eval_dirs[0]

    eval_name = eval_dir.name
    print(f"📂 Using eval: {eval_name}")

    # Load results
    raw_results_path = eval_dir / "raw_results.json"
    if not raw_results_path.exists():
        print(f"❌ No raw_results.json found in {eval_name}")
        return

    with open(raw_results_path) as f:
        results = json.load(f)

    # Detect eval type
    eval_type = detect_eval_type(results)
    print(f"📊 Detected eval type: {eval_type}")

    # Count scenarios and models
    scenarios_count = len(set(r['scenario_name'] for r in results))
    models_count = len(set(r['model_name'] for r in results))
    print(f"📝 Scenarios: {scenarios_count} | Models: {models_count}")

    # Load wardrobe
    print("🔄 Loading wardrobe from S3...")
    try:
        wm = WardrobeManager(user_id='peichin')
        wardrobe_data = wm.load_wardrobe_data()
        wardrobe_items = wardrobe_data.get('items', [])
        print(f"✅ Loaded {len(wardrobe_items)} wardrobe items")
    except Exception as e:
        print(f"⚠️  Warning: Could not load wardrobe ({e}), continuing with empty wardrobe")
        wardrobe_items = []

    # Group results
    grouped = group_results(results, eval_type)

    # Generate HTML
    if eval_type == 'ab_test':
        html = generate_ab_test_html(grouped, wardrobe_items, eval_name)
    else:
        html = generate_single_model_html(grouped, wardrobe_items, eval_name)

    # Save HTML
    output_filename = f"EVAL_REVIEW_{eval_name}.html"
    output_path = eval_dir / output_filename
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ HTML saved to: {output_path}")
    print(f"🌐 Open: file://{output_path.absolute()}")

if __name__ == '__main__':
    main()
