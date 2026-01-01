"""
Streaming Prompt Comparison
===========================
Compares two prompt approaches:
- Version A (Current): All reasoning → All JSON at end
- Version B (Interleaved): Outfit 1 reasoning → JSON → Outfit 2 reasoning → JSON → ...

Metrics:
1. Time study (when is each outfit's JSON available?)
2. Constraint honoring (does any item appear in 3+ outfits?)
3. Output quality (human judges)

Run from backend directory:
    python tests/streaming_prompt_comparison.py
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from services.ai.providers.openai import OpenAIProvider
from services.ai.providers.base import AIProviderConfig
from services.wardrobe_manager import WardrobeManager


# Test scenarios (subset of eval scenarios)
TEST_SCENARIOS = [
    {
        "id": "casual_weekend",
        "name": "Casual Weekend Outing",
        "occasion": "casual coffee with friends followed by some errands",
        "style_words": {"current": "casual", "aspirational": "polished", "feeling": "chic"},
        "anchor_items": None
    },
    {
        "id": "complete_boots",
        "name": "Complete My Look: Cream Boots",
        "occasion": "casual weekend brunch",
        "style_words": {"current": "classic", "aspirational": "relaxed", "feeling": "playful"},
        "anchor_items": ["Cream knee-high block heel boots"]
    },
    {
        "id": "complete_multi",
        "name": "Complete My Look: Dress + Loafers",
        "occasion": "brunch with friends",
        "style_words": {"current": "classic", "aspirational": "relaxed", "feeling": "playful"},
        "anchor_items": ["Olive green textured long-sleeve dress", "Black Patent Leather Loafers"]
    }
]


def format_wardrobe(items: list) -> str:
    """Format wardrobe items for prompt"""
    categories = {}
    for item in items:
        details = item.get('styling_details', {})
        cat = details.get('category', 'other').upper()
        name = details.get('name', 'Unknown')
        colors = details.get('colors', [])
        color_str = ', '.join(colors) if colors else ''

        if cat not in categories:
            categories[cat] = []

        desc = f"- {name}"
        if color_str:
            desc += f" ({color_str})"
        categories[cat].append(desc)

    result = []
    for cat in ['TOPS', 'BOTTOMS', 'DRESSES', 'OUTERWEAR', 'SHOES', 'ACCESSORIES']:
        if cat in categories:
            result.append(f"{cat}:")
            result.extend(categories[cat])
            result.append("")

    for cat, items_list in categories.items():
        if cat not in ['TOPS', 'BOTTOMS', 'DRESSES', 'OUTERWEAR', 'SHOES', 'ACCESSORIES']:
            result.append(f"{cat}:")
            result.extend(items_list)
            result.append("")

    return '\n'.join(result)


def build_prompt_version_a(scenario: dict, wardrobe_text: str) -> str:
    """Version A: Current approach - all reasoning then all JSON"""
    style = scenario['style_words']
    anchor_text = ""
    anchor_requirement = "3. Anchor pieces must be DIFFERENT across all 3 outfits"

    if scenario['anchor_items']:
        items_str = ', '.join([f'"{item}"' for item in scenario['anchor_items']])
        anchor_text = f"\n**ANCHOR ITEMS (REQUIRED):** {items_str}\nThese items MUST appear in ALL 3 outfits.\n"
        anchor_requirement = f"3. ALL anchor pieces ({items_str}) MUST appear in ALL 3 outfits"

    return f"""You are a fashion editor styling for a "Best Dressed" feature.

## USER CONTEXT
Style DNA: {style['current']} + {style['aspirational']} + wants to feel {style['feeling']}
Occasion: {scenario['occasion']}
{anchor_text}
## AVAILABLE WARDROBE
{wardrobe_text}

## REQUIREMENTS
1. Create 3 outfits
2. Each outfit MUST have an unexpected element
{anchor_requirement}
4. No item can appear in more than 2 of the 3 outfits (except anchor items)
5. Each outfit must include shoes
6. Show your reasoning for each outfit

## OUTPUT FORMAT

For EACH outfit, show reasoning:

### OUTFIT [N]

**FUNCTION:** What this outfit accomplishes
**ANCHOR:** The hero piece
**SUPPORTING PIECES:** 2-4 pieces that complete the look
**UNEXPECTED ELEMENT:** Which piece breaks convention and why it works
**STORY:** "I'm someone who ___"

**FINAL ITEMS:**
- Item 1
- Item 2
- etc.

**STYLING:** Specific instructions (tucked, cuffed, etc.)

---

After ALL 3 outfits, output:
===JSON OUTPUT===

Then the JSON array:
[
  {{"items": [...], "styling_notes": "...", "why_it_works": "..."}},
  {{"items": [...], "styling_notes": "...", "why_it_works": "..."}},
  {{"items": [...], "styling_notes": "...", "why_it_works": "..."}}
]
"""


def build_prompt_version_b(scenario: dict, wardrobe_text: str) -> str:
    """Version B: Interleaved - reasoning + JSON per outfit"""
    style = scenario['style_words']
    anchor_text = ""
    anchor_requirement = "3. Anchor pieces must be DIFFERENT across all 3 outfits"

    if scenario['anchor_items']:
        items_str = ', '.join([f'"{item}"' for item in scenario['anchor_items']])
        anchor_text = f"\n**ANCHOR ITEMS (REQUIRED):** {items_str}\nThese items MUST appear in ALL 3 outfits.\n"
        anchor_requirement = f"3. ALL anchor pieces ({items_str}) MUST appear in ALL 3 outfits"

    return f"""You are a fashion editor styling for a "Best Dressed" feature.

## USER CONTEXT
Style DNA: {style['current']} + {style['aspirational']} + wants to feel {style['feeling']}
Occasion: {scenario['occasion']}
{anchor_text}
## AVAILABLE WARDROBE
{wardrobe_text}

## REQUIREMENTS
1. Create 3 outfits
2. Each outfit MUST have an unexpected element
{anchor_requirement}
4. No item can appear in more than 2 of the 3 outfits (except anchor items)
5. Each outfit must include shoes
6. Show your reasoning for each outfit

## OUTPUT FORMAT

For EACH outfit, show reasoning IMMEDIATELY FOLLOWED by that outfit's JSON.

### OUTFIT 1

**FUNCTION:** What this outfit accomplishes
**ANCHOR:** The hero piece
**SUPPORTING PIECES:** 2-4 pieces
**UNEXPECTED ELEMENT:** Which piece breaks convention
**STORY:** "I'm someone who ___"
**FINAL ITEMS:** [list items]
**STYLING:** Specific instructions

===OUTFIT 1 JSON===
{{"items": [...], "styling_notes": "...", "why_it_works": "..."}}

---

### OUTFIT 2

[reasoning...]

===OUTFIT 2 JSON===
{{"items": [...], "styling_notes": "...", "why_it_works": "..."}}

---

### OUTFIT 3

[reasoning...]

===OUTFIT 3 JSON===
{{"items": [...], "styling_notes": "...", "why_it_works": "..."}}
"""


def run_streaming_test(provider: OpenAIProvider, prompt: str, version: str):
    """Run a streaming test and collect timing data"""
    system_message = "You are a fashion editor. Show reasoning, then output valid JSON."

    start_time = time.time()
    cumulative_text = ""
    markers = {}

    for chunk in provider.generate_text_stream(prompt, system_message=system_message):
        chunk_time = time.time() - start_time
        cumulative_text += chunk

        # Detect JSON markers for timing
        if version == "A":
            if "===JSON OUTPUT===" in cumulative_text and "json_start" not in markers:
                markers["json_start"] = chunk_time
            # Detect when each outfit's items array closes in the final JSON
            if markers.get("json_start"):
                # Count complete outfit objects
                json_part = cumulative_text.split("===JSON OUTPUT===")[-1]
                outfit_count = json_part.count('"why_it_works"')
                for i in range(1, 4):
                    if outfit_count >= i and f"outfit_{i}_json_complete" not in markers:
                        markers[f"outfit_{i}_json_complete"] = chunk_time
        else:
            # Version B - detect individual JSON markers
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
        "full_response": cumulative_text
    }


def extract_outfits(response: str, version: str) -> list:
    """Extract outfit JSON from response"""
    outfits = []

    if version == "A":
        if "===JSON OUTPUT===" in response:
            json_part = response.split("===JSON OUTPUT===")[1]
            start = json_part.find('[')
            end = json_part.rfind(']') + 1
            if start >= 0 and end > start:
                try:
                    # Clean up markdown code blocks if present
                    clean_json = json_part[start:end]
                    outfits = json.loads(clean_json)
                except json.JSONDecodeError:
                    pass
    else:
        for i in range(1, 4):
            marker = f"===OUTFIT {i} JSON==="
            if marker in response:
                parts = response.split(marker)
                if len(parts) > 1:
                    json_part = parts[1]
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
                        except json.JSONDecodeError:
                            pass

    return outfits


def check_constraints(outfits: list, anchor_items: list = None) -> dict:
    """Check if constraint 'no item in 3+ outfits' is honored"""
    all_items = []
    for outfit in outfits:
        items = outfit.get('items', [])
        all_items.extend([item.lower().strip() for item in items])

    item_counts = Counter(all_items)

    # Find violations (items appearing 3+ times, excluding anchor items)
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
    """Run the full comparison"""
    print("=" * 70)
    print("STREAMING PROMPT COMPARISON")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    config = AIProviderConfig(
        model='gpt-4o',
        api_key=os.getenv('OPENAI_API_KEY'),
        temperature=0.7,
        max_tokens=4000
    )
    provider = OpenAIProvider(config)

    print("Loading wardrobe for user 'peichin'...")
    wardrobe_manager = WardrobeManager(user_id='peichin')
    wardrobe_items = wardrobe_manager.get_wardrobe_items('all')
    wardrobe_text = format_wardrobe(wardrobe_items)
    print(f"Loaded {len(wardrobe_items)} items\n")

    results = []

    for scenario in TEST_SCENARIOS:
        print(f"\n{'=' * 70}")
        print(f"SCENARIO: {scenario['name']}")
        print(f"{'=' * 70}")

        prompt_a = build_prompt_version_a(scenario, wardrobe_text)
        prompt_b = build_prompt_version_b(scenario, wardrobe_text)

        # Run Version A
        print("\nRunning Version A (All JSON at end)...")
        result_a = run_streaming_test(provider, prompt_a, "A")
        outfits_a = extract_outfits(result_a['full_response'], "A")
        constraints_a = check_constraints(outfits_a, scenario['anchor_items'])
        result_a['outfits'] = outfits_a
        result_a['constraints'] = constraints_a
        print(f"  Total time: {result_a['total_time']:.2f}s")
        print(f"  Outfits extracted: {len(outfits_a)}")
        print(f"  Constraint check: {'PASS' if constraints_a['passed'] else 'FAIL - ' + str(constraints_a['violations'])}")

        time.sleep(2)

        # Run Version B
        print("\nRunning Version B (Interleaved JSON)...")
        result_b = run_streaming_test(provider, prompt_b, "B")
        outfits_b = extract_outfits(result_b['full_response'], "B")
        constraints_b = check_constraints(outfits_b, scenario['anchor_items'])
        result_b['outfits'] = outfits_b
        result_b['constraints'] = constraints_b
        print(f"  Total time: {result_b['total_time']:.2f}s")
        print(f"  Outfits extracted: {len(outfits_b)}")
        print(f"  Constraint check: {'PASS' if constraints_b['passed'] else 'FAIL - ' + str(constraints_b['violations'])}")

        results.append({
            "scenario": scenario,
            "version_a": result_a,
            "version_b": result_b
        })

        time.sleep(2)

    # Generate report
    print("\n" + "=" * 70)
    print("COMPARISON REPORT")
    print("=" * 70)

    report = []
    report.append("# Streaming Prompt Comparison Results")
    report.append(f"Generated: {datetime.now().isoformat()}\n")

    for r in results:
        scenario = r['scenario']
        va = r['version_a']
        vb = r['version_b']

        report.append(f"\n## Scenario: {scenario['name']}")
        if scenario['anchor_items']:
            report.append(f"Anchor items: {', '.join(scenario['anchor_items'])}")
        report.append("")

        # Time comparison
        report.append("### 1. TIME STUDY (Claude judges)")
        report.append("")
        report.append("| Metric | Version A | Version B | Winner |")
        report.append("|--------|-----------|-----------|--------|")

        total_a = va['total_time']
        total_b = vb['total_time']
        winner_total = "A" if total_a < total_b else "B" if total_b < total_a else "Tie"
        report.append(f"| Total time | {total_a:.2f}s | {total_b:.2f}s | {winner_total} |")

        # First outfit available
        first_a = va['markers'].get('outfit_1_json_complete', va['markers'].get('json_start', total_a))
        first_b = vb['markers'].get('outfit_1_json_start', total_b)
        winner_first = "A" if first_a < first_b else "B" if first_b < first_a else "Tie"
        report.append(f"| First outfit JSON | {first_a:.2f}s | {first_b:.2f}s | **{winner_first}** |")

        report.append("")

        # Constraint check
        report.append("### 2. CONSTRAINT HONORING (Claude judges)")
        report.append("")
        report.append("Constraint: No item in more than 2 outfits (except anchors)")
        report.append("")
        report.append(f"- **Version A:** {'PASS' if va['constraints']['passed'] else 'FAIL'}")
        if not va['constraints']['passed']:
            report.append(f"  - Violations: {va['constraints']['violations']}")
        report.append(f"- **Version B:** {'PASS' if vb['constraints']['passed'] else 'FAIL'}")
        if not vb['constraints']['passed']:
            report.append(f"  - Violations: {vb['constraints']['violations']}")
        report.append("")

        # Outfits for quality comparison
        report.append("### 3. OUTPUT QUALITY (User judges)")
        report.append("")

        report.append("#### Version A Outfits:")
        for i, outfit in enumerate(va['outfits'], 1):
            report.append(f"\n**Outfit {i}:**")
            report.append(f"- Items: {outfit.get('items', [])}")
            report.append(f"- Styling: {outfit.get('styling_notes', 'N/A')}")
            report.append(f"- Why it works: {outfit.get('why_it_works', 'N/A')}")

        report.append("")
        report.append("#### Version B Outfits:")
        for i, outfit in enumerate(vb['outfits'], 1):
            report.append(f"\n**Outfit {i}:**")
            report.append(f"- Items: {outfit.get('items', [])}")
            report.append(f"- Styling: {outfit.get('styling_notes', 'N/A')}")
            report.append(f"- Why it works: {outfit.get('why_it_works', 'N/A')}")

        report.append("\n---\n")

    report_text = '\n'.join(report)

    # Save report
    output_dir = Path(__file__).parent / "streaming_comparison_results"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    report_path = output_dir / f"comparison_report_{timestamp}.md"
    with open(report_path, 'w') as f:
        f.write(report_text)

    # Save raw data
    with open(output_dir / f"comparison_raw_{timestamp}.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(report_text)
    print(f"\nSaved to: {report_path}")

    return results


if __name__ == "__main__":
    run_comparison()
