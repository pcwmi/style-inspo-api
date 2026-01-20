#!/usr/bin/env python3
"""
Generate HTML Daily Digest for Style Inspo

Creates a visual HTML file showing all outfit generations for a day,
replicating the OutfitCard pattern from the frontend.

Usage:
    python scripts/generate_digest_html.py              # Yesterday
    python scripts/generate_digest_html.py 2026-01-19   # Specific date
    python scripts/generate_digest_html.py --no-open    # Don't auto-open browser
"""

import os
import sys
import argparse
import webbrowser
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from services.storage_manager import StorageManager


def get_all_users_with_data() -> List[str]:
    """Get list of all users who have data in S3."""
    known_users = ['peichin', 'heather', 'dimple', 'alexi', 'mia']
    users_with_data = []
    for user in known_users:
        try:
            storage = StorageManager(storage_type="s3", user_id=user)
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
    except Exception:
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
    """Check if generated outfit items match saved outfit items."""
    if not gen_items or not saved_items:
        return False
    gen_names = set(item.get("name", "").lower() for item in gen_items if item.get("name"))
    saved_names = set(item.get("name", "").lower() for item in saved_items if item.get("name"))
    if not gen_names or not saved_names:
        return False
    matches = gen_names & saved_names
    min_matches = min(2, len(gen_names), len(saved_names))
    return len(matches) >= min_matches


def generate_html(date_str: str, exclude_users: List[str] = None) -> str:
    """Generate the HTML digest."""
    exclude_users = exclude_users or []

    # Collect data
    all_users = get_all_users_with_data()
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

    # Calculate stats
    total_outfits = sum(
        sum(len(gen.get("outfits", [])) for gen in data["generations"])
        for data in user_data.values()
    )
    total_saves = 0

    # Format date
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%b %d, %Y")
    except Exception:
        formatted_date = date_str

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Style Inspo Daily Digest - {formatted_date}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #FAF8F5;
            margin: 0;
            padding: 20px;
            color: #1A1614;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        h1 {{
            font-size: 24px;
            margin-bottom: 8px;
        }}
        .summary {{
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }}
        .user-section {{
            margin-bottom: 40px;
        }}
        .user-header {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #E5E0DB;
        }}
        .session {{
            margin-bottom: 24px;
        }}
        .session-header {{
            font-size: 14px;
            color: #666;
            margin-bottom: 12px;
        }}
        .outfit-card {{
            background: white;
            border: 1px solid rgba(26, 22, 20, 0.12);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        .outfit-card.saved {{
            border-left: 4px solid #22c55e;
        }}
        .outfit-card.not-saved {{
            border-left: 4px solid #ef4444;
        }}
        .outfit-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .outfit-title {{
            font-weight: 600;
            font-size: 16px;
        }}
        .badge {{
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        .badge.saved {{
            background: #dcfce7;
            color: #166534;
        }}
        .badge.not-saved {{
            background: #fee2e2;
            color: #991b1b;
        }}
        .items-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 12px;
        }}
        .item-container {{
            position: relative;
            aspect-ratio: 1;
            border-radius: 4px;
            overflow: hidden;
            background: #E5E0DB;
        }}
        .item-container img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .styling-notes {{
            font-size: 14px;
            margin-bottom: 8px;
        }}
        .styling-notes strong {{
            color: #1A1614;
        }}
        .why-works {{
            font-size: 14px;
            color: #666;
        }}
        .drop-off {{
            background: #fef3c7;
            border: 1px solid #f59e0b;
            padding: 12px;
            border-radius: 6px;
            margin-top: 16px;
            font-size: 14px;
        }}
        .no-data {{
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Style Inspo Daily Digest - {formatted_date}</h1>
"""

    if not active_users:
        html += """
        <div class="no-data">
            <p>No outfit generations recorded for this day.</p>
        </div>
"""
    else:
        # Generate user sections
        for user_id in active_users:
            data = user_data[user_id]
            generations = data["generations"]
            saved_outfits = data["saved_outfits"]

            # Build saved lookup for this date
            saves_today = [
                saved for saved in saved_outfits
                if date_str in saved.get("saved_at", "")
            ]

            user_saves = 0
            user_outfits = 0
            used_save_ids = set()

            html += f"""
        <div class="user-section">
            <div class="user-header">{user_id.upper()}</div>
"""

            for gen in generations:
                gen_timestamp_str = gen.get("timestamp", "")
                gen_timestamp = parse_timestamp(gen_timestamp_str)
                mode = gen.get("mode", "unknown")
                outfits = gen.get("outfits", [])
                user_outfits += len(outfits)

                time_str = format_time(gen_timestamp_str)
                if mode == "occasion":
                    occasion = gen.get("occasion", "Not specified")
                    session_desc = f'{time_str} - "{occasion}"'
                else:
                    anchor_names = gen.get("anchor_item_names", [])
                    anchor_str = ", ".join(anchor_names[:2]) if anchor_names else "selected items"
                    session_desc = f'{time_str} - Complete look ({anchor_str})'

                html += f"""
            <div class="session">
                <div class="session-header">{session_desc} &rarr; {len(outfits)} outfits</div>
"""

                for i, outfit in enumerate(outfits, 1):
                    items = outfit.get("items", [])
                    styling_notes = outfit.get("styling_notes", "")
                    why_it_works = outfit.get("why_it_works", "")

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
                                    user_saves += 1
                                    used_save_ids.add(saved.get("id"))
                                    break

                    if was_saved:
                        total_saves += 1

                    card_class = "saved" if was_saved else "not-saved"
                    badge_class = "saved" if was_saved else "not-saved"
                    badge_text = f'SAVED "{save_feedback}"' if was_saved and save_feedback else ("SAVED" if was_saved else "Not saved")

                    html += f"""
                <div class="outfit-card {card_class}">
                    <div class="outfit-header">
                        <span class="outfit-title">Outfit {i}</span>
                        <span class="badge {badge_class}">{badge_text}</span>
                    </div>
                    <div class="items-grid">
"""

                    for item in items:
                        image_path = item.get("image_path", "")
                        item_name = item.get("name", "Unknown")
                        if image_path:
                            html += f'                        <div class="item-container"><img src="{image_path}" alt="{item_name}" title="{item_name}"></div>\n'
                        else:
                            html += f'                        <div class="item-container" title="{item_name}" style="display:flex;align-items:center;justify-content:center;font-size:11px;padding:8px;text-align:center;">{item_name}</div>\n'

                    html += f"""                    </div>
                    <div class="styling-notes"><strong>How to Style:</strong> {styling_notes}</div>
                    <div class="why-works"><strong>Why it works:</strong> {why_it_works}</div>
                </div>
"""

                html += """            </div>
"""

            # Drop-off warning
            if user_outfits > 0 and user_saves == 0:
                html += """
            <div class="drop-off">
                ⚠️ DROP-OFF: Left without saving any outfits
            </div>
"""

            html += """        </div>
"""

        # Summary stats
        save_rate = (total_saves / total_outfits * 100) if total_outfits > 0 else 0
        html = html.replace(
            f'<h1>Style Inspo Daily Digest - {formatted_date}</h1>',
            f'<h1>Style Inspo Daily Digest - {formatted_date}</h1>\n        <div class="summary">Active Users: {len(active_users)} | Outfits: {total_outfits} | Saved: {total_saves} ({save_rate:.0f}%)</div>'
        )

    html += """    </div>
</body>
</html>
"""

    return html


def main():
    parser = argparse.ArgumentParser(description="Generate HTML daily digest")
    parser.add_argument("date", nargs="?", help="Date in YYYY-MM-DD format (default: yesterday)")
    parser.add_argument("--exclude", nargs="*", default=["peichin"], help="Users to exclude")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open in browser")
    parser.add_argument("-o", "--output", help="Output file path (default: digest-DATE.html)")

    args = parser.parse_args()

    # Determine date (using Pacific time)
    pacific = ZoneInfo("America/Los_Angeles")
    if args.date:
        date_str = args.date
    else:
        yesterday = datetime.now(pacific) - timedelta(days=1)
        date_str = yesterday.strftime("%Y-%m-%d")

    # Generate HTML
    html = generate_html(date_str, exclude_users=args.exclude)

    # Write to file
    output_path = args.output or f"digest-{date_str}.html"
    with open(output_path, "w") as f:
        f.write(html)

    print(f"Generated: {output_path}")

    # Open in browser
    if not args.no_open:
        file_url = f"file://{os.path.abspath(output_path)}"
        webbrowser.open(file_url)
        print(f"Opened in browser")


if __name__ == "__main__":
    main()
