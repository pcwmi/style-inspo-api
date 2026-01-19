#!/usr/bin/env python3
"""
Daily Usage Digest for Style Inspo

Generates a daily briefing showing:
- Who used the app
- What they did (generated outfits)
- Which outfits they saved/disliked
- Drop-off signals

Data sources:
- S3: Generation logs ({user}/generations/{date}.json)
- S3: Saved outfits ({user}/saved_outfits.json)
- PostHog: Events for enhanced data (optional)

Usage:
    python scripts/daily_digest.py              # Yesterday's digest
    python scripts/daily_digest.py 2026-01-18   # Specific date
    python scripts/daily_digest.py --users      # List all users with data
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.storage_manager import StorageManager
from services.posthog_client import PostHogClient


def get_all_users_with_data() -> List[str]:
    """Get list of all users who have data in S3."""
    # Known users - could also scan S3 for user directories
    known_users = ['peichin', 'heather', 'dimple', 'alexi', 'mia']
    users_with_data = []

    for user in known_users:
        try:
            storage = StorageManager(storage_type="s3", user_id=user)
            # Check if user has wardrobe data
            wardrobe = storage.load_json("wardrobe_metadata.json")
            if wardrobe.get("items"):
                users_with_data.append(user)
        except Exception:
            continue

    return users_with_data


def load_generations_for_date(user_id: str, date_str: str) -> List[Dict]:
    """Load generation logs for a specific user and date."""
    try:
        storage = StorageManager(storage_type="s3", user_id=user_id)
        log_filename = f"generations/{date_str}.json"
        data = storage.load_json(log_filename)
        return data.get("generations", [])
    except Exception as e:
        return []


def load_saved_outfits(user_id: str) -> List[Dict]:
    """Load saved outfits for a user."""
    try:
        storage = StorageManager(storage_type="s3", user_id=user_id)
        data = storage.load_json("saved_outfits.json")
        return data.get("saved", [])
    except Exception:
        return []


def format_time(timestamp_str: str) -> str:
    """Format ISO timestamp to readable time."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%I:%M %p").lstrip('0')
    except Exception:
        return timestamp_str


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse ISO timestamp string to datetime."""
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except Exception:
        return None


def outfit_items_match(gen_items: List[Dict], saved_items: List[Dict]) -> bool:
    """
    Check if generated outfit items match saved outfit items.
    Uses fuzzy matching on item names.
    """
    if not gen_items or not saved_items:
        return False

    # Get names from both lists
    gen_names = set(
        item.get("name", "").lower()
        for item in gen_items
        if item.get("name")
    )
    saved_names = set(
        item.get("name", "").lower()
        for item in saved_items
        if item.get("name")
    )

    if not gen_names or not saved_names:
        return False

    # Match if at least 2 items match (or all items if less than 2)
    matches = gen_names & saved_names
    min_matches = min(2, len(gen_names), len(saved_names))
    return len(matches) >= min_matches


def format_outfit_items(items: List[Dict], max_items: int = 4) -> str:
    """Format outfit items as a short string."""
    names = []
    for item in items[:max_items]:
        name = item.get("name", "Unknown")
        # Shorten long names
        if len(name) > 30:
            name = name[:27] + "..."
        names.append(name)

    if len(items) > max_items:
        names.append(f"+{len(items) - max_items} more")

    return " + ".join(names)


def format_outfit_with_images(items: List[Dict], indent: str = "             ") -> List[str]:
    """Format outfit items with image links."""
    lines = []
    for item in items:
        name = item.get("name", "Unknown")
        image_path = item.get("image_path", "")
        if image_path:
            lines.append(f"{indent}• {name}")
            lines.append(f"{indent}  {image_path}")
        else:
            lines.append(f"{indent}• {name}")
    return lines


def generate_user_digest(
    user_id: str,
    generations: List[Dict],
    saved_outfits: List[Dict],
    date_str: str
) -> str:
    """Generate digest section for a single user."""
    output = []

    # Header
    output.append(f"\n{'═' * 60}")
    output.append(f"{user_id.upper()}")
    output.append(f"{'═' * 60}\n")

    if not generations:
        output.append("   No outfit generations on this day.\n")
        return "\n".join(output)

    # Build saved outfit lookup indexed by timestamp
    # Only include saves from this date
    saves_today = [
        saved for saved in saved_outfits
        if date_str in saved.get("saved_at", "")
    ]

    total_outfits = 0
    total_saved = 0
    used_save_ids = set()  # Track which saves we've matched

    for gen in generations:
        gen_timestamp_str = gen.get("timestamp", "")
        gen_timestamp = parse_timestamp(gen_timestamp_str)
        mode = gen.get("mode", "unknown")
        outfits = gen.get("outfits", [])
        total_outfits += len(outfits)

        # Format header based on mode
        time_str = format_time(gen_timestamp_str)
        if mode == "occasion":
            occasion = gen.get("occasion", "Not specified")
            output.append(f"📍 {time_str} - Started \"Plan my day\"")
            output.append(f"   Occasion: \"{occasion}\"")
        else:  # complete mode
            anchor_names = gen.get("anchor_item_names", [])
            output.append(f"📍 {time_str} - Started \"Complete my look\"")
            if anchor_names:
                output.append("   Anchor items:")
                for name in anchor_names:
                    output.append(f"   • {name}")

        output.append(f"\n   → Generated {len(outfits)} outfits\n")

        # Show each outfit
        for i, outfit in enumerate(outfits, 1):
            items = outfit.get("items", [])
            items_str = format_outfit_items(items)

            # Check if this outfit was saved
            # Requirements: items match AND save happened after generation
            was_saved = False
            save_feedback = None
            save_id = None

            for saved in saves_today:
                if saved.get("id") in used_save_ids:
                    continue  # Already matched

                saved_items = saved.get("outfit_data", {}).get("items", [])
                saved_timestamp = parse_timestamp(saved.get("saved_at", ""))

                # Match: items match AND save is after generation
                if gen_timestamp and saved_timestamp:
                    if saved_timestamp >= gen_timestamp:
                        if outfit_items_match(items, saved_items):
                            was_saved = True
                            save_feedback = saved.get("user_reason")
                            save_id = saved.get("id")
                            total_saved += 1
                            used_save_ids.add(save_id)
                            break

            output.append(f"   Outfit {i}:")
            # Show item names with image links
            output.extend(format_outfit_with_images(items, indent="      "))

            if was_saved:
                # Include link to saved outfits page
                saved_url = f"https://styleinspo.vercel.app/saved?user={user_id}"
                if save_feedback:
                    output.append(f"      ✅ SAVED - \"{save_feedback}\"")
                else:
                    output.append(f"      ✅ SAVED")
                output.append(f"      🔗 {saved_url}")
            else:
                output.append(f"      ❌ Not saved")

            output.append("")

    # Add drop-off signal if no outfits saved
    if total_outfits > 0 and total_saved == 0:
        output.append("   ⚠️ DROP-OFF: Left without saving any outfits\n")

    output.append(f"{'─' * 60}\n")

    return "\n".join(output)


def generate_daily_digest(date_str: str, exclude_users: List[str] = None) -> str:
    """Generate the full daily digest."""
    output = []

    # Header
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%b %d, %Y")
    except Exception:
        formatted_date = date_str

    output.append(f"\n📊 Style Inspo Daily Digest - {formatted_date}")
    output.append("━" * 60)

    # Get all users
    all_users = get_all_users_with_data()
    exclude_users = exclude_users or []

    # Filter and collect data
    active_users = []
    user_data = {}

    for user_id in all_users:
        if user_id in exclude_users:
            continue

        generations = load_generations_for_date(user_id, date_str)
        if generations:
            active_users.append(user_id)
            saved_outfits = load_saved_outfits(user_id)
            user_data[user_id] = {
                "generations": generations,
                "saved_outfits": saved_outfits
            }

    # Summary header
    output.append(f"\n👥 ACTIVE USERS: {len(active_users)}")
    if exclude_users:
        output.append(f"   (excluding: {', '.join(exclude_users)})")

    if not active_users:
        output.append("\n   No outfit generations recorded for this day.")
        output.append("")
        return "\n".join(output)

    # Generate per-user sections
    for user_id in active_users:
        data = user_data[user_id]
        user_section = generate_user_digest(
            user_id,
            data["generations"],
            data["saved_outfits"],
            date_str
        )
        output.append(user_section)

    # Daily summary stats
    total_generations = sum(
        len(data["generations"])
        for data in user_data.values()
    )
    total_outfits = sum(
        sum(len(gen.get("outfits", [])) for gen in data["generations"])
        for data in user_data.values()
    )

    # Count saves that match generated outfits (same logic as detail view)
    total_saves = 0
    for user_id, data in user_data.items():
        saves_today = [
            saved for saved in data["saved_outfits"]
            if date_str in saved.get("saved_at", "")
        ]
        used_save_ids = set()

        for gen in data["generations"]:
            gen_timestamp = parse_timestamp(gen.get("timestamp", ""))
            for outfit in gen.get("outfits", []):
                items = outfit.get("items", [])

                for saved in saves_today:
                    if saved.get("id") in used_save_ids:
                        continue
                    saved_items = saved.get("outfit_data", {}).get("items", [])
                    saved_timestamp = parse_timestamp(saved.get("saved_at", ""))

                    if gen_timestamp and saved_timestamp:
                        if saved_timestamp >= gen_timestamp:
                            if outfit_items_match(items, saved_items):
                                total_saves += 1
                                used_save_ids.add(saved.get("id"))
                                break

    save_rate = (total_saves / total_outfits * 100) if total_outfits > 0 else 0

    output.append(f"\n📈 DAILY SUMMARY")
    output.append(f"• Active users: {len(active_users)}")
    output.append(f"• Generation sessions: {total_generations}")
    output.append(f"• Total outfits generated: {total_outfits}")
    output.append(f"• Outfits saved: {total_saves}")
    output.append(f"• Save rate: {save_rate:.0f}%")
    output.append("")

    return "\n".join(output)


def generate_compact_digest(date_str: str, exclude_users: List[str] = None) -> str:
    """Generate a compact daily digest with visible URLs (~40 lines max)."""
    output = []

    # Header
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%b %d, %Y")
    except Exception:
        formatted_date = date_str

    output.append(f"📊 Style Inspo Daily Digest - {formatted_date}")
    output.append("")

    # Get all users
    all_users = get_all_users_with_data()
    exclude_users = exclude_users or []

    # Filter and collect data
    active_users = []
    user_data = {}

    for user_id in all_users:
        if user_id in exclude_users:
            continue

        generations = load_generations_for_date(user_id, date_str)
        if generations:
            active_users.append(user_id)
            saved_outfits = load_saved_outfits(user_id)
            user_data[user_id] = {
                "generations": generations,
                "saved_outfits": saved_outfits
            }

    output.append(f"👥 Active Users: {len(active_users)}")
    if exclude_users:
        output.append(f"   (excluding: {', '.join(exclude_users)})")
    output.append("")

    if not active_users:
        output.append("No outfit generations recorded for this day.")
        return "\n".join(output)

    # Generate compact per-user sections
    total_outfits = 0
    total_saves = 0

    for user_id in active_users:
        data = user_data[user_id]
        generations = data["generations"]
        saved_outfits = data["saved_outfits"]

        # Build saved outfit lookup for this date
        saves_today = [
            saved for saved in saved_outfits
            if date_str in saved.get("saved_at", "")
        ]

        user_saves = 0
        user_outfits = 0
        used_save_ids = set()

        # Count sessions and check for drop-off
        for gen in generations:
            gen_timestamp = parse_timestamp(gen.get("timestamp", ""))
            outfits = gen.get("outfits", [])
            user_outfits += len(outfits)

            for outfit in outfits:
                items = outfit.get("items", [])
                for saved in saves_today:
                    if saved.get("id") in used_save_ids:
                        continue
                    saved_items = saved.get("outfit_data", {}).get("items", [])
                    saved_timestamp = parse_timestamp(saved.get("saved_at", ""))
                    if gen_timestamp and saved_timestamp:
                        if saved_timestamp >= gen_timestamp:
                            if outfit_items_match(items, saved_items):
                                user_saves += 1
                                used_save_ids.add(saved.get("id"))
                                break

        total_outfits += user_outfits
        total_saves += user_saves

        # User header with drop-off indicator
        drop_off = " ⚠️ drop-off" if user_saves == 0 and user_outfits > 0 else ""
        output.append(f"{user_id.upper()} - {len(generations)} session(s), {user_saves} saved{drop_off}")

        # Show each session compactly
        used_save_ids = set()  # Reset for detail output
        for gen in generations:
            gen_timestamp_str = gen.get("timestamp", "")
            gen_timestamp = parse_timestamp(gen_timestamp_str)
            time_str = format_time(gen_timestamp_str)
            mode = gen.get("mode", "unknown")
            outfits = gen.get("outfits", [])

            if mode == "occasion":
                occasion = gen.get("occasion", "Not specified")
                output.append(f"  {time_str} \"{occasion}\" → {len(outfits)} outfits")
            else:
                anchor_names = gen.get("anchor_item_names", [])
                anchor_str = ", ".join(anchor_names[:2]) if anchor_names else "items"
                output.append(f"  {time_str} Complete look ({anchor_str}) → {len(outfits)} outfits")

            # Show each outfit with first item's image URL
            for i, outfit in enumerate(outfits, 1):
                items = outfit.get("items", [])
                first_item = items[0] if items else {}
                first_name = first_item.get("name", "Unknown")[:30]
                image_url = first_item.get("image_path", "")

                # Check if saved
                was_saved = False
                save_feedback = None
                for saved in saves_today:
                    if saved.get("id") in used_save_ids:
                        continue
                    saved_items = saved.get("outfit_data", {}).get("items", [])
                    saved_timestamp = parse_timestamp(saved.get("saved_at", ""))
                    if gen_timestamp and saved_timestamp:
                        if saved_timestamp >= gen_timestamp:
                            if outfit_items_match(items, saved_items):
                                was_saved = True
                                save_feedback = saved.get("user_reason", "")
                                used_save_ids.add(saved.get("id"))
                                break

                if was_saved:
                    feedback_str = f' "{save_feedback}"' if save_feedback else ""
                    output.append(f"    ✅ Outfit {i} SAVED{feedback_str}: {first_name}")
                else:
                    output.append(f"    ❌ Outfit {i}: {first_name}")

                # Always show the image URL
                if image_url:
                    output.append(f"       {image_url}")

        output.append("")

    # Summary
    save_rate = (total_saves / total_outfits * 100) if total_outfits > 0 else 0
    output.append(f"📈 Summary: {total_outfits} generated, {total_saves} saved ({save_rate:.0f}%)")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Generate daily usage digest for Style Inspo"
    )
    parser.add_argument(
        "date",
        nargs="?",
        help="Date in YYYY-MM-DD format (default: yesterday)"
    )
    parser.add_argument(
        "--users",
        action="store_true",
        help="List all users with data"
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=["peichin"],
        help="Users to exclude (default: peichin)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show full details (default is compact mode)"
    )

    args = parser.parse_args()

    # Load environment variables from .env
    from dotenv import load_dotenv
    load_dotenv()

    if args.users:
        users = get_all_users_with_data()
        print(f"\nUsers with data: {', '.join(users)}")
        return

    # Determine date
    if args.date:
        date_str = args.date
    else:
        # Default to yesterday
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        date_str = yesterday.strftime("%Y-%m-%d")

    # Generate digest (compact by default, verbose with -v)
    if args.verbose:
        digest = generate_daily_digest(date_str, exclude_users=args.exclude)
    else:
        digest = generate_compact_digest(date_str, exclude_users=args.exclude)
    print(digest)


if __name__ == "__main__":
    main()
