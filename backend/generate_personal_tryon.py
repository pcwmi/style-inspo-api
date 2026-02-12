"""
Generate 3x3 try-on comparison for LinkedIn post.

Compares 3 outfits × 3 variations:
1. Personal photo try-on (user's actual photo)
2. Runway Gen-4 (gen4_image) with descriptor
3. Nano Banana (gemini_2.5_flash) with descriptor
"""

import os
import sys
import time
from datetime import datetime
from PIL import Image

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.saved_outfits_manager import SavedOutfitsManager
from services.visualization.providers.runway import RunwayProvider, ImageGenerationRequest

USER_ID = "peichin"
PERSONAL_PHOTO_PATH = "/Users/peichin/Downloads/IMG_3748.jpg"
OUTPUT_DIR = "/Users/peichin/Projects/style-inspo-api/.claude"

# Updated descriptor
DESCRIPTOR = "5 feet 4 eastern asian with black wavy hair at chest length"

# 3 variations to test
VARIATIONS = [
    {"name": "Personal Photo", "mode": "personal", "model": "gen4_image"},
    {"name": "Runway Gen-4", "mode": "model", "model": "gen4_image"},
    {"name": "Nano Banana", "mode": "model", "model": "gemini_2.5_flash"},
]


def resize_photo_for_runway(photo_path: str, max_size_mb: float = 4.0) -> str:
    """Resize photo to meet Runway's size limits."""
    file_size_mb = os.path.getsize(photo_path) / (1024 * 1024)
    print(f"  Original photo size: {file_size_mb:.1f}MB")

    if file_size_mb <= max_size_mb:
        return photo_path

    img = Image.open(photo_path)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    scale = (max_size_mb / file_size_mb) ** 0.5
    new_width = int(img.width * scale)
    new_height = int(img.height * scale)

    print(f"  Resizing from {img.width}x{img.height} to {new_width}x{new_height}")
    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    temp_path = "/tmp/runway_user_photo_resized.jpg"
    img_resized.save(temp_path, "JPEG", quality=85)

    new_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
    print(f"  Resized photo size: {new_size_mb:.1f}MB")

    return temp_path


def get_outfits_4_to_6():
    """Get 4th to 6th most recent saved outfits with visualizations."""
    manager = SavedOutfitsManager(user_id=USER_ID)
    outfits = manager.get_saved_outfits()

    # Filter to outfits that have visualizations
    with_viz = [o for o in outfits if o.get("visualization_url")]

    print(f"Found {len(with_viz)} outfits with visualizations out of {len(outfits)} total")
    print(f"Selecting outfits 4-6 (indices 3-5)")

    return with_viz[3:6]  # Skip first 3, take next 3


def generate_tryon(outfit, provider, variation, resized_photo_path):
    """Generate a single try-on variation."""
    outfit_data = outfit.get("outfit_data", {})
    items = outfit_data.get("items", [])

    # Build outfit description from items
    item_descriptions = []
    garment_images = []
    for item in items:
        name = item.get("name", "")
        if name:
            item_descriptions.append(name)
        image_url = item.get("image_url") or item.get("image_path")
        if image_url:
            garment_images.append(image_url)

    outfit_description = ", ".join(item_descriptions)

    # Determine mode and model
    mode = variation["mode"]
    model = variation["model"]

    # Personal mode uses user photo (counts as 1 ref image, so max 2 garments)
    # Model mode can use all 3 garment slots
    max_garments = 2 if mode == "personal" else 3

    request = ImageGenerationRequest(
        garment_images=garment_images[:max_garments],
        prompt_text=outfit_description,
        styling_notes=outfit_data.get("styling_notes", ""),
        mode=mode,
        user_photo=resized_photo_path if mode == "personal" else None
    )

    # Use descriptor only for model modes
    descriptor = DESCRIPTOR if mode == "model" else None

    # Generate
    start_time = time.time()
    result = provider.generate_image(request, model_descriptor=descriptor, model=model)
    latency = time.time() - start_time

    if result.success:
        return result.image_url, latency
    else:
        print(f"    ✗ Failed: {result.error_message}")
        return None, latency


def generate_comparison_html(results, output_path):
    """Generate HTML showing 3x3 comparison grid with latency."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>3x3 Try-On Comparison</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        h1 {{ text-align: center; margin-bottom: 5px; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 20px; }}
        .descriptor {{ text-align: center; background: #e3f2fd; padding: 10px; border-radius: 8px; margin-bottom: 20px; font-family: monospace; }}
        .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 30px; }}
        .header {{ font-weight: 600; text-align: center; padding: 10px; background: #333; color: white; border-radius: 8px 8px 0 0; }}
        .cell {{ background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .cell img {{ width: 100%; height: 400px; object-fit: cover; }}
        .latency {{ text-align: center; padding: 8px; font-size: 14px; color: #666; background: #f9f9f9; }}
        .outfit-row {{ margin-bottom: 30px; }}
        .outfit-label {{ text-align: center; font-weight: 600; margin: 15px 0; padding: 10px; background: #fff3e0; border-radius: 8px; }}
        .summary {{ background: white; padding: 20px; border-radius: 8px; margin-top: 20px; }}
        .summary h3 {{ margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px 12px; border: 1px solid #ddd; text-align: left; }}
        th {{ background: #f5f5f5; }}
        .personal {{ background: #ffebee; }}
        .runway {{ background: #e8f5e9; }}
        .nano {{ background: #e3f2fd; }}
    </style>
</head>
<body>
    <h1>3x3 Try-On Comparison</h1>
    <p class="subtitle">Personal Photo vs Runway Gen-4 vs Nano Banana</p>
    <div class="descriptor">Descriptor: "{DESCRIPTOR}"</div>

    <!-- Column Headers -->
    <div class="grid">
        <div class="header personal">Personal Photo</div>
        <div class="header runway">Runway Gen-4</div>
        <div class="header nano">Nano Banana</div>
    </div>
"""

    # Add each outfit row
    for outfit_idx, outfit_result in enumerate(results):
        outfit_name = outfit_result["outfit_description"][:80] + "..."

        html += f"""
    <div class="outfit-row">
        <div class="grid">
"""
        for var_idx, var in enumerate(VARIATIONS):
            img_data = outfit_result["variations"][var_idx]
            img_url = img_data["url"] or "about:blank"
            latency = img_data["latency"]
            var_class = ["personal", "runway", "nano"][var_idx]

            html += f"""            <div class="cell {var_class}">
                <img src="{img_url}" alt="{var['name']}">
                <div class="latency">{latency:.1f}s</div>
            </div>
"""

        html += f"""        </div>
        <div class="outfit-label">Outfit {outfit_idx + 4}: {outfit_name}</div>
    </div>
"""

    # Summary table
    html += """
    <div class="summary">
        <h3>Latency Summary</h3>
        <table>
            <tr>
                <th>Outfit</th>
                <th>Personal Photo</th>
                <th>Runway Gen-4</th>
                <th>Nano Banana</th>
            </tr>
"""
    for outfit_idx, outfit_result in enumerate(results):
        personal_lat = outfit_result["variations"][0]["latency"]
        runway_lat = outfit_result["variations"][1]["latency"]
        nano_lat = outfit_result["variations"][2]["latency"]
        html += f"""            <tr>
                <td>Outfit {outfit_idx + 4}</td>
                <td>{personal_lat:.1f}s</td>
                <td>{runway_lat:.1f}s</td>
                <td>{nano_lat:.1f}s</td>
            </tr>
"""

    # Calculate averages
    avg_personal = sum(r["variations"][0]["latency"] for r in results) / len(results)
    avg_runway = sum(r["variations"][1]["latency"] for r in results) / len(results)
    avg_nano = sum(r["variations"][2]["latency"] for r in results) / len(results)

    html += f"""            <tr style="font-weight: bold; background: #f5f5f5;">
                <td>Average</td>
                <td>{avg_personal:.1f}s</td>
                <td>{avg_runway:.1f}s</td>
                <td>{avg_nano:.1f}s</td>
            </tr>
        </table>
    </div>
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"\nHTML saved to: {output_path}")
    return output_path


def main():
    print("=" * 60)
    print("3x3 Try-On Comparison Generator")
    print("Personal Photo vs Runway Gen-4 vs Nano Banana")
    print("=" * 60)

    # Verify photo exists
    if not os.path.exists(PERSONAL_PHOTO_PATH):
        print(f"Error: Photo not found at {PERSONAL_PHOTO_PATH}")
        return

    print(f"\n1. Using personal photo: {PERSONAL_PHOTO_PATH}")
    resized_photo_path = resize_photo_for_runway(PERSONAL_PHOTO_PATH)

    print(f"\n2. Using descriptor: {DESCRIPTOR}")

    # Get outfits 4-6
    print("\n3. Getting saved outfits 4-6...")
    outfits = get_outfits_4_to_6()

    if len(outfits) < 3:
        print(f"Not enough outfits! Found {len(outfits)}, need 3")
        return

    # Initialize Runway provider
    print("\n4. Initializing Runway provider...")
    provider = RunwayProvider()

    # Generate all 9 variations
    print("\n5. Generating 9 try-ons (3 outfits × 3 variations)...")
    print("   This will take approximately 4-5 minutes...\n")

    results = []
    total_start = time.time()

    for outfit_idx, outfit in enumerate(outfits):
        outfit_data = outfit.get("outfit_data", {})
        items = outfit_data.get("items", [])
        item_names = [item.get("name", "") for item in items if item.get("name")]
        outfit_desc = ", ".join(item_names)

        print(f"Outfit {outfit_idx + 4}/6: {outfit_desc[:60]}...")

        outfit_result = {
            "outfit_description": outfit_desc,
            "variations": []
        }

        for var_idx, variation in enumerate(VARIATIONS):
            print(f"  [{var_idx + 1}/3] {variation['name']} ({variation['model']})...")

            url, latency = generate_tryon(outfit, provider, variation, resized_photo_path)

            if url:
                print(f"    ✓ Generated in {latency:.1f}s")
            else:
                print(f"    ✗ Failed after {latency:.1f}s")

            outfit_result["variations"].append({
                "name": variation["name"],
                "model": variation["model"],
                "url": url,
                "latency": latency
            })

        results.append(outfit_result)
        print()

    total_time = time.time() - total_start
    print(f"Total generation time: {total_time:.1f}s ({total_time/60:.1f} minutes)")

    # Generate comparison HTML
    print("\n6. Generating comparison HTML...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{OUTPUT_DIR}/3x3_comparison_{timestamp}.html"
    generate_comparison_html(results, output_path)

    print("\n" + "=" * 60)
    print("Done! Opening HTML...")
    os.system(f"open {output_path}")


if __name__ == "__main__":
    main()
