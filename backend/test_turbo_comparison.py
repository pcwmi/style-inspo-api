"""
Gen-4 Standard vs Turbo Vibe Comparison.

Compares 5 outfits × 2 models:
1. gen4_image (current baseline — proven editorial vibe)
2. gen4_image_turbo (faster, cheaper — vibe unknown)

Goal: Does turbo preserve Runway's inspirational/editorial aesthetic?
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.saved_outfits_manager import SavedOutfitsManager
from services.visualization.providers.runway import RunwayProvider, ImageGenerationRequest

USER_ID = "peichin"
OUTPUT_DIR = "/Users/peichin/Projects/style-inspo-api/.claude"
DESCRIPTOR = "5 feet 4 eastern asian with black wavy hair at chest length"

VARIATIONS = [
    {"name": "Gen-4 Standard", "model": "gen4_image", "credits": 5},
    {"name": "Gen-4 Turbo", "model": "gen4_image_turbo", "credits": 2},
]

NUM_OUTFITS = 5


def get_outfits(n=NUM_OUTFITS):
    """Get the most recent saved outfits with visualizations."""
    manager = SavedOutfitsManager(user_id=USER_ID)
    outfits = manager.get_saved_outfits()
    with_viz = [o for o in outfits if o.get("visualization_url")]
    print(f"Found {len(with_viz)} outfits with visualizations out of {len(outfits)} total")
    print(f"Selecting first {n}")
    return with_viz[:n]


def generate_variation(outfit, provider, variation):
    """Generate a single visualization variation."""
    outfit_data = outfit.get("outfit_data", {})
    items = outfit_data.get("items", [])

    item_descriptions = []
    garment_images = []
    for item in items:
        name = item.get("name", "")
        if name:
            item_descriptions.append(name)
        image_url = item.get("image_url") or item.get("image_path")
        if image_url:
            garment_images.append(image_url)

    request = ImageGenerationRequest(
        garment_images=garment_images[:3],
        prompt_text=", ".join(item_descriptions),
        styling_notes=outfit_data.get("styling_notes", ""),
        mode="model",
    )

    start_time = time.time()
    result = provider.generate_image(request, model_descriptor=DESCRIPTOR, model=variation["model"])
    latency = time.time() - start_time

    if result.success:
        return result.image_url, latency
    else:
        print(f"    FAILED: {result.error_message}")
        return None, latency


def generate_html(results, output_path):
    """Generate side-by-side comparison HTML."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Gen-4 Standard vs Turbo Vibe Comparison</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        h1 {{ text-align: center; margin-bottom: 5px; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 20px; }}
        .descriptor {{ text-align: center; background: #e3f2fd; padding: 10px; border-radius: 8px; margin-bottom: 20px; font-family: monospace; }}
        .question {{ text-align: center; background: #fff3e0; padding: 15px; border-radius: 8px; margin-bottom: 25px; font-size: 18px; font-weight: 600; }}
        .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 10px; }}
        .header {{ font-weight: 600; text-align: center; padding: 10px; border-radius: 8px 8px 0 0; }}
        .header.standard {{ background: #2e7d32; color: white; }}
        .header.turbo {{ background: #1565c0; color: white; }}
        .cell {{ background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .cell img {{ width: 100%; height: auto; max-height: 600px; object-fit: contain; cursor: pointer; }}
        .cell img:hover {{ opacity: 0.9; }}
        .latency {{ text-align: center; padding: 8px; font-size: 14px; color: #666; background: #f9f9f9; }}
        .outfit-row {{ margin-bottom: 30px; }}
        .outfit-label {{ text-align: center; font-weight: 600; margin: 5px 0 20px; padding: 10px; background: #fff3e0; border-radius: 8px; font-size: 13px; }}
        .summary {{ background: white; padding: 20px; border-radius: 8px; margin-top: 20px; }}
        .summary h3 {{ margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px 12px; border: 1px solid #ddd; text-align: left; }}
        th {{ background: #f5f5f5; }}
        .faster {{ color: #2e7d32; font-weight: 600; }}
        .fullscreen-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 1000; justify-content: center; align-items: center; cursor: pointer; }}
        .fullscreen-overlay img {{ max-width: 95%; max-height: 95%; object-fit: contain; }}
        .fullscreen-overlay.active {{ display: flex; }}
    </style>
</head>
<body>
    <h1>Gen-4 Standard vs Turbo</h1>
    <p class="subtitle">Vibe Comparison &mdash; {datetime.now().strftime("%b %d, %Y %I:%M %p")}</p>
    <div class="descriptor">Descriptor: "{DESCRIPTOR}"</div>
    <div class="question">Does Turbo feel as inspiring as Standard?</div>

    <div class="grid">
        <div class="header standard">Gen-4 Standard (baseline)</div>
        <div class="header turbo">Gen-4 Turbo (faster/cheaper)</div>
    </div>
"""

    for outfit_idx, outfit_result in enumerate(results):
        outfit_name = outfit_result["outfit_description"][:100]
        html += f"""
    <div class="outfit-row">
        <div class="grid">
"""
        for var_idx, var in enumerate(VARIATIONS):
            img_data = outfit_result["variations"][var_idx]
            img_url = img_data["url"] or "about:blank"
            latency = img_data["latency"]
            var_class = "standard" if var_idx == 0 else "turbo"

            html += f"""            <div class="cell">
                <img src="{img_url}" alt="{var['name']}" onclick="openFullscreen(this.src)">
                <div class="latency">{latency:.1f}s &mdash; {var['credits']} credits</div>
            </div>
"""

        html += f"""        </div>
        <div class="outfit-label">Outfit {outfit_idx + 1}: {outfit_name}</div>
    </div>
"""

    # Summary table
    successful_standard = [r["variations"][0] for r in results if r["variations"][0]["url"]]
    successful_turbo = [r["variations"][1] for r in results if r["variations"][1]["url"]]

    avg_standard = sum(v["latency"] for v in successful_standard) / len(successful_standard) if successful_standard else 0
    avg_turbo = sum(v["latency"] for v in successful_turbo) / len(successful_turbo) if successful_turbo else 0
    speedup = avg_standard / avg_turbo if avg_turbo > 0 else 0

    html += f"""
    <div class="summary">
        <h3>Results Summary</h3>
        <table>
            <tr>
                <th>Outfit</th>
                <th>Standard (s)</th>
                <th>Turbo (s)</th>
                <th>Speedup</th>
            </tr>
"""
    for outfit_idx, outfit_result in enumerate(results):
        s_lat = outfit_result["variations"][0]["latency"]
        t_lat = outfit_result["variations"][1]["latency"]
        s_ok = "OK" if outfit_result["variations"][0]["url"] else "FAIL"
        t_ok = "OK" if outfit_result["variations"][1]["url"] else "FAIL"
        sp = f"{s_lat / t_lat:.1f}x" if t_lat > 0 and outfit_result["variations"][1]["url"] else "N/A"

        html += f"""            <tr>
                <td>Outfit {outfit_idx + 1}</td>
                <td>{s_lat:.1f}s ({s_ok})</td>
                <td>{t_lat:.1f}s ({t_ok})</td>
                <td class="faster">{sp}</td>
            </tr>
"""

    html += f"""            <tr style="font-weight: bold; background: #f5f5f5;">
                <td>Average</td>
                <td>{avg_standard:.1f}s</td>
                <td>{avg_turbo:.1f}s</td>
                <td class="faster">{speedup:.1f}x faster</td>
            </tr>
            <tr style="background: #e8f5e9;">
                <td>Cost per image</td>
                <td>5 credits</td>
                <td>2 credits</td>
                <td class="faster">2.5x cheaper</td>
            </tr>
        </table>
    </div>

    <div class="fullscreen-overlay" id="overlay" onclick="closeFullscreen()">
        <img id="fullscreen-img" src="">
    </div>
    <script>
        function openFullscreen(src) {{
            document.getElementById('fullscreen-img').src = src;
            document.getElementById('overlay').classList.add('active');
        }}
        function closeFullscreen() {{
            document.getElementById('overlay').classList.remove('active');
        }}
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') closeFullscreen();
        }});
    </script>
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)
    print(f"\nHTML saved to: {output_path}")
    return output_path


def main():
    print("=" * 60)
    print("Gen-4 Standard vs Turbo Vibe Comparison")
    print("=" * 60)

    print(f"\n1. Descriptor: {DESCRIPTOR}")

    print(f"\n2. Getting {NUM_OUTFITS} saved outfits...")
    outfits = get_outfits()

    if len(outfits) < NUM_OUTFITS:
        print(f"Only found {len(outfits)} outfits, using all of them")

    print(f"\n3. Initializing Runway provider...")
    provider = RunwayProvider()

    print(f"\n4. Generating {len(outfits) * len(VARIATIONS)} images ({len(outfits)} outfits x {len(VARIATIONS)} models)...")
    est_time = len(outfits) * (30 + 12)
    print(f"   Estimated time: ~{est_time // 60}m {est_time % 60}s\n")

    results = []
    total_start = time.time()

    for outfit_idx, outfit in enumerate(outfits):
        outfit_data = outfit.get("outfit_data", {})
        items = outfit_data.get("items", [])
        item_names = [item.get("name", "") for item in items if item.get("name")]
        outfit_desc = ", ".join(item_names)

        print(f"Outfit {outfit_idx + 1}/{len(outfits)}: {outfit_desc[:60]}...")

        outfit_result = {
            "outfit_description": outfit_desc,
            "variations": []
        }

        for var_idx, variation in enumerate(VARIATIONS):
            print(f"  [{var_idx + 1}/{len(VARIATIONS)}] {variation['name']} ({variation['model']})...")

            url, latency = generate_variation(outfit, provider, variation)

            if url:
                print(f"    OK {latency:.1f}s")
            else:
                print(f"    FAIL {latency:.1f}s")

            outfit_result["variations"].append({
                "name": variation["name"],
                "model": variation["model"],
                "url": url,
                "latency": latency
            })

        results.append(outfit_result)
        print()

    total_time = time.time() - total_start
    print(f"Total: {total_time:.1f}s ({total_time / 60:.1f} minutes)")

    print("\n5. Generating comparison HTML...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{OUTPUT_DIR}/turbo_vibe_comparison_{timestamp}.html"
    generate_html(results, output_path)

    print("\nDone! Opening HTML...")
    os.system(f"open {output_path}")


if __name__ == "__main__":
    main()
