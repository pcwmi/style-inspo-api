#!/usr/bin/env python3
"""
Run SMS agent quality evaluation across multi-turn conversations.

Simulates real SMS conversations: user messages + optional photos,
agent responses with tool calls (resolve_items, send_message),
multi-turn context accumulation.

Usage:
    cd backend/tests/sms_eval
    python scripts/run_sms_eval.py --preset quick-sms
    python scripts/run_sms_eval.py --preset full-sms-peichin
    python scripts/run_sms_eval.py --list-presets
"""

import argparse
import json
import yaml
import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
load_dotenv(backend_path / '.env')
os.environ['STORAGE_TYPE'] = 's3'

logging.basicConfig(level=logging.WARNING, format='%(levelname)s - %(message)s')
# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

from agent.agent import StylingAgent
from agent.output import MockOutput
from api.sms import preload_user_context
from services.wardrobe_manager import WardrobeManager


def load_scenarios(scenarios_path: str) -> List[Dict]:
    """Load scenario definitions from JSON file."""
    with open(scenarios_path, 'r') as f:
        return json.load(f)


def load_preset(preset_name: str) -> Dict:
    """Load named preset from YAML file."""
    presets_path = Path(__file__).parent.parent / 'fixtures' / 'sms_presets.yaml'
    with open(presets_path, 'r') as f:
        presets = yaml.safe_load(f)

    if preset_name not in presets:
        available = ', '.join(presets.keys())
        raise ValueError(f"Preset '{preset_name}' not found. Available: {available}")

    return presets[preset_name]


def list_presets():
    """Display all available presets."""
    presets_path = Path(__file__).parent.parent / 'fixtures' / 'sms_presets.yaml'
    with open(presets_path, 'r') as f:
        presets = yaml.safe_load(f)

    print("\nAvailable SMS Eval Presets:\n")
    for name, config in presets.items():
        desc = config.get('description', 'No description')
        print(f"  {name}")
        print(f"    {desc}")
        print()
    print("Usage: python scripts/run_sms_eval.py --preset <name>")


def apply_filters(scenarios: List[Dict], scenario_filter: str = None,
                  user_filter: str = None, use_case_filter: str = None) -> List[Dict]:
    """Apply filters to scenarios."""
    filtered = scenarios

    if scenario_filter:
        filtered = [s for s in filtered
                    if scenario_filter.lower() in s['name'].lower()
                    or scenario_filter.lower() in s['id'].lower()]

    if user_filter:
        filtered = [s for s in filtered if s.get('user_id') == user_filter]

    if use_case_filter:
        filtered = [s for s in filtered if s.get('use_case') == use_case_filter]

    return filtered


def resolve_photo_url(user_id: str, image_url_spec: Optional[str],
                      wardrobe_cache: Dict) -> Optional[str]:
    """
    Resolve photo URL from scenario spec.

    Handles:
    - None → None (no photo)
    - "s3://wardrobe_item:Name" → real S3 URL via fuzzy match
    - "https://..." → pass through directly
    """
    if not image_url_spec:
        return None

    if image_url_spec.startswith("s3://wardrobe_item:"):
        item_name = image_url_spec.split("s3://wardrobe_item:", 1)[1]

        if user_id not in wardrobe_cache:
            wm = WardrobeManager(user_id=user_id)
            items = wm.get_wardrobe_items(filter_type="all")
            wardrobe_cache[user_id] = items

        # Fuzzy match on item name
        for item in wardrobe_cache[user_id]:
            name = item.get("styling_details", {}).get("name", "")
            if item_name.lower() in name.lower() or name.lower() in item_name.lower():
                path = item.get("system_metadata", {}).get("image_path", "")
                if path:
                    return path

        print(f"  WARNING: Could not find wardrobe item '{item_name}' for {user_id}")
        # Fallback: return first item with an image
        for item in wardrobe_cache[user_id]:
            path = item.get("system_metadata", {}).get("image_path", "")
            if path and path.startswith("https://"):
                return path
        return None

    # Direct URL (inspiration photo, etc.)
    return image_url_spec


def run_scenario(scenario: Dict, iteration: int, wardrobe_cache: Dict) -> Dict:
    """
    Run a complete multi-turn SMS scenario.

    Mirrors production sms.py flow:
    - Fresh agent per turn
    - Accumulated messages as conversation_context (photos attached to their turns)
    """
    accumulated_messages = []
    turn_results = []
    total_start = time.time()

    # Pre-load user context once per scenario (mirrors production sms.py)
    preloaded = preload_user_context(scenario["user_id"])

    for turn_def in scenario["turns"]:
        turn_num = turn_def["turn"]

        # Resolve photo URL
        photo_url = resolve_photo_url(
            scenario["user_id"],
            turn_def.get("image_url"),
            wardrobe_cache
        )

        # Build conversation context from accumulated messages
        conversation_context = {"messages": list(accumulated_messages)} if accumulated_messages else None

        # Create fresh agent + MockOutput per turn (mirrors production)
        output = MockOutput()
        agent = StylingAgent(
            user_id=scenario["user_id"],
            provider="openai",
            output=output,
            conversation_context=conversation_context,
            preloaded_context=preloaded
        )

        # Build image args
        image_urls = [photo_url] if photo_url else None

        # Run agent — photos from prior turns are in conversation_context
        start = time.time()
        try:
            response = agent.run(
                turn_def["user_message"],
                image_urls=image_urls,
            )
            latency = time.time() - start
            success = True
            error = None
        except Exception as e:
            response = str(e)
            latency = time.time() - start
            success = False
            error = str(e)

        # Capture the ordered tool-call timeline from the agent's turn_log.
        # present_outfit / send_message / web_search / resolve_items all route
        # through _execute_tool, so tool_result entries give one ordered timeline
        # the assertion grader can reason about (e.g. "web_search before outfit").
        tool_calls = [
            {"tool": e["tool"], "args": e.get("args", {})}
            for e in agent.turn_log
            if e.get("type") == "tool_result" and e.get("tool")
        ]

        # Capture turn result (including LLM turn count and token usage)
        turn_results.append({
            "turn": turn_num,
            "user_message": turn_def["user_message"],
            "image_url": photo_url,
            "image_type": turn_def.get("image_type"),
            "agent_text_response": response,
            "output_messages": output.messages,
            "tool_calls": tool_calls,
            "latency_seconds": round(latency, 1),
            "llm_turns": len([e for e in agent.turn_log if e["type"] == "llm_response"]),
            "token_usage": {
                "input": agent.total_input_tokens,
                "output": agent.total_output_tokens,
                "cached": agent.total_cached_tokens,
            },
            "success": success,
            "error": error,
        })

        # Accumulate state for next turn
        msg = {
            "role": "user",
            "content": turn_def["user_message"],
        }
        if photo_url:
            msg["image_urls"] = [photo_url]
        accumulated_messages.append(msg)

        if response and success:
            accumulated_messages.append({
                "role": "assistant",
                "content": response,
            })

    return {
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "use_case": scenario["use_case"],
        "user_id": scenario["user_id"],
        "description": scenario.get("description", ""),
        "iteration": iteration,
        "timestamp": datetime.now().isoformat(),
        "turns": turn_results,
        "total_latency_seconds": round(time.time() - total_start, 1),
    }


def main():
    parser = argparse.ArgumentParser(description='Run SMS agent quality evaluation')
    parser.add_argument('--preset', default=None, help='Named preset from sms_presets.yaml')
    parser.add_argument('--list-presets', action='store_true', help='List available presets')
    parser.add_argument('--scenarios', default=None, help='Path to scenarios JSON')
    parser.add_argument('--iterations', type=int, default=None, help='Iterations per scenario')
    parser.add_argument('--scenario-filter', default=None, help='Filter by scenario name/ID')
    parser.add_argument('--user-filter', default=None, help='Filter by user_id')
    parser.add_argument('--use-case-filter', default=None, help='Filter by use_case')
    parser.add_argument('--output', default=None, help='Output directory')

    args = parser.parse_args()

    if args.list_presets:
        list_presets()
        sys.exit(0)

    # Load preset
    preset = None
    if args.preset:
        print(f"\nLoading preset: {args.preset}")
        preset = load_preset(args.preset)
        print(f"  {preset.get('description', '')}")

    # Resolve scenario path
    scenarios_path = args.scenarios
    if not scenarios_path:
        if preset and preset.get('scenarios'):
            scenarios_path = preset['scenarios']
        else:
            scenarios_path = str(Path(__file__).parent.parent / 'fixtures' / 'sms_scenarios.json')

    # Resolve iterations
    iterations = args.iterations
    if iterations is None:
        iterations = preset.get('iterations', 1) if preset else 1

    # Load scenarios
    print("\nLoading scenarios...")
    scenarios = load_scenarios(scenarios_path)
    print(f"  Loaded {len(scenarios)} scenarios")

    # Apply filters (CLI overrides preset)
    scenario_filter = args.scenario_filter or (preset.get('scenario_filter') if preset else None)
    user_filter = args.user_filter or (preset.get('user_filter') if preset else None)
    use_case_filter = args.use_case_filter or (preset.get('use_case_filter') if preset else None)

    scenarios = apply_filters(scenarios, scenario_filter, user_filter, use_case_filter)
    print(f"  After filters: {len(scenarios)} scenarios")

    if not scenarios:
        print("No scenarios match filters. Use --list-presets to see options.")
        sys.exit(1)

    # Output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(__file__).parent.parent / 'results' / f'sms_eval_{timestamp}'

    output_dir.mkdir(parents=True, exist_ok=True)

    # Calculate total
    total_scenarios = len(scenarios) * iterations
    total_turns = sum(len(s['turns']) for s in scenarios) * iterations
    print(f"\nPlan: {total_scenarios} scenario runs ({total_turns} total turns)")
    print(f"Est. time: ~{total_turns * 20}s ({total_turns * 20 / 60:.1f} min)")
    print(f"Output: {output_dir}\n")

    # Run
    wardrobe_cache = {}
    all_results = []
    run_count = 0

    for scenario in scenarios:
        print(f"{'=' * 70}")
        print(f"Scenario: {scenario['name']} [{scenario['use_case']}]")
        print(f"{'=' * 70}")

        for iteration in range(iterations):
            run_count += 1
            progress = (run_count / total_scenarios) * 100

            print(f"\n  Run {run_count}/{total_scenarios} [{progress:.0f}%] (iteration {iteration + 1})")

            result = run_scenario(scenario, iteration, wardrobe_cache)
            all_results.append(result)

            # Print per-turn summary
            for tr in result["turns"]:
                status = "OK" if tr["success"] else "FAIL"
                n_images = sum(len(m.get("images", [])) for m in tr["output_messages"])
                tokens = tr.get("token_usage", {})
                text_preview = (tr["agent_text_response"] or "")[:80]
                print(f"    Turn {tr['turn']}: {status} ({tr['latency_seconds']}s, {tr.get('llm_turns', '?')} LLM calls, {n_images} images)")
                print(f"      Tokens: {tokens.get('input', 0)} in ({tokens.get('cached', 0)} cached), {tokens.get('output', 0)} out")
                print(f"      Agent: {text_preview}...")

            print(f"    Total: {result['total_latency_seconds']}s")

    # Save results
    results_file = output_dir / 'raw_results.json'
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n{'=' * 70}")
    print(f"Done! {len(all_results)} scenario runs saved.")
    print(f"{'=' * 70}")
    print(f"Results: {results_file}")
    print(f"\nNext: python scripts/generate_sms_review.py --results-dir {output_dir}")


if __name__ == '__main__':
    main()
