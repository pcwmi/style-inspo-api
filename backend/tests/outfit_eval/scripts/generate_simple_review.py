"""Simple HTML review generator for A/B test results"""
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
    # Extract item names from items list
    items_match = re.search(r"items=\[(.*?)\], styling_notes=", outfit_str, re.DOTALL)
    if not items_match:
        return None

    items_str = items_match.group(1)
    # Extract all name fields
    item_names = re.findall(r"'name': '([^']+)'", items_str)

    # Extract styling notes
    notes_match = re.search(r"styling_notes='([^']+)'", outfit_str)
    styling_notes = notes_match.group(1) if notes_match else ""

    # Extract why it works
    why_match = re.search(r"why_it_works='([^']+)'", outfit_str)
    why_it_works = why_match.group(1) if why_match else ""

    return {
        'items': item_names,
        'styling_notes': styling_notes,
        'why_it_works': why_it_works
    }

def extract_reasoning(result):
    """Extract chain-of-thought reasoning from raw AI response if available"""
    # Look for reasoning in the result metadata
    # The reasoning appears before ===JSON OUTPUT=== marker in the AI response
    # We need to check if there's a way to get the raw AI response
    # For now, return None - we'll add this if the data is available
    return None

def get_image_url(item_name, wardrobe_items):
    """Find image URL for an item by name"""
    for item in wardrobe_items:
        name = item.get('styling_details', {}).get('name', '')
        if name == item_name:
            image_path = item.get('system_metadata', {}).get('image_path', '')
            if image_path:
                if image_path.startswith('http'):
                    return image_path
                # Extract filename
                filename = image_path.split('/')[-1] if '/' in image_path else image_path
                return f"https://style-inspo.s3.us-east-2.amazonaws.com/peichin/items/{filename}"
    return None

def main():
    # Check for command-line argument to specify eval directory
    import sys
    results_dir = Path(__file__).parent.parent / "results"

    if len(sys.argv) > 1:
        # Use specified eval directory
        eval_name = sys.argv[1]
        latest_eval = results_dir / eval_name
        if not latest_eval.exists():
            print(f"Error: {eval_name} not found!")
            return
    else:
        # Find latest eval directory
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

    # Load wardrobe
    print("Loading wardrobe from S3...")
    wm = WardrobeManager(user_id='peichin')
    wardrobe_data = wm.load_wardrobe_data()
    wardrobe_items = wardrobe_data.get('items', [])
    print(f"Loaded {len(wardrobe_items)} items")

    # Try to load reasoning from log file
    reasoning_by_scenario = {}
    log_file = Path('/tmp/ab_test_success.log')
    if log_file.exists():
        print("Extracting chain-of-thought reasoning from log...")
        with open(log_file) as f:
            log_content = f.read()

        # Split by scenario headers (which appear BEFORE each baseline/CoT pair)
        scenario_sections = re.split(r'📝 Scenario: ([^\n]+)', log_content)

        # Process pairs: scenario_sections[0] is before first scenario
        # Then alternates: [1]=scenario_name, [2]=content, [3]=scenario_name, [4]=content, etc
        for i in range(1, len(scenario_sections), 2):
            if i + 1 < len(scenario_sections):
                scenario_name = scenario_sections[i].strip()
                section_content = scenario_sections[i + 1]

                # Extract chain-of-thought reasoning from this scenario's section
                # Look for reasoning between "RAW AI RESPONSE" and "===JSON OUTPUT===" in the CoT portion
                reasoning_match = re.search(
                    r'Model: GPT-4o \(Chain-of-Thought\).*?RAW AI RESPONSE:.*?={80,}\n(.*?)===JSON OUTPUT===',
                    section_content,
                    re.DOTALL
                )
                if reasoning_match:
                    reasoning = reasoning_match.group(1).strip()
                    reasoning_by_scenario[scenario_name] = reasoning

    # Group by scenario
    scenarios = {}
    for r in results:
        scenario_name = r['scenario_name']
        if scenario_name not in scenarios:
            scenarios[scenario_name] = {'baseline': [], 'cot': [], 'reasoning': reasoning_by_scenario.get(scenario_name, '')}

        # Parse outfits
        parsed_outfits = []
        for outfit_str in r['outfits']:
            parsed = parse_outfit_string(outfit_str)
            if parsed:
                parsed_outfits.append(parsed)

        if 'Baseline' in r['model_name']:
            scenarios[scenario_name]['baseline'] = parsed_outfits
        else:
            scenarios[scenario_name]['cot'] = parsed_outfits

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>A/B Test: Baseline vs Chain-of-Thought</title>
    <style>
        body {{ font-family: system-ui; background: #f5f5f5; padding: 20px; max-width: 1800px; margin: 0 auto; }}
        .scenario {{ background: white; padding: 30px; margin: 20px 0; border-radius: 8px; }}
        h2 {{ color: #333; }}
        .comparison {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }}
        .column {{ border: 2px solid #ddd; padding: 20px; border-radius: 8px; }}
        .baseline {{ border-color: #0d6efd; }}
        .cot {{ border-color: #198754; }}
        .outfit {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 6px; }}
        .items {{ display: flex; flex-wrap: wrap; gap: 15px; margin: 15px 0; }}
        img {{
            width: 150px;
            height: 150px;
            object-fit: cover;
            border-radius: 8px;
            border: 2px solid #ddd;
            transition: transform 0.2s;
            cursor: pointer;
        }}
        img:hover {{ transform: scale(1.8); z-index: 100; box-shadow: 0 8px 16px rgba(0,0,0,0.3); }}
        .notes {{ font-size: 14px; margin: 10px 0; line-height: 1.5; }}
        .reasoning {{
            background: #e7f5e7;
            padding: 15px;
            margin: 20px 0;
            border-radius: 6px;
            border-left: 4px solid #198754;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 13px;
            line-height: 1.6;
            max-height: 600px;
            overflow-y: auto;
        }}
        .reasoning-title {{
            font-weight: bold;
            color: #198754;
            margin-bottom: 10px;
            font-family: system-ui;
        }}
        .rating-section {{
            margin-top: 15px;
            padding: 10px;
            background: #fff3cd;
            border-radius: 4px;
            border-left: 3px solid #ffc107;
        }}
        .rating-stars {{
            display: flex;
            gap: 5px;
            margin: 8px 0;
        }}
        .star {{
            font-size: 24px;
            cursor: pointer;
            color: #ddd;
            transition: color 0.2s;
        }}
        .star:hover, .star.active {{
            color: #ffc107;
        }}
        .notes-input {{
            width: 100%;
            min-height: 60px;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: system-ui;
            font-size: 13px;
            margin-top: 5px;
        }}
        .rating-label {{
            font-weight: bold;
            font-size: 13px;
            color: #856404;
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
            // Store rating in localStorage
            localStorage.setItem('rating-' + outfitId, rating);
        }}

        function saveNotes(outfitId) {{
            const notes = document.getElementById('notes-' + outfitId).value;
            localStorage.setItem('notes-' + outfitId, notes);
        }}

        function loadSavedData() {{
            // Load all saved ratings and notes from localStorage
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
    <h1>🧪 A/B Test Results: Baseline vs Chain-of-Thought</h1>
    <p><strong>Test Run:</strong> {latest_eval.name} | <strong>Items:</strong> {len(wardrobe_items)}</p>
"""

    for scenario_name, outfits in scenarios.items():
        html += f"""
    <div class="scenario">
        <h2>📝 {scenario_name}</h2>
        <div class="comparison">
            <div class="column baseline">
                <h3>Baseline Prompt</h3>
"""
        for i, outfit in enumerate(outfits['baseline'], 1):
            outfit_id = f"{scenario_name.replace(' ', '_').replace('(', '').replace(')', '')}_baseline_{i}"
            html += f"""
                <div class="outfit" id="outfit-{outfit_id}">
                    <strong>Outfit {i}</strong>
                    <div class="items">
"""
            for item_name in outfit['items']:
                url = get_image_url(item_name, wardrobe_items)
                if url:
                    html += f'<img src="{url}" title="{item_name}">'
                else:
                    html += f'<div style="width:150px;height:150px;background:#ddd;border-radius:8px;font-size:12px;padding:10px;display:flex;align-items:center;justify-content:center;text-align:center">{item_name}</div>'

            html += f"""
                    </div>
                    <div class="notes"><strong>Styling:</strong> {outfit['styling_notes']}</div>
                    <div class="notes"><strong>Why:</strong> {outfit['why_it_works']}</div>
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
            <div class="column cot">
                <h3>Chain-of-Thought Prompt</h3>
"""
        # Add reasoning section if available
        if outfits.get('reasoning'):
            html += f"""
                <div class="reasoning">
                    <div class="reasoning-title">🧠 Chain-of-Thought Reasoning Process</div>
                    {outfits['reasoning']}
                </div>
"""

        for i, outfit in enumerate(outfits['cot'], 1):
            outfit_id = f"{scenario_name.replace(' ', '_').replace('(', '').replace(')', '')}_cot_{i}"
            html += f"""
                <div class="outfit" id="outfit-{outfit_id}">
                    <strong>Outfit {i}</strong>
                    <div class="items">
"""
            for item_name in outfit['items']:
                url = get_image_url(item_name, wardrobe_items)
                if url:
                    html += f'<img src="{url}" title="{item_name}">'
                else:
                    html += f'<div style="width:150px;height:150px;background:#ddd;border-radius:8px;font-size:12px;padding:10px;display:flex;align-items:center;justify-content:center;text-align:center">{item_name}</div>'

            html += f"""
                    </div>
                    <div class="notes"><strong>Styling:</strong> {outfit['styling_notes']}</div>
                    <div class="notes"><strong>Why:</strong> {outfit['why_it_works']}</div>
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
        </div>
    </div>
"""

    html += """
</body>
</html>
"""

    # Save with unique filename based on eval directory
    output_filename = f"AB_TEST_REVIEW_{latest_eval.name}.html"
    output_path = latest_eval / output_filename
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ HTML saved to: {output_path}")
    print(f"📂 Open: file://{output_path}")

if __name__ == '__main__':
    main()
