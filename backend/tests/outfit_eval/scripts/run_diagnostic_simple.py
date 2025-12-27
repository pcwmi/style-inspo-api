"""
Simplified diagnostic test for outfit generation reasoning.
Focuses on core generation tests without Q&A functionality.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from services.style_engine import StyleGenerationEngine
from services.wardrobe_manager import WardrobeManager


def extract_item_name(item):
    """Extract item name from OutfitItem object or dict"""
    if hasattr(item, 'name'):
        return item.name
    elif isinstance(item, dict) and 'styling_details' in item:
        return item['styling_details'].get('name', str(item))
    elif isinstance(item, dict) and 'name' in item:
        return item['name']
    else:
        return str(item)


def main():
    print("\n" + "="*80)
    print("DIAGNOSTIC TEST: Outfit Generation Frequency Patterns")
    print("="*80 + "\n")

    # Load wardrobe
    print("📦 Loading wardrobe...")
    wm = WardrobeManager(user_id="peichin")
    wardrobe_data = wm.load_wardrobe_data()
    wardrobe = wardrobe_data.get('items', [])
    print(f"✅ Loaded {len(wardrobe)} items\n")

    # Test scenario
    scenario = {
        "occasion": "outdoor wedding in the afternoon",
        "weather": "sunny and warm",
        "temperature_range": "75-85°F",
        "style_profile": {
            "three_words": {
                "current": "classic",
                "aspirational": "relaxed",
                "feeling": "playful"
            }
        }
    }

    # Storage for results
    baseline_results = []
    constrained_results = []

    # Test 1A: Baseline Generation
    print("="*80)
    print("TEST 1A: Baseline Generation (5 iterations)")
    print("="*80 + "\n")

    engine = StyleGenerationEngine(
        model="gpt-4o",
        temperature=0.7,
        max_tokens=2000,
        prompt_version="baseline_v1"
    )

    for i in range(5):
        print(f"🎨 Iteration {i+1}/5...")

        try:
            outfits = engine.generate_outfit_combinations(
                user_profile=scenario['style_profile'],
                available_items=wardrobe,
                styling_challenges=[],
                occasion=scenario['occasion'],
                weather_condition=scenario['weather'],
                temperature_range=scenario['temperature_range']
            )

            for idx, outfit in enumerate(outfits):
                # Extract item names
                item_names = [extract_item_name(item) for item in outfit.items]

                # Check for white items
                has_white_sneakers = any('white' in name.lower() and 'sneaker' in name.lower() for name in item_names)
                has_white_shirt = any('white' in name.lower() and ('shirt' in name.lower() or 't-shirt' in name.lower()) for name in item_names)

                result = {
                    "iteration": i + 1,
                    "outfit_num": idx + 1,
                    "items": item_names,
                    "has_white_sneakers": has_white_sneakers,
                    "has_white_shirt": has_white_shirt,
                    "styling_notes": outfit.styling_notes,
                    "why_it_works": outfit.why_it_works
                }

                baseline_results.append(result)

                # Print summary
                markers = []
                if has_white_sneakers:
                    markers.append("🔴 WHITE SNEAKERS")
                if has_white_shirt:
                    markers.append("🔴 WHITE SHIRT")

                marker_str = " | ".join(markers) if markers else ""
                print(f"  Outfit {idx+1}: {len(item_names)} items {marker_str}")
                for name in item_names:
                    print(f"    - {name}")

            time.sleep(1)  # Rate limiting

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print()

    # Test 1B: Constrained Generation
    print("="*80)
    print("TEST 1B: Constrained Generation (5 iterations)")
    print("="*80)
    print("Constraint: Do NOT use white sneakers OR white shirts\n")

    for i in range(5):
        print(f"🎨 Iteration {i+1}/5...")

        # Inject constraint into occasion
        constrained_occasion = f"{scenario['occasion']} (CONSTRAINT: Do NOT use white sneakers with red Nike logo OR white button-down shirt with ruffled details)"

        try:
            outfits = engine.generate_outfit_combinations(
                user_profile=scenario['style_profile'],
                available_items=wardrobe,
                styling_challenges=[],
                occasion=constrained_occasion,
                weather_condition=scenario['weather'],
                temperature_range=scenario['temperature_range']
            )

            for idx, outfit in enumerate(outfits):
                # Extract item names
                item_names = [extract_item_name(item) for item in outfit.items]

                # Check for white items (should NOT appear)
                has_white_sneakers = any('white' in name.lower() and 'sneaker' in name.lower() for name in item_names)
                has_white_shirt = any('white' in name.lower() and ('shirt' in name.lower() or 't-shirt' in name.lower()) for name in item_names)

                # Find shoe and top substitutes
                shoes = [name for name in item_names if any(s in name.lower() for s in ['shoe', 'boot', 'sneaker', 'heel', 'sandal'])]
                tops = [name for name in item_names if any(t in name.lower() for t in ['shirt', 'top', 'blouse', 't-shirt', 'tee', 'dress'])]

                result = {
                    "iteration": i + 1,
                    "outfit_num": idx + 1,
                    "items": item_names,
                    "has_white_sneakers": has_white_sneakers,
                    "has_white_shirt": has_white_shirt,
                    "shoe_substitutes": shoes,
                    "top_substitutes": tops,
                    "styling_notes": outfit.styling_notes,
                    "why_it_works": outfit.why_it_works
                }

                constrained_results.append(result)

                # Print summary
                violations = []
                if has_white_sneakers:
                    violations.append("⚠️ WHITE SNEAKERS VIOLATION")
                if has_white_shirt:
                    violations.append("⚠️ WHITE SHIRT VIOLATION")

                violation_str = " | ".join(violations) if violations else "✅ No violations"
                print(f"  Outfit {idx+1}: {len(item_names)} items | {violation_str}")
                print(f"    Shoes: {', '.join(shoes) if shoes else 'None'}")
                print(f"    Tops: {', '.join(tops) if tops else 'None'}")

            time.sleep(1)  # Rate limiting

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print()

    # Calculate statistics
    print("="*80)
    print("FREQUENCY ANALYSIS")
    print("="*80 + "\n")

    baseline_sneakers = sum(1 for r in baseline_results if r['has_white_sneakers'])
    baseline_shirts = sum(1 for r in baseline_results if r['has_white_shirt'])
    baseline_total = len(baseline_results)

    constrained_sneakers = sum(1 for r in constrained_results if r['has_white_sneakers'])
    constrained_shirts = sum(1 for r in constrained_results if r['has_white_shirt'])
    constrained_total = len(constrained_results)

    print(f"📊 Baseline Results ({baseline_total} outfits):")
    print(f"  White sneakers: {baseline_sneakers} / {baseline_total} ({baseline_sneakers/baseline_total*100:.1f}%)")
    print(f"  White shirts: {baseline_shirts} / {baseline_total} ({baseline_shirts/baseline_total*100:.1f}%)")
    print()

    print(f"📊 Constrained Results ({constrained_total} outfits):")
    print(f"  White sneakers: {constrained_sneakers} / {constrained_total} ({constrained_sneakers/constrained_total*100 if constrained_total > 0 else 0:.1f}%)")
    print(f"  White shirts: {constrained_shirts} / {constrained_total} ({constrained_shirts/constrained_total*100 if constrained_total > 0 else 0:.1f}%)")
    print()

    if constrained_sneakers > 0 or constrained_shirts > 0:
        print("⚠️  CONSTRAINT VIOLATIONS DETECTED")
        print("   Model used excluded items even when explicitly told not to.")
    else:
        print("✅ No constraint violations - model respected exclusions")

    print()

    # Save results
    output_dir = Path(__file__).parent.parent
    output_file = output_dir / "DIAGNOSTIC_FINDINGS_RAW.json"

    findings = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "user_id": "peichin",
            "total_wardrobe_items": len(wardrobe),
            "scenario": scenario
        },
        "baseline": baseline_results,
        "constrained": constrained_results,
        "statistics": {
            "baseline": {
                "total_outfits": baseline_total,
                "white_sneakers_count": baseline_sneakers,
                "white_sneakers_frequency": baseline_sneakers / baseline_total if baseline_total > 0 else 0,
                "white_shirt_count": baseline_shirts,
                "white_shirt_frequency": baseline_shirts / baseline_total if baseline_total > 0 else 0
            },
            "constrained": {
                "total_outfits": constrained_total,
                "white_sneakers_count": constrained_sneakers,
                "white_sneakers_frequency": constrained_sneakers / constrained_total if constrained_total > 0 else 0,
                "white_shirt_count": constrained_shirts,
                "white_shirt_frequency": constrained_shirts / constrained_total if constrained_total > 0 else 0
            }
        }
    }

    with open(output_file, 'w') as f:
        json.dump(findings, f, indent=2, default=str)

    print(f"💾 Results saved to: {output_file}")
    print()
    print("="*80)
    print("✅ DIAGNOSTIC TEST COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
