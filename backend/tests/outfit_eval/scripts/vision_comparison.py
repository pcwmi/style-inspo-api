#!/usr/bin/env python3
"""Side-by-side comparison of text-only vs vision-informed outfit generation."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dotenv import load_dotenv
load_dotenv()

from services.style_engine import StyleGenerationEngine
from services.wardrobe_manager import WardrobeManager


def run_comparison(num_items: int = 50):
    """Run side-by-side comparison of text vs vision generation."""

    # Load full wardrobe
    wm = WardrobeManager(user_id='peichin')
    all_items = wm.wardrobe_data.get('items', [])
    print(f"📦 Total wardrobe items: {len(all_items)}")

    # Filter to items with S3 image URLs for vision test
    items_with_images = [
        item for item in all_items
        if item.get('system_metadata', {}).get('image_path', '').startswith('http')
    ]
    print(f"🖼️  Items with S3 images: {len(items_with_images)}")

    # Use requested number of items
    test_items = items_with_images[:num_items]
    print(f"📊 Using {len(test_items)} items for this test\n")

    user_profile = {
        'three_words': {'current': 'casual', 'aspirational': 'polished', 'feeling': 'chic'}
    }
    occasion = 'casual coffee with friends followed by some errands'
    weather = 'mild'
    temp_range = '60-70F'

    # Run both variants
    results = {}

    for variant_name, prompt_version in [
        ("TEXT-ONLY (Control)", "baseline_v1"),
        ("VISION (Treatment)", "vision_v1")
    ]:
        print("=" * 80)
        print(f"🧪 {variant_name}")
        print("=" * 80)

        engine = StyleGenerationEngine(
            api_key=os.getenv('OPENAI_API_KEY'),
            model='gpt-4o',
            temperature=0.7,
            max_tokens=2000,
            prompt_version=prompt_version
        )

        result = engine.generate_outfit_combinations(
            user_profile=user_profile,
            available_items=test_items,
            styling_challenges=[],
            occasion=occasion,
            weather_condition=weather,
            temperature_range=temp_range,
            user_id='peichin'
        )

        # Store for comparison
        if isinstance(result, dict):
            outfits = result.get('outfits', [])
        else:
            outfits = result

        results[variant_name] = outfits
        print(f"\n✅ {variant_name}: Generated {len(outfits)} outfits\n")

    # Side-by-side comparison
    print("\n" + "=" * 80)
    print("📊 SIDE-BY-SIDE COMPARISON")
    print("=" * 80)

    for i in range(3):
        print(f"\n{'─' * 80}")
        print(f"OUTFIT {i+1}")
        print(f"{'─' * 80}")

        for variant_name in ["TEXT-ONLY (Control)", "VISION (Treatment)"]:
            outfits = results[variant_name]
            if i < len(outfits):
                outfit = outfits[i]
                if hasattr(outfit, '__dict__'):
                    outfit = outfit.__dict__

                items = outfit.get('items', [])
                if items and isinstance(items[0], dict):
                    item_names = [item.get('styling_details', {}).get('name', 'Unknown') for item in items]
                else:
                    item_names = items if items else []

                print(f"\n[{variant_name}]")
                print(f"  Items: {', '.join(item_names)}")
                print(f"  Styling Notes: {outfit.get('styling_notes', 'N/A')[:400]}")
                print(f"  Why It Works: {outfit.get('why_it_works', 'N/A')[:400]}")

                # Show physical sensibility if present (this is where vision should shine)
                principles = outfit.get('constitution_principles', {})
                if principles:
                    phys = principles.get('physical_sensibility', '')
                    if phys:
                        print(f"  Physical Sensibility: {phys}")

    print("\n✅ Comparison complete!")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--items', type=int, default=50, help='Number of items to use')
    args = parser.parse_args()
    run_comparison(args.items)
