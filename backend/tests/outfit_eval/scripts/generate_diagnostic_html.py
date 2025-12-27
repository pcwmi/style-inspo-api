"""Generate HTML review for diagnostic results with S3 images"""
import json
import os
import sys
from pathlib import Path

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
    # Load diagnostic results
    diagnostic_path = Path(__file__).parent.parent / "DIAGNOSTIC_FINDINGS_RAW.json"
    with open(diagnostic_path) as f:
        diagnostic = json.load(f)

    # Load wardrobe from S3
    print("Loading wardrobe from S3...")
    wm = WardrobeManager(user_id='peichin')
    wardrobe_data = wm.load_wardrobe_data()
    wardrobe_items = wardrobe_data.get('items', [])
    print(f"Loaded {len(wardrobe_items)} items")

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diagnostic Review</title>
    <style>
        body {{ font-family: system-ui; background: #f5f5f5; padding: 20px; }}
        .header {{ background: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; }}
        h1 {{ font-size: 32px; }}
        .section {{ background: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; }}
        .outfit-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; }}
        .outfit-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 20px; background: #fafafa; }}
        .outfit-title {{ font-weight: bold; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #ddd; }}
        .items-container {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 15px 0; }}
        .item-image {{ width: 80px; height: 80px; object-fit: cover; border-radius: 4px; border: 1px solid #ddd; }}
        .item-placeholder {{ width: 80px; height: 80px; background: #e0e0e0; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 10px; text-align: center; padding: 5px; }}
        .styling-notes {{ font-size: 14px; margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 4px; }}
        .marker {{ background: #ff4444; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px; margin-left: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Diagnostic Review: White Sneakers & Shirt Constraint Test</h1>
        <p><strong>User:</strong> peichin | <strong>Wardrobe Items:</strong> {len(wardrobe_items)} | <strong>Scenario:</strong> Outdoor Wedding (75-85°F)</p>
    </div>

    <div class="section">
        <h2>Baseline Generation (No Constraints)</h2>
        <p>Generated {len(diagnostic['baseline'])} outfits with no constraints</p>
        <div class="outfit-grid">
"""

    # Add baseline outfits
    for outfit in diagnostic['baseline']:
        title = f"Iteration {outfit['iteration']}, Outfit {outfit['outfit_num']}"
        markers = []
        if outfit['has_white_sneakers']:
            markers.append('<span class="marker">WHITE SNEAKERS</span>')
        if outfit['has_white_shirt']:
            markers.append('<span class="marker">WHITE SHIRT</span>')
        marker_html = ''.join(markers)

        html += f"""
            <div class="outfit-card">
                <div class="outfit-title">{title} {marker_html}</div>
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
                <div class="styling-notes"><strong>Styling:</strong> {outfit['styling_notes']}</div>
                <div class="styling-notes"><strong>Why it works:</strong> {outfit['why_it_works']}</div>
            </div>
"""

    html += """
        </div>
    </div>

    <div class="section">
        <h2>Constrained Generation (No White Sneakers/Shirts)</h2>
        <p>Generated {len} outfits with explicit exclusion of white sneakers and white ruffled shirt</p>
        <div class="outfit-grid">
""".replace('{len}', str(len(diagnostic['constrained'])))

    # Add constrained outfits
    for outfit in diagnostic['constrained']:
        title = f"Iteration {outfit['iteration']}, Outfit {outfit['outfit_num']}"

        html += f"""
            <div class="outfit-card">
                <div class="outfit-title">{title}</div>
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
                <div class="styling-notes"><strong>Styling:</strong> {outfit['styling_notes']}</div>
                <div class="styling-notes"><strong>Why it works:</strong> {outfit['why_it_works']}</div>
            </div>
"""

    html += """
        </div>
    </div>
</body>
</html>
"""

    # Save HTML
    output_path = Path(__file__).parent.parent / "DIAGNOSTIC_REVIEW.html"
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ HTML saved to: {output_path}")

if __name__ == '__main__':
    main()
