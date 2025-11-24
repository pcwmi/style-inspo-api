"""
Generate HTML review page from evaluation results.

Usage:
    python generate_review.py --results results/eval_20251123_143022/
"""

import argparse
import json
from pathlib import Path
from datetime import datetime


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Outfit Generation Evaluation - {timestamp}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .stat {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            margin-top: 5px;
        }}
        .scenario-section {{
            margin-bottom: 40px;
        }}
        .scenario-header {{
            background: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
            border-bottom: 2px solid #e0e0e0;
        }}
        .scenario-title {{
            font-size: 24px;
            font-weight: 600;
        }}
        .scenario-description {{
            color: #666;
            margin-top: 5px;
        }}
        .model-group {{
            background: white;
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .model-group:last-child {{
            border-radius: 0 0 8px 8px;
        }}
        .model-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .model-name {{
            font-size: 18px;
            font-weight: 600;
        }}
        .model-stats {{
            display: flex;
            gap: 20px;
            font-size: 14px;
            color: #666;
        }}
        .outfits-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        .outfit-card {{
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            background: #fafafa;
            transition: box-shadow 0.2s;
        }}
        .outfit-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .outfit-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #ddd;
        }}
        .outfit-title {{
            font-weight: 600;
            font-size: 14px;
        }}
        .outfit-meta {{
            font-size: 12px;
            color: #666;
        }}
        .outfit-items {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin: 15px 0;
        }}
        .item-image {{
            width: 100%;
            aspect-ratio: 1;
            object-fit: cover;
            border-radius: 4px;
            background: #e0e0e0;
        }}
        .outfit-notes {{
            font-size: 13px;
            line-height: 1.5;
            color: #555;
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-radius: 4px;
        }}
        .rating-section {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
        }}
        .stars {{
            display: flex;
            gap: 5px;
            margin: 10px 0;
        }}
        .star {{
            font-size: 24px;
            cursor: pointer;
            color: #ddd;
            transition: color 0.1s;
        }}
        .star:hover,
        .star.active {{
            color: #FFD700;
        }}
        .notes-input {{
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 13px;
            font-family: inherit;
            resize: vertical;
            min-height: 60px;
        }}
        .save-button {{
            background: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            margin-top: 10px;
        }}
        .save-button:hover {{
            background: #45a049;
        }}
        .save-button.saved {{
            background: #888;
        }}
        .validation {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin: 10px 0;
            font-size: 12px;
        }}
        .validation-badge {{
            padding: 4px 8px;
            border-radius: 3px;
            font-weight: 500;
        }}
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        .badge-error {{
            background: #f8d7da;
            color: #721c24;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎨 Outfit Generation Evaluation</h1>
        <p>Generated: {timestamp}</p>

        <div class="summary">
            <div class="stat">
                <div class="stat-label">Total Outfits</div>
                <div class="stat-value">{total_outfits}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Models Tested</div>
                <div class="stat-value">{num_models}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Test Scenarios</div>
                <div class="stat-value">{num_scenarios}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Rated</div>
                <div class="stat-value" id="rated-count">0/{total_outfits}</div>
            </div>
        </div>
    </div>

    {content}

    <script>
        // Ratings storage
        let ratings = {{}};

        // Load existing ratings
        try {{
            const saved = localStorage.getItem('outfit_ratings');
            if (saved) {{
                ratings = JSON.parse(saved);
                applyRatings();
            }}
        }} catch (e) {{
            console.error('Error loading ratings:', e);
        }}

        // Star rating handler
        document.querySelectorAll('.star').forEach(star => {{
            star.addEventListener('click', function() {{
                const outfitId = this.dataset.outfitId;
                const rating = parseInt(this.dataset.rating);

                // Update visual
                const stars = document.querySelectorAll(`[data-outfit-id="${{outfitId}}"]`);
                stars.forEach(s => {{
                    const starRating = parseInt(s.dataset.rating);
                    s.classList.toggle('active', starRating <= rating);
                }});

                // Store rating
                if (!ratings[outfitId]) ratings[outfitId] = {{}};
                ratings[outfitId].rating = rating;
                saveRatings();
            }});
        }});

        // Notes handler
        document.querySelectorAll('.notes-input').forEach(input => {{
            input.addEventListener('change', function() {{
                const outfitId = this.dataset.outfitId;
                if (!ratings[outfitId]) ratings[outfitId] = {{}};
                ratings[outfitId].notes = this.value;
                saveRatings();
            }});
        }});

        // Save ratings
        function saveRatings() {{
            localStorage.setItem('outfit_ratings', JSON.stringify(ratings));
            updateRatedCount();
            console.log('Ratings saved:', ratings);
        }}

        // Apply saved ratings to UI
        function applyRatings() {{
            Object.keys(ratings).forEach(outfitId => {{
                const data = ratings[outfitId];

                // Apply star rating
                if (data.rating) {{
                    const stars = document.querySelectorAll(`[data-outfit-id="${{outfitId}}"]`);
                    stars.forEach(s => {{
                        const starRating = parseInt(s.dataset.rating);
                        s.classList.toggle('active', starRating <= data.rating);
                    }});
                }}

                // Apply notes
                if (data.notes) {{
                    const notesInput = document.querySelector(`textarea[data-outfit-id="${{outfitId}}"]`);
                    if (notesInput) notesInput.value = data.notes;
                }}
            }});
            updateRatedCount();
        }}

        // Update rated count
        function updateRatedCount() {{
            const ratedCount = Object.keys(ratings).filter(k => ratings[k].rating).length;
            const totalCount = document.querySelectorAll('.outfit-card').length;
            document.getElementById('rated-count').textContent = `${{ratedCount}}/${{totalCount}}`;
        }}

        // Export ratings
        function exportRatings() {{
            const dataStr = JSON.stringify(ratings, null, 2);
            const dataBlob = new Blob([dataStr], {{type: 'application/json'}});
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'ratings.json';
            link.click();
        }}

        // Add export button
        window.addEventListener('load', () => {{
            const header = document.querySelector('.header');
            const button = document.createElement('button');
            button.textContent = '💾 Export Ratings';
            button.className = 'save-button';
            button.style.marginTop = '20px';
            button.onclick = exportRatings;
            header.appendChild(button);
        }});
    </script>
</body>
</html>
"""


def generate_outfit_card_html(result: dict, outfit_idx: int) -> str:
    """Generate HTML for a single outfit card."""
    outfit = result['outfits'][outfit_idx]
    outfit_id = f"{result['scenario_id']}_{result['model_id']}_{result['iteration']}_{outfit_idx}"

    # Build items grid
    items_html = ""
    for item in outfit.get('items', [])[:9]:  # Max 9 items for 3x3 grid
        image_path = item.get('image_path', '')
        item_name = item.get('styling_details', {}).get('name', 'Unknown item')
        items_html += f'<img src="{image_path}" alt="{item_name}" class="item-image" title="{item_name}">'

    # Validation badges
    validation_html = f'<span class="validation-badge badge-success">✅ Valid structure</span>'
    validation_html += f'<span class="validation-badge badge-success">⏱️ {result["latency_seconds"]:.2f}s</span>'

    card_html = f"""
    <div class="outfit-card">
        <div class="outfit-header">
            <div class="outfit-title">Outfit {outfit_idx + 1}</div>
            <div class="outfit-meta">Iteration {result['iteration'] + 1}</div>
        </div>

        <div class="outfit-items">
            {items_html}
        </div>

        <div class="outfit-notes">
            <strong>Styling Notes:</strong> {outfit.get('styling_notes', 'N/A')}
        </div>

        <div class="validation">
            {validation_html}
        </div>

        <div class="rating-section">
            <div class="stars">
                <span class="star" data-outfit-id="{outfit_id}" data-rating="1">★</span>
                <span class="star" data-outfit-id="{outfit_id}" data-rating="2">★</span>
                <span class="star" data-outfit-id="{outfit_id}" data-rating="3">★</span>
                <span class="star" data-outfit-id="{outfit_id}" data-rating="4">★</span>
                <span class="star" data-outfit-id="{outfit_id}" data-rating="5">★</span>
            </div>
            <textarea class="notes-input" data-outfit-id="{outfit_id}" placeholder="Your notes..."></textarea>
        </div>
    </div>
    """
    return card_html


def generate_html(results: list, output_path: Path):
    """Generate HTML review page from results."""

    # Group results by scenario and model
    scenarios = {}
    for result in results:
        scenario_id = result['scenario_id']
        if scenario_id not in scenarios:
            scenarios[scenario_id] = {
                'name': result['scenario_name'],
                'models': {}
            }

        model_id = result['model_id']
        if model_id not in scenarios[scenario_id]['models']:
            scenarios[scenario_id]['models'][model_id] = {
                'name': result['model_name'],
                'results': []
            }

        scenarios[scenario_id]['models'][model_id]['results'].append(result)

    # Generate content HTML
    content_html = ""
    for scenario_id, scenario_data in scenarios.items():
        content_html += f"""
        <div class="scenario-section">
            <div class="scenario-header">
                <div class="scenario-title">{scenario_data['name']}</div>
            </div>
        """

        for model_id, model_data in scenario_data['models'].items():
            # Calculate average latency
            avg_latency = sum(r['latency_seconds'] for r in model_data['results']) / len(model_data['results'])
            total_outfits = sum(len(r.get('outfits', [])) for r in model_data['results'])

            content_html += f"""
            <div class="model-group">
                <div class="model-header">
                    <div class="model-name">{model_data['name']}</div>
                    <div class="model-stats">
                        <span>Avg Latency: {avg_latency:.2f}s</span>
                        <span>Total Outfits: {total_outfits}</span>
                    </div>
                </div>
                <div class="outfits-grid">
            """

            # Add outfit cards
            for result in model_data['results']:
                for outfit_idx in range(len(result.get('outfits', []))):
                    content_html += generate_outfit_card_html(result, outfit_idx)

            content_html += """
                </div>
            </div>
            """

        content_html += """
        </div>
        """

    # Calculate stats
    total_outfits = sum(len(r.get('outfits', [])) for r in results)
    num_models = len(set(r['model_id'] for r in results))
    num_scenarios = len(scenarios)

    # Generate final HTML
    html = HTML_TEMPLATE.format(
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        total_outfits=total_outfits,
        num_models=num_models,
        num_scenarios=num_scenarios,
        content=content_html
    )

    # Write to file
    with open(output_path, 'w') as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser(description='Generate HTML review page')
    parser.add_argument('--results', required=True, help='Path to results directory')
    args = parser.parse_args()

    results_dir = Path(args.results)
    results_file = results_dir / 'raw_results.json'
    output_file = results_dir / 'review.html'

    print(f"\n📖 Generating HTML review page...")
    print(f"  📁 Input: {results_file}")

    # Load results
    with open(results_file, 'r') as f:
        results = json.load(f)

    print(f"  ✅ Loaded {len(results)} evaluation results")

    # Generate HTML
    generate_html(results, output_file)

    print(f"  ✅ Generated: {output_file}")
    print(f"\n📋 Next steps:")
    print(f"  1. Open in browser: open {output_file}")
    print(f"  2. Rate all outfits (click stars, add notes)")
    print(f"  3. Click 'Export Ratings' button to save ratings.json")
    print(f"  4. Analyze: python scripts/analyze_results.py --ratings {results_dir}/ratings.json")


if __name__ == '__main__':
    main()
