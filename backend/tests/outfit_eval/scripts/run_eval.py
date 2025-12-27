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


def load_preset(preset_name: str) -> Dict:
    """Load eval preset configuration from YAML file."""
    presets_path = Path(__file__).parent.parent / 'fixtures' / 'eval_presets.yaml'
    with open(presets_path, 'r') as f:
        presets = yaml.safe_load(f)

    if preset_name not in presets:
        available = ', '.join(presets.keys())
        raise ValueError(f"Preset '{preset_name}' not found. Available presets: {available}")

    return presets[preset_name]


def list_available_presets():
    """Display all available eval presets with descriptions."""
    presets_path = Path(__file__).parent.parent / 'fixtures' / 'eval_presets.yaml'

    if not presets_path.exists():
        print("❌ No presets file found at:", presets_path)
        return

    with open(presets_path, 'r') as f:
        presets = yaml.safe_load(f)

    print("\n📦 Available Eval Presets:\n")
    for name, config in presets.items():
        description = config.get('description', 'No description')
        print(f"  • {name}")
        print(f"    {description}")
        print()

    print("Usage: python3 scripts/run_eval.py --preset <preset_name>")
    print("Example: python3 scripts/run_eval.py --preset baseline-vs-cot\n")


def apply_model_filters(models: List[Dict], model_filter: str = None, model_ids: List[str] = None) -> List[Dict]:
    """Apply model filters to model configurations."""
    if model_ids:
        # Explicit list of model IDs
        return [m for m in models if m['id'] in model_ids]
    elif model_filter:
        # Substring filter on model ID
        return [m for m in models if model_filter.lower() in m['id'].lower()]
    return models


def apply_scenario_filters(scenarios: List[Dict], scenario_filter: str = None, user_filter: str = None) -> List[Dict]:
    """Apply filters to test scenarios."""
    filtered = scenarios

    if scenario_filter:
        # Substring filter on scenario name or ID
        filtered = [s for s in filtered
                   if scenario_filter.lower() in s['name'].lower()
                   or scenario_filter.lower() in s['id'].lower()]

    if user_filter:
        # Exact match on user_id
        filtered = [s for s in filtered if s.get('user_id') == user_filter]

    return filtered


def fetch_user_wardrobe(user_id: str) -> List[Dict]:
    """Fetch wardrobe for a user from production storage."""
    print(f"  📦 Fetching wardrobe for user: {user_id}")

    # Debug: Check storage configuration
    storage_type = os.getenv("STORAGE_TYPE", "local")
    print(f"  🔧 STORAGE_TYPE env var: '{storage_type}'")

    wardrobe_manager = WardrobeManager(user_id=user_id)
    print(f"  🔧 Storage type in use: {wardrobe_manager.storage.storage_type}")

    wardrobe_data = wardrobe_manager.load_wardrobe_data()
    print(f"  🔧 Wardrobe data keys: {wardrobe_data.keys() if wardrobe_data else 'None'}")

    # Extract items array from wardrobe data
    wardrobe = wardrobe_data.get('items', [])

    if not wardrobe or len(wardrobe) == 0:
        print(f"  ❌ Wardrobe data: {wardrobe_data}")
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

    # Create style engine with specified model and prompt version
    engine = StyleGenerationEngine(
        model=model_config['model'],
        temperature=model_config['temperature'],
        max_tokens=model_config['max_tokens'],
        prompt_version=model_config.get('prompt_version', 'baseline_v1')  # Default to baseline for backward compatibility
    )

    # Prepare parameters based on scenario type
    if scenario['scenario_type'] == 'complete_my_look':
        # Handle both single anchor (anchor_item_name) and multiple anchors (anchor_items)
        if 'anchor_items' in scenario:
            # Multiple anchor items (array)
            styling_challenges = []
            for anchor_name in scenario['anchor_items']:
                anchor_item = find_anchor_item(wardrobe, anchor_name)
                if anchor_item:
                    styling_challenges.append(anchor_item)
        elif 'anchor_item_name' in scenario:
            # Single anchor item (string)
            anchor_item = find_anchor_item(wardrobe, scenario['anchor_item_name'])
            styling_challenges = [anchor_item] if anchor_item else []
        else:
            styling_challenges = []
    else:
        styling_challenges = []

    # Generate outfits
    start_time = time.time()

    try:
        outfits = engine.generate_outfit_combinations(
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

        # Calculate cost from last AI call and extract reasoning
        cost_usd = 0.0
        tokens_used = 0
        reasoning = None
        if hasattr(engine, '_last_ai_response'):
            ai_resp = engine._last_ai_response
            cost_usd = engine.ai_provider.calculate_cost(ai_resp.usage)
            tokens_used = ai_resp.usage.get('total_tokens', 0)

            # Extract chain-of-thought reasoning if present
            raw_response = ai_resp.content
            if '===JSON OUTPUT===' in raw_response:
                reasoning = raw_response.split('===JSON OUTPUT===')[0].strip()

    except Exception as e:
        latency = time.time() - start_time
        outfits = []
        success = False
        error = str(e)
        cost_usd = 0.0
        tokens_used = 0

    return {
        "scenario_id": scenario['id'],
        "scenario_name": scenario['name'],
        "model_id": model_config['id'],
        "model_name": model_config['name'],
        "model": model_config['model'],
        "prompt_version": model_config.get('prompt_version', 'baseline_v1'),
        "iteration": iteration,
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "error": error,
        "latency_seconds": latency,
        "cost_usd": cost_usd,
        "tokens_used": tokens_used,
        "reasoning": reasoning,
        "outfits": outfits,
        "num_outfits": len(outfits) if outfits else 0
    }


def main():
    parser = argparse.ArgumentParser(description='Run outfit generation evaluation')
    parser.add_argument('--preset', default=None, help='Use named preset from eval_presets.yaml (e.g., quick-test, baseline-vs-cot)')
    parser.add_argument('--list-presets', action='store_true', help='List all available eval presets and exit')
    parser.add_argument('--scenarios', default='fixtures/test_scenarios.json', help='Path to test scenarios JSON')
    parser.add_argument('--models', default='fixtures/model_configs.yaml', help='Path to model configs YAML')
    parser.add_argument('--iterations', type=int, default=None, help='Number of iterations per scenario/model')
    parser.add_argument('--output', default=None, help='Output directory (default: results/eval_TIMESTAMP/)')
    parser.add_argument('--model-filter', default=None, help='Filter to specific model ID (e.g., gpt4o, gemini_2_flash)')
    parser.add_argument('--scenario-filter', default=None, help='Filter scenarios by name or ID substring (e.g., complete, wedding, boots)')
    parser.add_argument('--user-filter', default=None, help='Filter scenarios to specific user_id (e.g., peichin)')

    args = parser.parse_args()

    # Show presets if requested
    if args.list_presets:
        list_available_presets()
        sys.exit(0)

    # Show presets if run with no meaningful args (helpful default)
    if (args.preset is None and
        args.scenarios == 'fixtures/test_scenarios.json' and
        args.models == 'fixtures/model_configs.yaml' and
        args.iterations is None and
        args.model_filter is None):
        print("ℹ️  No preset or custom configuration specified.\n")
        list_available_presets()
        sys.exit(0)

    # Load preset if specified
    preset_config = None
    if args.preset:
        print(f"\n📦 Loading preset: {args.preset}")
        preset_config = load_preset(args.preset)
        print(f"  ℹ️  {preset_config.get('description', 'No description')}")

        # Override args with preset values (args can still override preset)
        if not args.scenarios and preset_config.get('scenarios'):
            args.scenarios = preset_config['scenarios']
        if not args.models and preset_config.get('models'):
            args.models = preset_config['models']
        if args.iterations is None and preset_config.get('iterations'):
            args.iterations = preset_config['iterations']
        if not args.model_filter and preset_config.get('model_filter'):
            args.model_filter = preset_config['model_filter']

    # Set default iterations if still not set
    if args.iterations is None:
        args.iterations = 10

    # Load configurations
    print("\n📋 Loading configurations...")
    scenarios = load_test_scenarios(args.scenarios)
    model_configs = load_model_configs(args.models)

    print(f"  ✅ Loaded {len(scenarios)} test scenarios")
    print(f"  ✅ Loaded {len(model_configs)} model configurations")

    # Apply filters from preset or command line
    model_ids = preset_config.get('model_ids') if preset_config else None
    model_configs = apply_model_filters(model_configs, args.model_filter, model_ids)
    if model_ids or args.model_filter:
        print(f"  🔍 Filtered to {len(model_configs)} models")

    # Apply scenario filters (command line overrides preset)
    scenario_filter = args.scenario_filter or (preset_config.get('scenario_filter') if preset_config else None)
    user_filter = args.user_filter or (preset_config.get('user_filter') if preset_config else None)
    scenarios = apply_scenario_filters(scenarios, scenario_filter, user_filter)
    if scenario_filter or user_filter:
        print(f"  🔍 Filtered to {len(scenarios)} scenarios")

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
                    cost_str = f", ${result['cost_usd']:.4f}" if result.get('cost_usd', 0) > 0 else ""
                    print(f"✅ ({result['latency_seconds']:.2f}s, {result['num_outfits']} outfits{cost_str})")
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
