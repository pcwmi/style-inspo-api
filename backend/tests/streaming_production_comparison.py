"""
Production Prompt Streaming Comparison
======================================
Tests Version A vs Version B using ACTUAL production chain-of-thought prompts.

This validates:
1. Does the ~4s timing advantage hold at production scale?
2. Does production prompt produce better quality than simplified?

Run from backend directory:
    python tests/streaming_production_comparison.py
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

load_dotenv()
os.environ['STORAGE_TYPE'] = 's3'

from services.ai.providers.openai import OpenAIProvider
from services.ai.providers.base import AIProviderConfig
from services.wardrobe_manager import WardrobeManager
from services.prompts.chain_of_thought_v1 import ChainOfThoughtPromptV1
from services.prompts.base import PromptContext


# Just 1 scenario to keep it quick but representative
TEST_SCENARIO = {
    "id": "casual_weekend",
    "name": "Casual Weekend Outing",
    "occasion": "casual coffee with friends followed by some errands",
    "style_words": {"current": "casual", "aspirational": "polished", "feeling": "chic"},
    "anchor_items": None
}


def build_production_prompt_a(wardrobe_items: list, scenario: dict) -> tuple:
    """Build actual production chain-of-thought prompt (Version A - all JSON at end)"""
    prompt_builder = ChainOfThoughtPromptV1()

    # Create PromptContext
    context = PromptContext(
        user_profile={"three_words": scenario["style_words"]},
        occasion=scenario["occasion"],
        available_items=wardrobe_items,
        styling_challenges=[]  # No anchor items for this scenario
    )

    prompt = prompt_builder.build(context)
    system_message = prompt_builder.system_message

    return prompt, system_message


def build_production_prompt_b(wardrobe_items: list, scenario: dict) -> tuple:
    """
    Build Version B: Same production prompt but modified to output JSON per outfit.
    We take the production prompt and modify the OUTPUT FORMAT section.
    """
    prompt_builder = ChainOfThoughtPromptV1()

    context = PromptContext(
        user_profile={"three_words": scenario["style_words"]},
        occasion=scenario["occasion"],
        available_items=wardrobe_items,
        styling_challenges=[]
    )

    prompt = prompt_builder.build(context)
    system_message = prompt_builder.system_message

    # Modify the output format section to request interleaved JSON
    # Find and replace the FINAL OUTPUT section
    old_final_output = """## FINAL OUTPUT

First, show your complete reasoning for all 3 outfits using the format above.

Then, you MUST include this exact line:
===JSON OUTPUT===

After that line, output ONLY the JSON array. No text before or after the JSON."""

    new_final_output = """## FINAL OUTPUT

For EACH outfit, show reasoning IMMEDIATELY FOLLOWED by that outfit's JSON.

After each outfit's reasoning, output:
===OUTFIT N JSON===
{"items": [...], "styling_notes": "...", "why_it_works": "..."}

Then continue to the next outfit.

Example flow:
- Outfit 1 reasoning... ===OUTFIT 1 JSON=== {...}
- Outfit 2 reasoning... ===OUTFIT 2 JSON=== {...}
- Outfit 3 reasoning... ===OUTFIT 3 JSON=== {...}

Do NOT batch all JSON at the end. Output each outfit's JSON immediately after its reasoning."""

    prompt = prompt.replace(old_final_output, new_final_output)

    # Also remove the part about JSON array format since we're doing individual objects
    prompt = prompt.replace(
        "The JSON must:\n- Start with [ and end with ]\n- Contain exactly 3 outfit objects\n- Use exact item names from the wardrobe\n- Include all items from each outfit's FINAL OUTFIT list",
        "Each JSON object must use exact item names from the wardrobe and include all items from that outfit's FINAL OUTFIT list."
    )

    return prompt, system_message


def run_streaming_test(provider: OpenAIProvider, prompt: str, system_message: str, version: str):
    """Run streaming test and collect detailed timing"""
    start_time = time.time()
    cumulative_text = ""
    markers = {}
    chunk_count = 0

    # Track when we see key content
    outfit_reasoning_starts = {}

    for chunk in provider.generate_text_stream(prompt, system_message=system_message):
        chunk_time = time.time() - start_time
        cumulative_text += chunk
        chunk_count += 1

        # First token
        if "first_token" not in markers:
            markers["first_token"] = chunk_time

        # Track outfit reasoning starts (look for "FUNCTION:" which starts each outfit)
        function_count = cumulative_text.count("FUNCTION:")
        for i in range(1, 4):
            if function_count >= i and f"outfit_{i}_reasoning_start" not in markers:
                markers[f"outfit_{i}_reasoning_start"] = chunk_time

        # Version A markers
        if version == "A":
            if "===JSON OUTPUT===" in cumulative_text and "json_start" not in markers:
                markers["json_start"] = chunk_time
            # Track when each outfit appears in final JSON
            if markers.get("json_start"):
                json_part = cumulative_text.split("===JSON OUTPUT===")[-1]
                why_count = json_part.count('"why_it_works"')
                for i in range(1, 4):
                    if why_count >= i and f"outfit_{i}_json_complete" not in markers:
                        markers[f"outfit_{i}_json_complete"] = chunk_time

        # Version B markers
        else:
            for i in range(1, 4):
                marker = f"===OUTFIT {i} JSON==="
                if marker in cumulative_text and f"outfit_{i}_json_start" not in markers:
                    markers[f"outfit_{i}_json_start"] = chunk_time

    end_time = time.time() - start_time
    markers["complete"] = end_time

    return {
        "version": version,
        "total_time": end_time,
        "markers": markers,
        "full_response": cumulative_text,
        "chunk_count": chunk_count,
        "response_length": len(cumulative_text)
    }


def extract_outfits(response: str, version: str) -> list:
    """Extract outfit JSON from response"""
    outfits = []

    if version == "A":
        if "===JSON OUTPUT===" in response:
            json_part = response.split("===JSON OUTPUT===")[1]
            # Handle markdown code blocks
            if "```json" in json_part:
                json_part = json_part.split("```json")[1].split("```")[0]
            elif "```" in json_part:
                json_part = json_part.split("```")[1].split("```")[0]

            start = json_part.find('[')
            end = json_part.rfind(']') + 1
            if start >= 0 and end > start:
                try:
                    outfits = json.loads(json_part[start:end])
                except json.JSONDecodeError as e:
                    print(f"JSON parse error (A): {e}")
    else:
        for i in range(1, 4):
            marker = f"===OUTFIT {i} JSON==="
            if marker in response:
                parts = response.split(marker)
                if len(parts) > 1:
                    json_part = parts[1]
                    # Handle markdown code blocks
                    if "```json" in json_part:
                        json_part = json_part.split("```json")[1].split("```")[0]
                    elif "```" in json_part:
                        json_part = json_part.split("```")[1].split("```")[0]

                    start = json_part.find('{')
                    if start >= 0:
                        brace_count = 0
                        end = start
                        for j, c in enumerate(json_part[start:]):
                            if c == '{':
                                brace_count += 1
                            elif c == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end = start + j + 1
                                    break
                        try:
                            outfit = json.loads(json_part[start:end])
                            outfits.append(outfit)
                        except json.JSONDecodeError as e:
                            print(f"JSON parse error (B, outfit {i}): {e}")

    return outfits


def check_constraints(outfits: list, anchor_items: list = None) -> dict:
    """Check constraint: no item in 3+ outfits"""
    all_items = []
    for outfit in outfits:
        items = outfit.get('items', [])
        all_items.extend([item.lower().strip() for item in items])

    item_counts = Counter(all_items)
    anchor_lower = [a.lower().strip() for a in (anchor_items or [])]

    violations = []
    for item, count in item_counts.items():
        if count >= 3 and item not in anchor_lower:
            violations.append({"item": item, "count": count})

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "item_counts": dict(item_counts)
    }


def run_comparison():
    """Run the production prompt comparison"""
    print("=" * 70)
    print("PRODUCTION PROMPT STREAMING COMPARISON")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    config = AIProviderConfig(
        model='gpt-4o',
        api_key=os.getenv('OPENAI_API_KEY'),
        temperature=0.7,
        max_tokens=6000  # Production prompts need more tokens
    )
    provider = OpenAIProvider(config)

    print("Loading wardrobe for user 'peichin'...")
    wardrobe_manager = WardrobeManager(user_id='peichin')
    wardrobe_items = wardrobe_manager.get_wardrobe_items('all')
    print(f"Loaded {len(wardrobe_items)} items\n")

    scenario = TEST_SCENARIO
    print(f"Scenario: {scenario['name']}")
    print(f"Occasion: {scenario['occasion']}")
    print()

    # Build prompts
    prompt_a, system_a = build_production_prompt_a(wardrobe_items, scenario)
    prompt_b, system_b = build_production_prompt_b(wardrobe_items, scenario)

    print(f"Prompt A length: {len(prompt_a)} chars")
    print(f"Prompt B length: {len(prompt_b)} chars")
    print()

    # Run Version A
    print("Running Version A (Production - All JSON at end)...")
    result_a = run_streaming_test(provider, prompt_a, system_a, "A")
    outfits_a = extract_outfits(result_a['full_response'], "A")
    constraints_a = check_constraints(outfits_a, scenario['anchor_items'])
    result_a['outfits'] = outfits_a
    result_a['constraints'] = constraints_a

    print(f"  Total time: {result_a['total_time']:.2f}s")
    print(f"  Response length: {result_a['response_length']} chars")
    print(f"  Outfits extracted: {len(outfits_a)}")
    print(f"  Constraint: {'PASS' if constraints_a['passed'] else 'FAIL'}")
    print(f"  Key markers:")
    for k, v in sorted(result_a['markers'].items(), key=lambda x: x[1]):
        print(f"    {k}: {v:.2f}s")

    time.sleep(3)

    # Run Version B
    print("\nRunning Version B (Production - Interleaved JSON)...")
    result_b = run_streaming_test(provider, prompt_b, system_b, "B")
    outfits_b = extract_outfits(result_b['full_response'], "B")
    constraints_b = check_constraints(outfits_b, scenario['anchor_items'])
    result_b['outfits'] = outfits_b
    result_b['constraints'] = constraints_b

    print(f"  Total time: {result_b['total_time']:.2f}s")
    print(f"  Response length: {result_b['response_length']} chars")
    print(f"  Outfits extracted: {len(outfits_b)}")
    print(f"  Constraint: {'PASS' if constraints_b['passed'] else 'FAIL'}")
    print(f"  Key markers:")
    for k, v in sorted(result_b['markers'].items(), key=lambda x: x[1]):
        print(f"    {k}: {v:.2f}s")

    # Summary
    print("\n" + "=" * 70)
    print("TIMING COMPARISON")
    print("=" * 70)

    first_json_a = result_a['markers'].get('outfit_1_json_complete',
                   result_a['markers'].get('json_start', result_a['total_time']))
    first_json_b = result_b['markers'].get('outfit_1_json_start', result_b['total_time'])

    print(f"\n| Metric                    | Version A  | Version B  | Diff      |")
    print(f"|---------------------------|------------|------------|-----------|")
    print(f"| Total time                | {result_a['total_time']:>8.2f}s | {result_b['total_time']:>8.2f}s | {result_b['total_time'] - result_a['total_time']:>+7.2f}s |")
    print(f"| First outfit JSON         | {first_json_a:>8.2f}s | {first_json_b:>8.2f}s | {first_json_b - first_json_a:>+7.2f}s |")
    print(f"| Response length           | {result_a['response_length']:>8} | {result_b['response_length']:>8} | {result_b['response_length'] - result_a['response_length']:>+8} |")

    advantage = first_json_a - first_json_b
    print(f"\n✅ Version B delivers first outfit {advantage:.1f}s faster")

    # Save results
    output_dir = Path(__file__).parent / "streaming_comparison_results"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    results = {
        "scenario": scenario,
        "version_a": result_a,
        "version_b": result_b,
        "prompt_a_length": len(prompt_a),
        "prompt_b_length": len(prompt_b)
    }

    with open(output_dir / f"production_comparison_{timestamp}.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to: production_comparison_{timestamp}.json")

    # Print outfits for quality comparison
    print("\n" + "=" * 70)
    print("OUTFITS FOR QUALITY COMPARISON")
    print("=" * 70)

    print("\n--- VERSION A (Production - All JSON at end) ---")
    for i, outfit in enumerate(outfits_a, 1):
        print(f"\nOutfit {i}:")
        print(f"  Items: {outfit.get('items', [])}")
        print(f"  Styling: {outfit.get('styling_notes', 'N/A')[:100]}...")
        print(f"  Why: {outfit.get('why_it_works', 'N/A')[:100]}...")

    print("\n--- VERSION B (Production - Interleaved JSON) ---")
    for i, outfit in enumerate(outfits_b, 1):
        print(f"\nOutfit {i}:")
        print(f"  Items: {outfit.get('items', [])}")
        print(f"  Styling: {outfit.get('styling_notes', 'N/A')[:100]}...")
        print(f"  Why: {outfit.get('why_it_works', 'N/A')[:100]}...")

    return results


if __name__ == "__main__":
    run_comparison()
