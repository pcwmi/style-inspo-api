"""
A/B test: baseline_v1 vs physical_fit_v1

Generates outfits for 3 users × 3 occasions using both prompt versions,
then asks a judge model to score each outfit for physical layering plausibility.

Usage:
    cd backend && python -m tests.test_physical_fit_ab
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
os.environ.setdefault("STORAGE_TYPE", "s3")

from services.style_engine import StyleGenerationEngine
from services.wardrobe_manager import WardrobeManager
from services.user_profile_manager import UserProfileManager


USERS = ["peichin", "dana", "alexi"]

OCCASIONS = [
    ("casual weekend brunch", "Mild", "65-75°F"),
    ("work meeting + after-work drinks", "Cool", "50-65°F"),
    ("date night", "Cool", "50-65°F"),
]

PROMPT_VERSIONS = ["baseline_v1", "physical_fit_v1"]

# Judge prompt — scores physical plausibility of layering
JUDGE_PROMPT = """You are a fashion physics expert. Given an outfit with item metadata,
score how physically plausible the layering is on a scale of 1-5:

5 = Every layer fits naturally over the one beneath it. No bulk or fit conflicts.
4 = Minor concern but wearable (e.g., slightly snug outer layer).
3 = One noticeable issue (e.g., tucking a thick fabric, slightly tight layering).
2 = Clearly problematic (e.g., fitted cardigan over flowy blouse, structured blazer over chunky knit).
1 = Physically impossible or absurd (e.g., tight vest over oversized puffer).

For each outfit, respond with ONLY a JSON object:
{
  "score": <1-5>,
  "issues": ["brief description of each physical issue found, or empty if none"],
  "worst_transition": "which layer-over-layer transition is most problematic, or null if none"
}

Here is the outfit to evaluate:
"""


def load_user_context(user_id):
    """Load wardrobe and profile for a user."""
    wardrobe = WardrobeManager(user_id=user_id)
    profile_mgr = UserProfileManager(user_id=user_id)

    items = wardrobe.get_wardrobe_items("all")
    raw_profile = profile_mgr.get_profile(user_id)

    if not raw_profile or not raw_profile.get("style_words"):
        print(f"  ⚠️  No profile for {user_id}, using defaults")
        user_profile = {
            "three_words": {
                "current": "versatile",
                "aspirational": "confident",
                "feeling": "comfortable",
            }
        }
    else:
        words = raw_profile["style_words"]
        user_profile = {
            "three_words": {
                "current": words[0] if len(words) > 0 else "versatile",
                "aspirational": words[1] if len(words) > 1 else "confident",
                "feeling": words[2] if len(words) > 2 else "comfortable",
            }
        }

    return items, user_profile


def format_outfit_for_judge(outfit, all_items):
    """Format an outfit with full metadata for the judge."""
    lines = []
    for item in outfit.items:
        details = item.get("styling_details", {})
        name = details.get("name", "Unknown")
        fit = details.get("fit", "unknown")
        cut = details.get("cut", "unknown")
        fabric = details.get("fabric_type") or details.get("fabric") or "unknown"
        weight = details.get("fabric_weight") or details.get("weight") or "unknown"
        category = details.get("category", "unknown")
        sub_cat = details.get("sub_category", "unknown")
        texture = details.get("texture", "unknown")
        lines.append(
            f"- {name}: category={category}, sub_category={sub_cat}, "
            f"fit={fit}, cut={cut}, fabric={fabric}, weight={weight}, texture={texture}"
        )
    lines.append(f"\nStyling notes: {outfit.styling_notes}")
    return "\n".join(lines)


def judge_outfit(outfit_text):
    """Use a cheap model to judge physical plausibility."""
    from services.ai.factory import AIProviderFactory

    provider = AIProviderFactory.create(
        model="gpt-4.1-mini",
        temperature=0.0,
        max_tokens=300,
    )

    result = provider.generate_text(
        prompt=JUDGE_PROMPT + outfit_text,
        system_message="You are a fashion physics expert. Return ONLY valid JSON.",
        temperature=0.0,
        max_tokens=300,
    )

    try:
        # Extract JSON from response
        import re
        match = re.search(r'\{[\s\S]*\}', result.content)
        if match:
            return json.loads(match.group(0))
    except (json.JSONDecodeError, AttributeError):
        pass
    return {"score": 0, "issues": ["judge parse error"], "worst_transition": None}


def main():
    results = []

    for user_id in USERS:
        print(f"\n{'='*60}")
        print(f"USER: {user_id}")
        print(f"{'='*60}")

        items, user_profile = load_user_context(user_id)
        if not items:
            print(f"  ⚠️  No wardrobe items for {user_id}, skipping")
            continue

        print(f"  Wardrobe: {len(items)} items")

        for occasion, weather, temp_range in OCCASIONS:
            print(f"\n  Occasion: {occasion} ({weather}, {temp_range})")

            for version in PROMPT_VERSIONS:
                print(f"    Prompt: {version}...", end=" ", flush=True)
                start = time.time()

                engine = StyleGenerationEngine(
                    model="gpt-5.1",
                    temperature=0.7,
                    max_tokens=4000,
                    prompt_version=version,
                )

                outfits = engine.generate_outfit_combinations(
                    user_profile=user_profile,
                    available_items=items,
                    styling_challenges=[],
                    num_outfits=3,
                    occasion=occasion,
                    weather_condition=weather,
                    temperature_range=temp_range,
                    user_id=user_id,
                )

                gen_time = time.time() - start
                print(f"{len(outfits)} outfits ({gen_time:.1f}s)")

                for i, outfit in enumerate(outfits):
                    outfit_text = format_outfit_for_judge(outfit, items)
                    judgment = judge_outfit(outfit_text)

                    item_names = [
                        it.get("styling_details", {}).get("name", "?")
                        for it in outfit.items
                    ]

                    result = {
                        "user": user_id,
                        "occasion": occasion,
                        "prompt_version": version,
                        "outfit_idx": i,
                        "items": item_names,
                        "styling_notes": outfit.styling_notes,
                        "score": judgment.get("score", 0),
                        "issues": judgment.get("issues", []),
                        "worst_transition": judgment.get("worst_transition"),
                    }
                    results.append(result)

                    score = judgment.get("score", 0)
                    issues = judgment.get("issues", [])
                    issue_str = f" — {'; '.join(issues)}" if issues else ""
                    print(f"      Outfit {i+1}: score={score}/5{issue_str}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for version in PROMPT_VERSIONS:
        version_results = [r for r in results if r["prompt_version"] == version]
        if not version_results:
            continue
        scores = [r["score"] for r in version_results]
        avg = sum(scores) / len(scores) if scores else 0
        low = sum(1 for s in scores if s <= 2)
        print(f"\n  {version}:")
        print(f"    Outfits: {len(scores)}")
        print(f"    Avg score: {avg:.2f}/5")
        print(f"    Physical failures (score ≤ 2): {low} ({low/len(scores)*100:.0f}%)" if scores else "")

        # Show worst offenders
        failures = [r for r in version_results if r["score"] <= 2]
        if failures:
            print(f"    Failures:")
            for f in failures:
                print(f"      [{f['user']}] {f['occasion']}: {', '.join(f['items'][:3])}...")
                print(f"        → {f['worst_transition']}")

    # Per-user breakdown
    print(f"\n  Per-user avg scores:")
    for user_id in USERS:
        for version in PROMPT_VERSIONS:
            user_ver = [r for r in results if r["user"] == user_id and r["prompt_version"] == version]
            if user_ver:
                avg = sum(r["score"] for r in user_ver) / len(user_ver)
                print(f"    {user_id:10s} {version:20s}: {avg:.2f}/5 (n={len(user_ver)})")

    # Save full results
    out_path = os.path.join(os.path.dirname(__file__), "physical_fit_ab_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Full results saved to: {out_path}")


if __name__ == "__main__":
    main()
