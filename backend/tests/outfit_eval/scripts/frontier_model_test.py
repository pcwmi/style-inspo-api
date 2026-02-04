#!/usr/bin/env python3
"""Frontier Model Test: Compare latest models on garment physics reasoning.

Tests: GPT-5.1, Claude Opus 4.5, and optionally reasoning models (o1, o3).
"""

import os
import sys
import random
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


# Multiple test scenarios
SCENARIOS = [
    {
        "id": "casual_brunch",
        "name": "Casual Brunch",
        "occasion": "casual brunch with friends, then shopping",
        "weather": "cool",
        "temperature": "55-65°F",
    },
    {
        "id": "work_meeting",
        "name": "Work Meeting",
        "occasion": "important work meeting, want to look professional but approachable",
        "weather": "mild",
        "temperature": "65-72°F",
    },
    {
        "id": "date_night",
        "name": "Date Night",
        "occasion": "dinner date at a nice restaurant, want to look elegant but not overdressed",
        "weather": "mild",
        "temperature": "60-70°F",
    },
]

# Default style profile (can be overridden per user)
DEFAULT_STYLE = {
    "three_words": {"current": "casual", "aspirational": "polished", "feeling": "chic"}
}

# Models to test - GPT-4o vs 5.2 comparison (text metadata + chain of thought)
MODELS = [
    {"id": "gpt-4o", "provider": "openai", "name": "GPT-4o (Text)", "prompt": "chain_of_thought_v1"},
    {"id": "gpt-5.2", "provider": "openai", "name": "GPT-5.2 (Text)", "prompt": "chain_of_thought_v1"},
]


def get_image_url(item_name: str, wardrobe_items: List[Dict]) -> str:
    """Find image URL for an item by name."""
    item_name_lower = item_name.lower().strip()
    for item in wardrobe_items:
        name = item.get('styling_details', {}).get('name', '')
        if name.lower().strip() == item_name_lower:
            return item.get('system_metadata', {}).get('image_path', '')
    for item in wardrobe_items:
        name = item.get('styling_details', {}).get('name', '')
        if item_name_lower in name.lower() or name.lower() in item_name_lower:
            return item.get('system_metadata', {}).get('image_path', '')
    return ''


def run_model_test(model_config: Dict, items: List[Dict], user_id: str) -> Dict:
    """Run outfit generation with a specific model."""
    import time

    model_id = model_config["id"]
    provider = model_config["provider"]
    prompt_version = model_config.get("prompt", "vision_cot_v1")
    # Reasoning models (o1, o3) only support temperature=1
    temp = 1.0 if model_id.startswith("o") else 0.7

    # Get API key based on provider
    if provider == "openai":
        api_key = os.getenv('OPENAI_API_KEY')
    else:
        api_key = os.getenv('ANTHROPIC_API_KEY')

    if not api_key:
        return {"error": f"No API key for {provider}", "outfits": [], "latency": 0, "cost": 0}

    try:
        engine = StyleGenerationEngine(
            api_key=api_key,
            model=model_id,
            temperature=temp,
            max_tokens=4000,
            prompt_version=prompt_version
        )

        start = time.time()

        # Randomize item order to avoid "silent middle problem" (matches production)
        shuffled_items = random.sample(items, len(items))

        result = engine.generate_outfit_combinations(
            user_profile=SCENARIO["style_profile"],
            available_items=shuffled_items,
            styling_challenges=[],
            occasion=SCENARIO["occasion"],
            weather_condition=SCENARIO["weather"],
            temperature_range=SCENARIO["temperature"],
            user_id=user_id
        )

        elapsed = time.time() - start

        # Extract outfits
        if isinstance(result, dict):
            outfits = result.get('outfits', [])
        else:
            outfits = result

        # Parse outfits
        parsed_outfits = []
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

            parsed_outfits.append({
                'items': item_names,
                'styling_notes': o.get('styling_notes', ''),
                'why_it_works': o.get('why_it_works', ''),
                'constitution_principles': o.get('constitution_principles', {})
            })

        # Get cost from last response
        cost = 0
        if hasattr(engine, '_last_ai_response') and engine._last_ai_response:
            usage = engine._last_ai_response.usage or {}
            cost = engine.ai_provider.calculate_cost(usage) if hasattr(engine, 'ai_provider') else 0

        return {
            "outfits": parsed_outfits,
            "latency": elapsed,
            "cost": cost,
            "model": model_id
        }

    except Exception as e:
        print(f"⚠️ Error with {model_id}: {e}")
        return {"error": str(e), "outfits": [], "latency": 0, "cost": 0, "model": model_id}


def generate_html(results: Dict, wardrobe_items: List[Dict], output_path: str):
    """Generate HTML comparison of frontier models."""

    html = """<!DOCTYPE html>
<html>
<head>
    <title>Frontier Model Comparison - Garment Physics</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px; background: #f5f5f5;
        }
        h1 { text-align: center; color: #333; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; }

        .model-section {
            background: white; border-radius: 12px; padding: 20px;
            margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .model-header {
            display: flex; justify-content: space-between; align-items: center;
            border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 20px;
        }
        .model-name { font-size: 20px; font-weight: bold; color: #333; }
        .model-metrics { display: flex; gap: 20px; }
        .metric { text-align: center; }
        .metric-value { font-size: 18px; font-weight: bold; color: #2196F3; }
        .metric-label { font-size: 12px; color: #666; }

        .outfit-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
        .outfit-card {
            border: 1px solid #eee; border-radius: 8px; padding: 15px;
            background: #fafafa;
        }
        .outfit-header { font-weight: bold; margin-bottom: 10px; color: #333; }

        .item-images { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
        .item-img {
            width: 60px; height: 60px; object-fit: cover; border-radius: 6px;
            border: 1px solid #ddd;
        }
        .item-img:hover { transform: scale(2); z-index: 100; position: relative; }

        .item-names { margin: 10px 0; }
        .item-name {
            display: inline-block; background: #e8e8e8; padding: 2px 8px;
            border-radius: 4px; margin: 2px; font-size: 12px;
        }

        .section-label { font-size: 11px; color: #999; text-transform: uppercase; margin-top: 10px; }
        .section-content { font-size: 13px; color: #555; line-height: 1.4; margin: 5px 0; }

        .error { background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; }
    </style>
</head>
<body>
    <h1>🏆 Frontier Model Comparison</h1>
    <p class="subtitle">Testing garment physics reasoning with vision + chain-of-thought</p>
"""

    for model_id, result in results.items():
        model_name = result.get("name", model_id)

        html += f"""
    <div class="model-section">
        <div class="model-header">
            <div class="model-name">{model_name}</div>
            <div class="model-metrics">
                <div class="metric">
                    <div class="metric-value">{result.get('latency', 0):.1f}s</div>
                    <div class="metric-label">Latency</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${result.get('cost', 0):.4f}</div>
                    <div class="metric-label">Cost</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{len(result.get('outfits', []))}</div>
                    <div class="metric-label">Outfits</div>
                </div>
            </div>
        </div>
"""

        if result.get("error"):
            html += f'<div class="error">Error: {result["error"]}</div>'
        else:
            html += '<div class="outfit-grid">'
            for i, outfit in enumerate(result.get('outfits', [])[:3]):
                items = outfit.get('items', [])

                html += f"""
            <div class="outfit-card">
                <div class="outfit-header">Outfit {i+1}</div>
                <div class="item-images">
"""
                for item_name in items:
                    img_url = get_image_url(item_name, wardrobe_items)
                    if img_url:
                        html += f'                    <img class="item-img" src="{img_url}" alt="{item_name}" title="{item_name}">\n'

                html += '                </div>\n                <div class="item-names">\n'
                for item_name in items:
                    html += f'                    <span class="item-name">{item_name}</span>\n'

                html += f"""                </div>
                <div class="section-label">Styling Notes</div>
                <div class="section-content">{outfit.get('styling_notes', 'N/A')}</div>
                <div class="section-label">Why It Works</div>
                <div class="section-content">{outfit.get('why_it_works', 'N/A')}</div>
            </div>
"""
            html += '        </div>'

        html += '\n    </div>\n'

    html += """
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ HTML saved to: {output_path}")


def run_scenario_test(user_id: str, scenario: Dict, model_config: Dict, items: List[Dict]) -> Dict:
    """Run a single scenario with a specific model."""
    import time

    model_id = model_config["id"]
    provider = model_config["provider"]
    prompt_version = model_config.get("prompt", "vision_cot_v1")
    temp = 1.0 if model_id.startswith("o") else 0.7

    if provider == "openai":
        api_key = os.getenv('OPENAI_API_KEY')
    else:
        api_key = os.getenv('ANTHROPIC_API_KEY')

    if not api_key:
        return {"error": f"No API key for {provider}", "outfits": [], "latency": 0, "cost": 0}

    try:
        engine = StyleGenerationEngine(
            api_key=api_key,
            model=model_id,
            temperature=temp,
            max_tokens=4000,
            prompt_version=prompt_version
        )

        start = time.time()

        # Randomize item order to avoid "silent middle problem" (matches production)
        shuffled_items = random.sample(items, len(items))

        # Debug: show first 3 items to verify randomization
        first_3 = [item.get('styling_details', {}).get('name', 'Unknown')[:25] for item in shuffled_items[:3]]
        print(f"\n         🎲 Shuffled (first 3): {first_3}")

        result = engine.generate_outfit_combinations(
            user_profile={"three_words": DEFAULT_STYLE["three_words"]},
            available_items=shuffled_items,
            styling_challenges=[],
            occasion=scenario["occasion"],
            weather_condition=scenario["weather"],
            temperature_range=scenario["temperature"],
            user_id=user_id
        )

        elapsed = time.time() - start

        if isinstance(result, dict):
            outfits = result.get('outfits', [])
        else:
            outfits = result

        parsed_outfits = []
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

            parsed_outfits.append({
                'items': item_names,
                'styling_notes': o.get('styling_notes', ''),
                'why_it_works': o.get('why_it_works', ''),
            })

        return {
            "outfits": parsed_outfits,
            "latency": elapsed,
            "cost": 0,
            "scenario": scenario["name"],
            "user": user_id,
        }

    except Exception as e:
        return {"error": str(e), "outfits": [], "latency": 0, "cost": 0}


def main_multi_user(users: List[str] = None, num_items: int = 22):
    """Run multi-user, multi-scenario comparison across GPT models."""
    if users is None:
        users = ['dana', 'peichin', 'kate', 'alexi']

    print("=" * 70)
    print(f"🏆 GPT Model Comparison: 4o vs 5.2 (Text + Chain of Thought)")
    print(f"   {len(users)} users × {len(SCENARIOS)} scenarios × {len(MODELS)} models")
    print("=" * 70)

    all_results = []
    summary_data = []

    for user_id in users:
        print(f"\n{'='*50}")
        print(f"👤 User: {user_id}")
        print(f"{'='*50}")

        # Load wardrobe
        try:
            wm = WardrobeManager(user_id=user_id)
            all_items = wm.wardrobe_data.get('items', [])
        except Exception as e:
            print(f"   ⚠️ Could not load wardrobe: {e}")
            continue

        items_with_images = [
            item for item in all_items
            if item.get('system_metadata', {}).get('image_path', '').startswith('http')
        ][:num_items]
        print(f"   📦 {len(items_with_images)} items with images")

        if len(items_with_images) < 5:
            print(f"   ⚠️ Skipping - not enough items")
            continue

        for scenario in SCENARIOS:
            print(f"\n   📋 Scenario: {scenario['name']}")

            for model_config in MODELS:
                model_name = model_config["name"]
                print(f"      🧪 {model_name}...", end=" ", flush=True)

                result = run_scenario_test(user_id, scenario, model_config, items_with_images)
                result["model"] = model_name
                result["user"] = user_id
                result["scenario"] = scenario["name"]

                if result.get("error"):
                    print(f"❌ {result['error'][:30]}...")
                else:
                    print(f"✅ {len(result['outfits'])} outfits | {result['latency']:.1f}s")
                    all_results.append(result)

                    summary_data.append({
                        "user": user_id,
                        "scenario": scenario["name"],
                        "model": model_name,
                        "latency": result["latency"],
                        "outfits": len(result["outfits"]),
                    })

    # Generate combined HTML
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = Path(__file__).parent.parent / f'results/multi_user_ab_test_{timestamp}.html'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_multi_user_html(all_results, summary_data, str(output_path))

    print(f"\n{'=' * 70}")
    print(f"✅ Multi-User A/B Test Complete!")
    print(f"🌐 Open: file://{output_path}")
    print(f"{'=' * 70}")

    return str(output_path)


def generate_multi_user_html(results: List[Dict], summary_data: List[Dict], output_path: str):
    """Generate HTML for multi-user comparison with rating capability."""

    # Group results by user and scenario
    grouped = {}
    for r in results:
        key = f"{r['user']}_{r['scenario']}"
        if key not in grouped:
            grouped[key] = {"user": r["user"], "scenario": r["scenario"], "models": {}}
        grouped[key]["models"][r["model"]] = r

    # Model display order and colors
    MODEL_ORDER = ["GPT-4o (Text)", "GPT-5.2 (Text)"]
    MODEL_COLORS = {
        "GPT-4o (Text)": "#fff3e0",
        "GPT-5.2 (Text)": "#e3f2fd",
    }

    html = """<!DOCTYPE html>
<html>
<head>
    <title>GPT Model Comparison - 5.1 vs 5.2</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        h1 { text-align: center; }
        .summary { background: white; padding: 20px; border-radius: 12px; margin-bottom: 30px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f8f8; }

        .comparison { background: white; border-radius: 12px; padding: 20px; margin: 20px 0; }
        .comparison-header { font-size: 18px; font-weight: bold; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #eee; }
        .side-by-side { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
        .variant { border: 1px solid #ddd; border-radius: 8px; padding: 12px; }
        .variant-header { font-weight: bold; margin-bottom: 10px; padding: 8px; border-radius: 4px; font-size: 14px; }

        .outfit { margin: 12px 0; padding: 10px; background: #fafafa; border-radius: 6px; position: relative; }
        .outfit-title { font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center; }
        .item-images { display: flex; flex-wrap: wrap; gap: 5px; margin: 8px 0; }
        .item-img { width: 45px; height: 45px; object-fit: cover; border-radius: 4px; border: 1px solid #ddd; cursor: pointer; }
        .item-img:hover { transform: scale(2.5); z-index: 100; position: relative; }
        .items-list { font-size: 10px; color: #666; line-height: 1.3; }
        .styling { font-size: 11px; color: #555; margin-top: 5px; }
        .latency { font-size: 11px; color: #888; }

        /* Rating UI */
        .rating-btns { display: flex; gap: 4px; }
        .rating-btn {
            width: 24px; height: 24px; border: none; border-radius: 4px; cursor: pointer;
            font-size: 12px; opacity: 0.5; transition: all 0.2s;
        }
        .rating-btn:hover { opacity: 1; transform: scale(1.1); }
        .rating-btn.selected { opacity: 1; box-shadow: 0 0 0 2px #333; }
        .rating-btn.good { background: #c8e6c9; }
        .rating-btn.ok { background: #fff9c4; }
        .rating-btn.bad { background: #ffcdd2; }

        /* Saved ratings display */
        .ratings-summary {
            background: #f0f0f0; padding: 15px; border-radius: 8px; margin-top: 20px;
            display: none;
        }
        .ratings-summary.has-ratings { display: block; }
        .export-btn {
            background: #2196F3; color: white; border: none; padding: 10px 20px;
            border-radius: 6px; cursor: pointer; margin-top: 10px;
        }
    </style>
</head>
<body>
    <h1>🔬 GPT Model Comparison: 4o vs 5.2</h1>
    <p style="text-align: center; color: #666;">Comparing latency and outfit quality (text metadata + chain of thought)</p>

    <div class="summary">
        <h3>📊 Latency Summary</h3>
        <table>
            <tr>
                <th>User</th>
                <th>Scenario</th>
                <th>GPT-4o</th>
                <th>GPT-5.2</th>
                <th>5.2 vs 4o Δ</th>
            </tr>
"""

    # Build summary rows
    for key, group in sorted(grouped.items()):
        m4o = group["models"].get("GPT-4o (Text)", {})
        m52 = group["models"].get("GPT-5.2 (Text)", {})

        lat_4o = m4o.get("latency", 0)
        lat_52 = m52.get("latency", 0)
        delta = lat_52 - lat_4o if lat_4o > 0 else 0
        delta_pct = (delta / lat_4o * 100) if lat_4o > 0 else 0

        html += f"""            <tr>
                <td><strong>{group['user']}</strong></td>
                <td>{group['scenario']}</td>
                <td>{lat_4o:.1f}s</td>
                <td>{lat_52:.1f}s</td>
                <td style="color: {'green' if delta < 0 else 'red'}">{delta:+.1f}s ({delta_pct:+.0f}%)</td>
            </tr>
"""

    html += """        </table>
    </div>

    <div class="ratings-summary" id="ratingsSummary">
        <h3>📝 Your Ratings</h3>
        <div id="ratingsContent"></div>
        <button class="export-btn" onclick="exportRatings()">Export Ratings as JSON</button>
    </div>
"""

    # Load all wardrobes for image lookup
    wardrobes = {}
    for r in results:
        if r["user"] not in wardrobes:
            try:
                wm = WardrobeManager(user_id=r["user"])
                wardrobes[r["user"]] = wm.wardrobe_data.get('items', [])
            except:
                wardrobes[r["user"]] = []

    # Side-by-side comparisons (3 columns)
    for key, group in sorted(grouped.items()):
        user = group["user"]
        scenario = group["scenario"]
        wardrobe_items = wardrobes.get(user, [])

        html += f"""
    <div class="comparison">
        <div class="comparison-header">👤 {user.upper()} — {scenario}</div>
        <div class="side-by-side">
"""
        for model_name in MODEL_ORDER:
            model_result = group["models"].get(model_name, {})
            bg_color = MODEL_COLORS.get(model_name, "#f5f5f5")
            latency = model_result.get("latency", 0)

            html += f"""            <div class="variant">
                <div class="variant-header" style="background: {bg_color};">
                    {model_name} <span class="latency">({latency:.1f}s)</span>
                </div>
"""
            outfits = model_result.get("outfits", [])[:3]
            for i, outfit in enumerate(outfits):
                items = outfit.get("items", [])
                outfit_id = f"{user}_{scenario}_{model_name}_{i}".replace(" ", "_").replace("(", "").replace(")", "")

                html += f"""                <div class="outfit" id="{outfit_id}">
                    <div class="outfit-title">
                        <span>Outfit {i+1}</span>
                        <div class="rating-btns">
                            <button class="rating-btn good" onclick="rate('{outfit_id}', 'good')" title="Good">✓</button>
                            <button class="rating-btn ok" onclick="rate('{outfit_id}', 'ok')" title="OK">~</button>
                            <button class="rating-btn bad" onclick="rate('{outfit_id}', 'bad')" title="Bad">✗</button>
                        </div>
                    </div>
                    <div class="item-images">
"""
                for item_name in items:
                    img_url = get_image_url(item_name, wardrobe_items)
                    if img_url:
                        html += f'                        <img class="item-img" src="{img_url}" title="{item_name}">\n'

                html += f"""                    </div>
                    <div class="items-list">{' • '.join(items)}</div>
"""
                if outfit.get("styling_notes"):
                    notes = outfit["styling_notes"][:120] + ("..." if len(outfit.get("styling_notes", "")) > 120 else "")
                    html += f'                    <div class="styling">{notes}</div>\n'

                html += """                </div>
"""

            if not outfits:
                html += '                <div class="outfit"><em>No outfits generated</em></div>\n'

            html += """            </div>
"""

        html += """        </div>
    </div>
"""

    # Add rating JavaScript
    html += """
    <script>
        const ratings = {};

        function rate(outfitId, rating) {
            // Update data
            ratings[outfitId] = rating;

            // Update UI
            const outfit = document.getElementById(outfitId);
            outfit.querySelectorAll('.rating-btn').forEach(btn => btn.classList.remove('selected'));
            outfit.querySelector(`.rating-btn.${rating}`).classList.add('selected');

            // Update summary
            updateRatingsSummary();

            // Save to localStorage
            localStorage.setItem('outfitRatings', JSON.stringify(ratings));
        }

        function updateRatingsSummary() {
            const summary = document.getElementById('ratingsSummary');
            const content = document.getElementById('ratingsContent');

            const counts = {good: 0, ok: 0, bad: 0};
            const byModel = {};

            Object.entries(ratings).forEach(([id, rating]) => {
                counts[rating]++;
                // Extract model from ID
                const parts = id.split('_');
                const model = parts.slice(2, -1).join(' ');
                if (!byModel[model]) byModel[model] = {good: 0, ok: 0, bad: 0};
                byModel[model][rating]++;
            });

            if (Object.keys(ratings).length > 0) {
                summary.classList.add('has-ratings');
                let html = `<p><strong>Total:</strong> ✓ ${counts.good} good | ~ ${counts.ok} ok | ✗ ${counts.bad} bad</p>`;
                html += '<p><strong>By Model:</strong></p><ul>';
                Object.entries(byModel).forEach(([model, c]) => {
                    html += `<li>${model}: ✓${c.good} ~${c.ok} ✗${c.bad}</li>`;
                });
                html += '</ul>';
                content.innerHTML = html;
            } else {
                summary.classList.remove('has-ratings');
            }
        }

        function exportRatings() {
            const blob = new Blob([JSON.stringify(ratings, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'outfit_ratings.json';
            a.click();
        }

        // Load saved ratings on page load
        window.onload = function() {
            const saved = localStorage.getItem('outfitRatings');
            if (saved) {
                Object.assign(ratings, JSON.parse(saved));
                Object.entries(ratings).forEach(([id, rating]) => {
                    const outfit = document.getElementById(id);
                    if (outfit) {
                        outfit.querySelector(`.rating-btn.${rating}`)?.classList.add('selected');
                    }
                });
                updateRatingsSummary();
            }
        };
    </script>
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ HTML saved to: {output_path}")


def main(user_id: str = 'dana', num_items: int = 22):
    """Run single-user frontier model comparison (legacy)."""
    print("=" * 60)
    print(f"🏆 Frontier Model Comparison (user: {user_id})")
    print("=" * 60)

    wm = WardrobeManager(user_id=user_id)
    all_items = wm.wardrobe_data.get('items', [])
    print(f"📦 Total wardrobe items: {len(all_items)}")

    items_with_images = [
        item for item in all_items
        if item.get('system_metadata', {}).get('image_path', '').startswith('http')
    ][:num_items]
    print(f"🖼️  Using {len(items_with_images)} items with images\n")

    results = {}

    for i, model_config in enumerate(MODELS):
        print(f"\n🧪 Testing {model_config['name']}...")
        result = run_model_test(model_config, items_with_images, user_id)
        result["name"] = model_config["name"]
        result_key = model_config["name"].replace(" ", "_").replace("(", "").replace(")", "")
        results[result_key] = result

        if result.get("error"):
            print(f"   ❌ Error: {result['error']}")
        else:
            print(f"   ✅ {len(result['outfits'])} outfits | {result['latency']:.1f}s | ${result['cost']:.4f}")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = Path(__file__).parent.parent / f'results/frontier_test_{user_id}_{timestamp}.html'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_html(results, items_with_images, str(output_path))

    print(f"\n{'=' * 60}")
    print(f"✅ Frontier Test Complete!")
    print(f"🌐 Open: file://{output_path}")
    print(f"{'=' * 60}")

    return str(output_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', type=str, default=None, help='Single user ID (legacy mode)')
    parser.add_argument('--users', type=str, default='dana,peichin,kate,alexi', help='Comma-separated user IDs')
    parser.add_argument('--items', type=int, default=22, help='Number of items to use')
    parser.add_argument('--multi', action='store_true', help='Run multi-user test')
    args = parser.parse_args()

    if args.user and not args.multi:
        main(args.user, args.items)
    else:
        users = args.users.split(',')
        main_multi_user(users, args.items)
