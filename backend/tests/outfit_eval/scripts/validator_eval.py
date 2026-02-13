#!/usr/bin/env python3
"""
Outfit Validator Eval — Side-by-side impact assessment.

Generates outfits for multiple users, runs each through the
slot-based validator, and produces an HTML report showing what
would PASS vs get FILTERED — so we can assess whether the
filter is too aggressive before wiring it to production.

Usage:
    python tests/outfit_eval/scripts/validator_eval.py
    python tests/outfit_eval/scripts/validator_eval.py --users peichin,dana
    python tests/outfit_eval/scripts/validator_eval.py --users kate --rounds 5
"""

import os
import sys
import json
import time
import argparse
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

from services.style_engine import StyleGenerationEngine
from services.wardrobe_manager import WardrobeManager
from services.user_profile_manager import UserProfileManager
from services.outfit_validator import validate_outfit_detailed

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_USERS = ["peichin", "dana", "kate"]
DEFAULT_ROUNDS = 4  # 4 rounds × 3 outfits = 12 outfits per user

OCCASIONS = [
    "casual weekend brunch with friends",
    "important work meeting",
    "dinner date at a nice restaurant",
    "running errands on a Saturday",
]

DEFAULT_PROFILE = {
    "three_words": {
        "current": "classic",
        "aspirational": "polished",
        "feeling": "relaxed"
    }
}


def load_wardrobe(user_id: str) -> List[Dict]:
    """Load user's wardrobe from S3."""
    wm = WardrobeManager(user_id=user_id)
    items = wm.get_wardrobe_items(filter_type="all")
    logger.info(f"Loaded {len(items)} wardrobe items for {user_id}")
    return items


def load_profile(user_id: str) -> Dict:
    """Load user's style profile, or use default."""
    try:
        pm = UserProfileManager(user_id=user_id)
        profile = pm.get_profile(user_id)
        if profile and profile.get("three_words"):
            logger.info(f"Loaded profile for {user_id}")
            return profile
    except Exception as e:
        logger.warning(f"Could not load profile for {user_id}: {e}")
    logger.info(f"Using default profile for {user_id}")
    return DEFAULT_PROFILE


def enrich_outfit_items(outfit_items: List[str], wardrobe: List[Dict]) -> List[Dict]:
    """
    Match generated item names to wardrobe items with full metadata.
    Same fuzzy matching as production (substring match).
    """
    enriched = []
    for item_name in outfit_items:
        item_name_lower = item_name.lower().strip()
        matched = None

        for w_item in wardrobe:
            w_name = w_item.get("styling_details", {}).get("name", "").lower()
            if w_name and (w_name in item_name_lower or item_name_lower in w_name):
                matched = w_item
                break

        if matched:
            sd = matched.get("styling_details", {})
            image_path = (
                matched.get("system_metadata", {}).get("image_path")
                or matched.get("image_path", "")
            )
            enriched.append({
                "name": sd.get("name", item_name),
                "category": sd.get("category", "unknown"),
                "sub_category": sd.get("sub_category", ""),
                "cut": sd.get("cut", ""),
                "fit": sd.get("fit", ""),
                "image_path": image_path,
                "matched": True,
            })
        else:
            enriched.append({
                "name": item_name,
                "category": "unknown",
                "sub_category": "",
                "image_path": "",
                "matched": False,
            })

    return enriched


def generate_outfits_for_user(
    user_id: str,
    wardrobe: List[Dict],
    profile: Dict,
    num_rounds: int = 4,
) -> List[Dict]:
    """Generate outfits using the style engine and validate each."""
    engine = StyleGenerationEngine(
        model="gpt-4o",
        temperature=0.9,
        max_tokens=4096,
        prompt_version="baseline_v1",
    )

    all_results = []

    for round_idx in range(num_rounds):
        occasion = OCCASIONS[round_idx % len(OCCASIONS)]
        logger.info(f"  Round {round_idx + 1}/{num_rounds}: {occasion}")

        try:
            start = time.time()
            outfits = engine.generate_outfit_combinations(
                user_profile=profile,
                available_items=wardrobe,
                styling_challenges=[],
                occasion=occasion,
                num_outfits=3,
            )
            elapsed = time.time() - start
            logger.info(f"  Generated {len(outfits)} outfits in {elapsed:.1f}s")

            for i, outfit in enumerate(outfits):
                # Get item names from outfit
                if hasattr(outfit, 'items'):
                    # OutfitCombination object
                    raw_items = [item.get('name', str(item)) if isinstance(item, dict) else str(item) for item in outfit.items]
                    styling_notes = getattr(outfit, 'styling_notes', '')
                    why_it_works = getattr(outfit, 'why_it_works', '')
                elif isinstance(outfit, dict):
                    raw_items = outfit.get('items', [])
                    styling_notes = outfit.get('styling_notes', '')
                    why_it_works = outfit.get('why_it_works', '')
                else:
                    raw_items = [str(outfit)]
                    styling_notes = ''
                    why_it_works = ''

                # Enrich with wardrobe metadata
                enriched = enrich_outfit_items(raw_items, wardrobe)

                # Validate
                validation = validate_outfit_detailed(enriched)

                all_results.append({
                    "user_id": user_id,
                    "round": round_idx + 1,
                    "outfit_num": i + 1,
                    "occasion": occasion,
                    "raw_items": raw_items,
                    "enriched_items": enriched,
                    "styling_notes": styling_notes,
                    "why_it_works": why_it_works,
                    "validation": validation,
                })

        except Exception as e:
            logger.error(f"  Error generating outfits: {e}")
            import traceback
            traceback.print_exc()

    return all_results


def generate_html_report(all_results: List[Dict], output_path: str):
    """Generate interactive HTML report from eval results."""

    # Group by user
    by_user = {}
    for r in all_results:
        uid = r["user_id"]
        if uid not in by_user:
            by_user[uid] = []
        by_user[uid].append(r)

    # Summary stats
    total = len(all_results)
    filtered = sum(1 for r in all_results if not r["validation"]["is_valid"])
    passed = total - filtered

    # Build HTML
    html_parts = [f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Outfit Validator Eval — {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #faf9f7; color: #333; padding: 24px; }}
    h1 {{ font-size: 28px; margin-bottom: 8px; }}
    .subtitle {{ color: #666; margin-bottom: 24px; font-size: 14px; }}
    .summary {{ display: flex; gap: 16px; margin-bottom: 32px; }}
    .stat {{ background: white; border-radius: 12px; padding: 16px 24px;
             box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
    .stat .number {{ font-size: 32px; font-weight: 700; }}
    .stat .label {{ font-size: 13px; color: #888; margin-top: 4px; }}
    .stat.filtered .number {{ color: #d32f2f; }}
    .stat.passed .number {{ color: #2e7d32; }}

    .user-section {{ margin-bottom: 40px; }}
    .user-header {{ font-size: 20px; font-weight: 600; margin-bottom: 16px;
                    padding-bottom: 8px; border-bottom: 2px solid #eee; }}

    .outfit-card {{ background: white; border-radius: 12px; padding: 20px;
                    margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
    .outfit-card.filtered {{ border-left: 4px solid #d32f2f; }}
    .outfit-card.passed {{ border-left: 4px solid #2e7d32; }}

    .outfit-header {{ display: flex; justify-content: space-between; align-items: center;
                      margin-bottom: 12px; }}
    .outfit-title {{ font-weight: 600; font-size: 14px; }}
    .badge {{ padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
    .badge.pass {{ background: #e8f5e9; color: #2e7d32; }}
    .badge.fail {{ background: #ffebee; color: #d32f2f; }}
    .reason {{ color: #d32f2f; font-size: 13px; margin-bottom: 12px; font-style: italic; }}

    .items-grid {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }}
    .item-card {{ width: 120px; text-align: center; }}
    .item-card img {{ width: 120px; height: 140px; object-fit: cover;
                      border-radius: 8px; background: #f0ede8; }}
    .item-card .no-img {{ width: 120px; height: 140px; background: #f0ede8;
                          border-radius: 8px; display: flex; align-items: center;
                          justify-content: center; color: #aaa; font-size: 11px; }}
    .item-name {{ font-size: 11px; margin-top: 4px; font-weight: 500;
                  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .item-slot {{ font-size: 10px; padding: 2px 6px; border-radius: 4px;
                  display: inline-block; margin-top: 2px; }}
    .slot-base_top {{ background: #e3f2fd; color: #1565c0; }}
    .slot-mid_layer {{ background: #fff3e0; color: #e65100; }}
    .slot-outer_layer {{ background: #f3e5f5; color: #7b1fa2; }}
    .slot-bottom {{ background: #e8f5e9; color: #2e7d32; }}
    .slot-shoes {{ background: #fce4ec; color: #c62828; }}
    .slot-dress {{ background: #e8eaf6; color: #283593; }}
    .slot-accessory {{ background: #f5f5f5; color: #616161; }}
    .slot-bag {{ background: #efebe9; color: #4e342e; }}
    .slot-unassigned {{ background: #fff9c4; color: #f57f17; }}

    .styling-notes {{ font-size: 13px; color: #555; line-height: 1.5; }}
    .occasion {{ font-size: 12px; color: #888; }}

    .filter-bar {{ margin-bottom: 20px; display: flex; gap: 8px; }}
    .filter-btn {{ padding: 6px 16px; border-radius: 20px; border: 1px solid #ddd;
                   background: white; cursor: pointer; font-size: 13px; }}
    .filter-btn.active {{ background: #333; color: white; border-color: #333; }}
</style>
</head>
<body>
<h1>Outfit Validator Eval</h1>
<p class="subtitle">Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} &middot;
   {len(by_user)} users &middot; {total} outfits</p>

<div class="summary">
    <div class="stat">
        <div class="number">{total}</div>
        <div class="label">Total Outfits</div>
    </div>
    <div class="stat passed">
        <div class="number">{passed}</div>
        <div class="label">Would PASS</div>
    </div>
    <div class="stat filtered">
        <div class="number">{filtered}</div>
        <div class="label">Would be FILTERED</div>
    </div>
    <div class="stat">
        <div class="number">{filtered * 100 // total if total else 0}%</div>
        <div class="label">Filter Rate</div>
    </div>
</div>

<div class="filter-bar">
    <button class="filter-btn active" onclick="filterOutfits('all')">All ({total})</button>
    <button class="filter-btn" onclick="filterOutfits('filtered')">Filtered ({filtered})</button>
    <button class="filter-btn" onclick="filterOutfits('passed')">Passed ({passed})</button>
</div>
"""]

    for user_id, results in by_user.items():
        user_filtered = sum(1 for r in results if not r["validation"]["is_valid"])
        user_passed = len(results) - user_filtered
        html_parts.append(f"""
<div class="user-section">
<h2 class="user-header">{user_id} — {len(results)} outfits
    ({user_passed} pass, {user_filtered} filtered)</h2>
""")
        for r in results:
            v = r["validation"]
            status = "passed" if v["is_valid"] else "filtered"
            badge_cls = "pass" if v["is_valid"] else "fail"
            badge_text = "PASS" if v["is_valid"] else "FILTERED"

            html_parts.append(f"""
<div class="outfit-card {status}" data-status="{status}">
    <div class="outfit-header">
        <div>
            <span class="outfit-title">Round {r['round']} · Outfit {r['outfit_num']}</span>
            <span class="occasion"> — {r['occasion']}</span>
        </div>
        <span class="badge {badge_cls}">{badge_text}</span>
    </div>
""")
            if not v["is_valid"]:
                html_parts.append(f'    <div class="reason">{v["reason"]}</div>')

            html_parts.append('    <div class="items-grid">')
            for sa in v["slot_assignments"]:
                img_path = ""
                # Find image from enriched items
                for ei in r["enriched_items"]:
                    if ei["name"] == sa["name"]:
                        img_path = ei.get("image_path", "")
                        break

                slot_cls = f"slot-{sa['slot']}"
                img_html = (
                    f'<img src="{img_path}" alt="{sa["name"]}" loading="lazy">'
                    if img_path
                    else f'<div class="no-img">{sa["name"][:20]}</div>'
                )
                html_parts.append(f"""
        <div class="item-card">
            {img_html}
            <div class="item-name" title="{sa['name']}">{sa['name']}</div>
            <span class="item-slot {slot_cls}">{sa['slot']}</span>
        </div>""")

            html_parts.append('    </div>')

            if r.get("styling_notes"):
                notes = r["styling_notes"][:200]
                html_parts.append(f'    <div class="styling-notes">{notes}</div>')

            html_parts.append('</div>')

        html_parts.append('</div>')

    html_parts.append("""
<script>
function filterOutfits(status) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('.outfit-card').forEach(card => {
        if (status === 'all') {
            card.style.display = '';
        } else {
            card.style.display = card.dataset.status === status ? '' : 'none';
        }
    });
}
</script>
</body>
</html>""")

    html = "\n".join(html_parts)
    with open(output_path, 'w') as f:
        f.write(html)
    logger.info(f"HTML report written to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Outfit Validator Eval")
    parser.add_argument("--users", default=",".join(DEFAULT_USERS),
                        help="Comma-separated user IDs")
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS,
                        help="Generation rounds per user (each produces ~3 outfits)")
    args = parser.parse_args()

    users = [u.strip() for u in args.users.split(",")]
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    all_results = []
    for user_id in users:
        logger.info(f"\n{'='*50}")
        logger.info(f"Generating outfits for: {user_id}")
        logger.info(f"{'='*50}")

        wardrobe = load_wardrobe(user_id)
        if not wardrobe:
            logger.warning(f"No wardrobe for {user_id}, skipping")
            continue

        profile = load_profile(user_id)
        results = generate_outfits_for_user(user_id, wardrobe, profile, args.rounds)
        all_results.extend(results)

        # Per-user stats
        user_filtered = sum(1 for r in results if not r["validation"]["is_valid"])
        logger.info(f"  {user_id}: {len(results)} outfits, {user_filtered} filtered")

    # Save raw JSON results
    json_path = results_dir / f"validator_eval_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    logger.info(f"\nJSON results: {json_path}")

    # Generate HTML report
    html_path = results_dir / f"validator_eval_{timestamp}.html"
    generate_html_report(all_results, str(html_path))

    # Print summary
    total = len(all_results)
    filtered = sum(1 for r in all_results if not r["validation"]["is_valid"])
    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")
    print(f"Total outfits: {total}")
    print(f"Would PASS:    {total - filtered}")
    print(f"Would FILTER:  {filtered} ({filtered * 100 // total if total else 0}%)")
    print(f"\nHTML report: {html_path}")
    print(f"Open with: open {html_path}")


if __name__ == "__main__":
    main()
