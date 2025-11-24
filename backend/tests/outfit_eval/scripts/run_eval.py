"""
Run outfit generation evaluation across multiple models.

Usage:
    python run_eval.py --scenarios fixtures/test_scenarios.json --models fixtures/model_configs.yaml --iterations 10
"""

import argparse
import json
import yaml
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import time

# Add backend to path so we can import services
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from services.style_engine import StyleGenerationEngine
from services.wardrobe_manager import WardrobeManager


def load_test_scenarios(scenarios_path: str) -> List[Dict]:
    """Load test scenarios from JSON file."""
    with open(scenarios_path, 'r') as f:
        return json.load(f)


def load_model_configs(models_path: str) -> List[Dict]:
    """Load model configurations from YAML file."""
    with open(models_path, 'r') as f:
        config = yaml.safe_load(f)
        return config['models']


def fetch_user_wardrobe(user_id: str) -> List[Dict]:
    """Fetch wardrobe for a user from production storage."""
    print(f"  📦 Fetching wardrobe for user: {user_id}")
    wardrobe_manager = WardrobeManager(user_id)
    wardrobe = wardrobe_manager.load_wardrobe()

    if not wardrobe or len(wardrobe) == 0:
        raise ValueError(f"No wardrobe found for user {user_id}. User must have uploaded items.")

    print(f"  ✅ Loaded {len(wardrobe)} items")
    return wardrobe


def find_anchor_item(wardrobe: List[Dict], anchor_name: str) -> Dict:
    """Find anchor item in wardrobe by name (fuzzy match)."""
    anchor_name_lower = anchor_name.lower()

    for item in wardrobe:
        item_name = item.get('styling_details', {}).get('name', '').lower()
        if anchor_name_lower in item_name or item_name in anchor_name_lower:
            return item

    # If not found, return first item as fallback
    print(f"  ⚠️  Anchor item '{anchor_name}' not found, using first item as fallback")
    return wardrobe[0] if wardrobe else None


def run_single_evaluation(
    scenario: Dict,
    model_config: Dict,
    iteration: int,
    wardrobe: List[Dict]
) -> Dict:
    """Run a single outfit generation evaluation."""

    # Create style engine with specified model
    engine = StyleGenerationEngine(
        model=model_config['model'],
        temperature=model_config['temperature'],
        max_tokens=model_config['max_tokens']
    )

    # Prepare parameters based on scenario type
    if scenario['scenario_type'] == 'complete_my_look':
        # Find anchor item
        anchor_item = find_anchor_item(wardrobe, scenario.get('anchor_item_name', ''))
        styling_challenges = [anchor_item] if anchor_item else []
    else:
        styling_challenges = []

    # Generate outfits
    start_time = time.time()

    try:
        outfits = engine.generate_outfits(
            user_profile=scenario['style_profile'],
            available_items=wardrobe,
            styling_challenges=styling_challenges,
            occasion=scenario.get('occasion'),
            weather_condition=scenario.get('weather'),
            temperature_range=scenario.get('temperature_range')
        )

        latency = time.time() - start_time
        success = True
        error = None

    except Exception as e:
        latency = time.time() - start_time
        outfits = []
        success = False
        error = str(e)

    return {
        "scenario_id": scenario['id'],
        "scenario_name": scenario['name'],
        "model_id": model_config['id'],
        "model_name": model_config['name'],
        "model": model_config['model'],
        "iteration": iteration,
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "error": error,
        "latency_seconds": latency,
        "outfits": outfits,
        "num_outfits": len(outfits) if outfits else 0
    }


def main():
    parser = argparse.ArgumentParser(description='Run outfit generation evaluation')
    parser.add_argument('--scenarios', default='fixtures/test_scenarios.json', help='Path to test scenarios JSON')
    parser.add_argument('--models', default='fixtures/model_configs.yaml', help='Path to model configs YAML')
    parser.add_argument('--iterations', type=int, default=10, help='Number of iterations per scenario/model')
    parser.add_argument('--output', default=None, help='Output directory (default: results/eval_TIMESTAMP/)')

    args = parser.parse_args()

    # Load configurations
    print("\n📋 Loading configurations...")
    scenarios = load_test_scenarios(args.scenarios)
    model_configs = load_model_configs(args.models)

    print(f"  ✅ Loaded {len(scenarios)} test scenarios")
    print(f"  ✅ Loaded {len(model_configs)} model configurations")

    # Create output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(__file__).parent.parent / 'results' / f'eval_{timestamp}'

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"  📁 Output directory: {output_dir}")

    # Calculate total evaluations
    total_evals = len(scenarios) * len(model_configs) * args.iterations
    print(f"\n🎯 Total evaluations to run: {total_evals}")
    print(f"   ({len(scenarios)} scenarios × {len(model_configs)} models × {args.iterations} iterations)\n")

    # Cache wardrobes (one fetch per user)
    wardrobe_cache = {}

    # Run evaluations
    all_results = []
    eval_count = 0

    for scenario in scenarios:
        print(f"\n{'='*80}")
        print(f"📝 Scenario: {scenario['name']}")
        print(f"{'='*80}")

        # Fetch wardrobe (cached)
        user_id = scenario['user_id']
        if user_id not in wardrobe_cache:
            wardrobe_cache[user_id] = fetch_user_wardrobe(user_id)
        wardrobe = wardrobe_cache[user_id]

        for model_config in model_configs:
            print(f"\n  🤖 Model: {model_config['name']}")

            for iteration in range(args.iterations):
                eval_count += 1
                progress = (eval_count / total_evals) * 100

                print(f"    Iteration {iteration + 1}/{args.iterations} [{progress:.1f}%]...", end=' ', flush=True)

                result = run_single_evaluation(scenario, model_config, iteration, wardrobe)
                all_results.append(result)

                if result['success']:
                    print(f"✅ ({result['latency_seconds']:.2f}s, {result['num_outfits']} outfits)")
                else:
                    print(f"❌ Error: {result['error']}")

    # Save results
    results_file = output_dir / 'raw_results.json'
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n{'='*80}")
    print(f"✅ Evaluation complete!")
    print(f"{'='*80}")
    print(f"📊 Total evaluations: {len(all_results)}")
    print(f"📁 Results saved to: {results_file}")
    print(f"\n📋 Next steps:")
    print(f"  1. Generate review page: python scripts/generate_review.py --results {output_dir}")
    print(f"  2. Open review.html in browser to rate outfits")
    print(f"  3. Analyze results: python scripts/analyze_results.py --ratings {output_dir}/ratings.json")


if __name__ == '__main__':
    main()
