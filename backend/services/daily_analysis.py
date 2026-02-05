"""
Daily Usage Analysis Service

Generates daily digest with AI-powered analysis of why outfits weren't saved.
Sends results via email.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from zoneinfo import ZoneInfo

import httpx

from services.storage_manager import StorageManager
from services.outfit_analyzer import analyze_outfit_failure, analyze_failure_patterns

logger = logging.getLogger(__name__)

# Config
PEICHIN_EMAIL = "peichin000@gmail.com"
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "Style Inspo <noreply@styleinspo.vercel.app>")

# Pei-Chin's device IDs - filter these out to see real user activity
PEICHIN_DEVICE_IDS = {
    '019b5d53-2130-76a8-943e-4a5552e0758b',
    '019bc998-094e-7309-a042-2e017cc5bd45',
    '019b6b77-3a3e-7343-942f-80c2bb67787a',
    '019b5d2f-f5cc-7329-bc3a-26f01842e4bd',
    'peichin'
}


def get_all_users_with_data() -> List[str]:
    """Get list of all users who have data in S3 by listing top-level prefixes."""
    import boto3

    # Filter out test users
    test_patterns = ['test', 'default', 'yourname', 'pa-test']

    bucket_name = os.getenv('S3_BUCKET_NAME') or os.getenv('AWS_S3_BUCKET')
    if not bucket_name:
        logger.warning("S3 bucket not configured, falling back to known users")
        return ['peichin', 'heather', 'dimple', 'alexi', 'mia', 'anneka', 'andy', 'dana', 'kate', 'muppoad']

    try:
        s3_client = boto3.client('s3')
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Delimiter='/'
        )

        users = []
        for prefix in response.get('CommonPrefixes', []):
            user_id = prefix['Prefix'].rstrip('/')
            # Skip system folders and test users
            if user_id and not user_id.startswith('.') and not user_id.startswith('_'):
                if not any(p in user_id.lower() for p in test_patterns):
                    users.append(user_id)

        return sorted(users)
    except Exception as e:
        logger.warning(f"Could not list S3 users: {e}, falling back to known users")
        return ['peichin', 'heather', 'dimple', 'alexi', 'mia', 'anneka', 'andy', 'dana', 'kate', 'muppoad']


def load_generations_for_date(user_id: str, date_str: str, exclude_device_ids: Set[str] = None) -> List[Dict]:
    """Load generation logs for a specific user and date."""
    try:
        storage = StorageManager(storage_type="s3", user_id=user_id)
        log_filename = f"generations/{date_str}.json"
        data = storage.load_json(log_filename)
        generations = data.get("generations", [])

        if exclude_device_ids:
            generations = [
                gen for gen in generations
                if gen.get("device_id") not in exclude_device_ids
            ]

        return generations
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


def load_user_profile(user_id: str) -> Optional[Dict]:
    """Load user style profile."""
    try:
        storage = StorageManager(storage_type="s3", user_id=user_id)
        data = storage.load_json("user_profile.json")
        style_words = data.get("style_words", [])
        # Convert list to dict format expected by analyzer
        if isinstance(style_words, list) and len(style_words) >= 2:
            return {
                "current": style_words[0] if len(style_words) > 0 else "",
                "aspirational": style_words[1] if len(style_words) > 1 else "",
                "feeling": style_words[2] if len(style_words) > 2 else ""
            }
        return None
    except Exception:
        return None


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


def format_time(timestamp_str: str) -> str:
    """Format ISO timestamp to readable time."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%I:%M %p").lstrip('0')
    except Exception:
        return timestamp_str


async def run_daily_analysis(date_str: Optional[str] = None, exclude_users: List[str] = None) -> Dict:
    """
    Run daily analysis for all active users.

    Args:
        date_str: Date to analyze (YYYY-MM-DD format). Defaults to yesterday.
        exclude_users: User IDs to exclude from analysis

    Returns:
        Dict with analysis results and email status
    """
    exclude_users = exclude_users or ["peichin"]

    # Determine date (default to yesterday in Pacific time)
    pacific = ZoneInfo("America/Los_Angeles")
    if not date_str:
        yesterday = datetime.now(pacific) - timedelta(days=1)
        date_str = yesterday.strftime("%Y-%m-%d")

    logger.info(f"Running daily analysis for {date_str}")

    # Collect data for all users
    all_users = get_all_users_with_data()
    active_users = []
    user_data = {}

    for user_id in all_users:
        if user_id in exclude_users:
            continue

        generations = load_generations_for_date(user_id, date_str, PEICHIN_DEVICE_IDS)
        if generations:
            active_users.append(user_id)
            saved_outfits = load_saved_outfits(user_id)
            user_profile = load_user_profile(user_id)
            user_data[user_id] = {
                "generations": generations,
                "saved_outfits": saved_outfits,
                "profile": user_profile
            }

    if not active_users:
        logger.info(f"No active users for {date_str}")
        return {"date": date_str, "active_users": 0, "email_sent": False}

    # Analyze each user's not-saved outfits
    analysis_results = {}

    for user_id in active_users:
        data = user_data[user_id]
        generations = data["generations"]
        saved_outfits = data["saved_outfits"]
        profile = data["profile"]

        # Build saved lookup for this date
        saves_today = [
            saved for saved in saved_outfits
            if date_str in saved.get("saved_at", "")
        ]
        used_save_ids = set()

        user_analysis = {
            "saved": [],
            "not_saved": [],
            "total_outfits": 0,
            "total_saved": 0
        }

        for gen in generations:
            gen_timestamp = parse_timestamp(gen.get("timestamp", ""))
            occasion = gen.get("occasion", "")
            outfits = gen.get("outfits", [])
            user_analysis["total_outfits"] += len(outfits)

            for outfit in outfits:
                items = outfit.get("items", [])

                # Check if this outfit was saved
                was_saved = False
                for saved in saves_today:
                    if saved.get("id") in used_save_ids:
                        continue
                    saved_items = saved.get("outfit_data", {}).get("items", [])
                    saved_timestamp = parse_timestamp(saved.get("saved_at", ""))
                    if gen_timestamp and saved_timestamp:
                        if saved_timestamp >= gen_timestamp:
                            if outfit_items_match(items, saved_items):
                                was_saved = True
                                user_analysis["total_saved"] += 1
                                used_save_ids.add(saved.get("id"))
                                user_analysis["saved"].append({
                                    "outfit": outfit,
                                    "reason": saved.get("user_reason", "")
                                })
                                break

                if not was_saved:
                    # Analyze this outfit
                    analysis = await analyze_outfit_failure(
                        outfit=outfit,
                        user_profile=profile,
                        occasion=occasion
                    )
                    user_analysis["not_saved"].append({
                        "outfit": outfit,
                        "occasion": occasion,
                        "analysis": analysis
                    })

        # Analyze patterns if multiple failures
        if len(user_analysis["not_saved"]) >= 2:
            user_analysis["pattern"] = await analyze_failure_patterns(
                user_analysis["not_saved"]
            )

        analysis_results[user_id] = user_analysis

    # Generate HTML email
    html_content = generate_analysis_email(date_str, analysis_results)

    # Send email
    email_sent = await send_analysis_email(date_str, html_content)

    # Calculate summary stats
    total_outfits = sum(r["total_outfits"] for r in analysis_results.values())
    total_saved = sum(r["total_saved"] for r in analysis_results.values())
    save_rate = (total_saved / total_outfits * 100) if total_outfits > 0 else 0

    return {
        "date": date_str,
        "active_users": len(active_users),
        "total_outfits": total_outfits,
        "total_saved": total_saved,
        "save_rate": round(save_rate, 1),
        "email_sent": email_sent,
        "users": list(analysis_results.keys())
    }


def generate_analysis_email(date_str: str, analysis_results: Dict) -> str:
    """Generate HTML email content with analysis."""
    # Format date
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%b %d, %Y")
    except Exception:
        formatted_date = date_str

    # Calculate summary stats
    total_outfits = sum(r["total_outfits"] for r in analysis_results.values())
    total_saved = sum(r["total_saved"] for r in analysis_results.values())
    save_rate = (total_saved / total_outfits * 100) if total_outfits > 0 else 0

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Style Inspo Daily Analysis - {formatted_date}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
            background: #FAF8F5;
            color: #1A1614;
        }}
        .header {{
            margin-bottom: 24px;
        }}
        h1 {{
            font-size: 22px;
            margin: 0 0 8px 0;
        }}
        .summary {{
            background: white;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 24px;
            border: 1px solid #E5E0DB;
        }}
        .stat {{
            display: inline-block;
            margin-right: 24px;
            font-size: 14px;
        }}
        .stat-value {{
            font-weight: 600;
            font-size: 20px;
        }}
        .user-section {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #E5E0DB;
        }}
        .user-header {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #E5E0DB;
        }}
        .outfit-card {{
            background: #FAF8F5;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 16px;
        }}
        .outfit-card.not-saved {{
            border-left: 4px solid #ef4444;
        }}
        .outfit-card.saved {{
            border-left: 4px solid #22c55e;
        }}
        .outfit-items {{
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }}
        .item-img {{
            width: 70px;
            height: 70px;
            object-fit: cover;
            border-radius: 4px;
            background: #E5E0DB;
        }}
        .item-placeholder {{
            width: 70px;
            height: 70px;
            border-radius: 4px;
            background: #E5E0DB;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            text-align: center;
            padding: 4px;
            color: #666;
        }}
        .outfit-details {{
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
        }}
        .analysis {{
            background: #FEF3C7;
            padding: 12px;
            border-radius: 4px;
            font-size: 13px;
            margin-top: 8px;
        }}
        .analysis-label {{
            font-weight: 600;
            color: #B45309;
            margin-bottom: 4px;
        }}
        .pattern {{
            background: #DBEAFE;
            padding: 12px;
            border-radius: 6px;
            margin-top: 16px;
            font-size: 13px;
        }}
        .pattern-label {{
            font-weight: 600;
            color: #1E40AF;
            margin-bottom: 4px;
        }}
        .drop-off {{
            background: #FEE2E2;
            color: #991B1B;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 13px;
            margin-top: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Style Inspo Daily Analysis</h1>
        <div style="color: #666;">{formatted_date}</div>
    </div>

    <div class="summary">
        <div class="stat">
            <div class="stat-value">{len(analysis_results)}</div>
            <div>Active Users</div>
        </div>
        <div class="stat">
            <div class="stat-value">{total_outfits}</div>
            <div>Outfits Generated</div>
        </div>
        <div class="stat">
            <div class="stat-value">{total_saved}</div>
            <div>Saved ({save_rate:.0f}%)</div>
        </div>
    </div>
"""

    for user_id, data in analysis_results.items():
        user_saved = data["total_saved"]
        user_total = data["total_outfits"]
        not_saved_count = len(data["not_saved"])

        html += f"""
    <div class="user-section">
        <div class="user-header">
            👤 {user_id.upper()} ({user_saved}/{user_total} saved)
        </div>
"""

        # Show saved outfits first (no analysis needed)
        if data["saved"]:
            for i, item in enumerate(data["saved"], 1):
                outfit = item["outfit"]
                reason = item.get("reason", "")
                items = outfit.get("items", [])

                html += f"""
        <div class="outfit-card saved">
            <div style="font-weight: 600; margin-bottom: 8px;">✅ Saved #{i}{f' - "{reason}"' if reason else ''}</div>
            <div class="outfit-items">
"""
                for itm in items:
                    image_path = itm.get("image_path", "")
                    name = itm.get("name", "Unknown")
                    if image_path and image_path.startswith("http"):
                        html += f'                <img src="{image_path}" alt="{name}" title="{name}" class="item-img">\n'
                    else:
                        html += f'                <div class="item-placeholder">{name[:20]}</div>\n'

                styling_notes = outfit.get("styling_notes", "")

                html += f"""            </div>
            <div class="outfit-details">
                <strong>Items:</strong> {', '.join(itm.get('name', 'Unknown') for itm in items)}
            </div>
            <div class="outfit-details">
                <strong>Styling:</strong> {styling_notes[:150]}{'...' if len(styling_notes) > 150 else ''}
            </div>
        </div>
"""

        # Show not-saved outfits with analysis
        if data["not_saved"]:
            for i, item in enumerate(data["not_saved"], 1):
                outfit = item["outfit"]
                analysis = item["analysis"]
                items = outfit.get("items", [])

                html += f"""
        <div class="outfit-card not-saved">
            <div style="font-weight: 600; margin-bottom: 8px;">❌ Not Saved #{i}</div>
            <div class="outfit-items">
"""
                for itm in items:
                    image_path = itm.get("image_path", "")
                    name = itm.get("name", "Unknown")
                    if image_path and image_path.startswith("http"):
                        html += f'                <img src="{image_path}" alt="{name}" title="{name}" class="item-img">\n'
                    else:
                        html += f'                <div class="item-placeholder">{name[:20]}</div>\n'

                styling_notes = outfit.get("styling_notes", "")

                html += f"""            </div>
            <div class="outfit-details">
                <strong>Items:</strong> {', '.join(itm.get('name', 'Unknown') for itm in items)}
            </div>
            <div class="outfit-details">
                <strong>Styling:</strong> {styling_notes[:150]}{'...' if len(styling_notes) > 150 else ''}
            </div>
            <div class="analysis">
                <div class="analysis-label">🤖 AI Analysis:</div>
                {analysis}
            </div>
        </div>
"""

            # Add pattern if detected
            if data.get("pattern"):
                html += f"""
        <div class="pattern">
            <div class="pattern-label">📈 Pattern Detected:</div>
            {data["pattern"]}
        </div>
"""

        # Drop-off warning
        if user_total > 0 and user_saved == 0:
            html += """
        <div class="drop-off">
            ⚠️ DROP-OFF: Left without saving any outfits
        </div>
"""

        html += """
    </div>
"""

    html += """
</body>
</html>
"""

    return html


async def send_analysis_email(date_str: str, html_content: str) -> bool:
    """Send analysis email via Resend."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured, skipping email")
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": RESEND_FROM_EMAIL,
                    "to": [PEICHIN_EMAIL],
                    "subject": f"Style Inspo Daily Analysis - {date_str}",
                    "html": html_content
                },
                timeout=30.0
            )

            if response.status_code == 200:
                logger.info(f"Daily analysis email sent successfully for {date_str}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False


class DailyAnalysisService:
    """Service class for compatibility with existing patterns."""

    async def run_analysis(self, date_str: Optional[str] = None) -> Dict:
        """Run daily analysis. Wrapper for run_daily_analysis."""
        return await run_daily_analysis(date_str)


async def run_daily_analysis_preview(date_str: Optional[str] = None, exclude_users: List[str] = None) -> str:
    """
    Run daily analysis and return HTML content (without sending email).

    Useful for previewing what the email will look like.

    Args:
        date_str: Date to analyze (YYYY-MM-DD format). Defaults to yesterday.
        exclude_users: User IDs to exclude from analysis

    Returns:
        HTML content of the analysis email
    """
    exclude_users = exclude_users or ["peichin"]

    # Determine date (default to yesterday in Pacific time)
    pacific = ZoneInfo("America/Los_Angeles")
    if not date_str:
        yesterday = datetime.now(pacific) - timedelta(days=1)
        date_str = yesterday.strftime("%Y-%m-%d")

    logger.info(f"Running daily analysis preview for {date_str}")

    # Collect data for all users
    all_users = get_all_users_with_data()
    active_users = []
    user_data = {}

    for user_id in all_users:
        if user_id in exclude_users:
            continue

        generations = load_generations_for_date(user_id, date_str, PEICHIN_DEVICE_IDS)
        if generations:
            active_users.append(user_id)
            saved_outfits = load_saved_outfits(user_id)
            user_profile = load_user_profile(user_id)
            user_data[user_id] = {
                "generations": generations,
                "saved_outfits": saved_outfits,
                "profile": user_profile
            }

    if not active_users:
        logger.info(f"No active users for {date_str}")
        return f"<html><body><h1>No active users for {date_str}</h1></body></html>"

    # Analyze each user's not-saved outfits
    analysis_results = {}

    for user_id in active_users:
        data = user_data[user_id]
        generations = data["generations"]
        saved_outfits = data["saved_outfits"]
        profile = data["profile"]

        # Build saved lookup for this date
        saves_today = [
            saved for saved in saved_outfits
            if date_str in saved.get("saved_at", "")
        ]
        used_save_ids = set()

        user_analysis = {
            "saved": [],
            "not_saved": [],
            "total_outfits": 0,
            "total_saved": 0
        }

        for gen in generations:
            gen_timestamp = parse_timestamp(gen.get("timestamp", ""))
            occasion = gen.get("occasion", "")
            outfits = gen.get("outfits", [])
            user_analysis["total_outfits"] += len(outfits)

            for outfit in outfits:
                items = outfit.get("items", [])

                # Check if this outfit was saved
                was_saved = False
                for saved in saves_today:
                    if saved.get("id") in used_save_ids:
                        continue
                    saved_items = saved.get("outfit_data", {}).get("items", [])
                    saved_timestamp = parse_timestamp(saved.get("saved_at", ""))
                    if gen_timestamp and saved_timestamp:
                        if saved_timestamp >= gen_timestamp:
                            if outfit_items_match(items, saved_items):
                                was_saved = True
                                user_analysis["total_saved"] += 1
                                used_save_ids.add(saved.get("id"))
                                user_analysis["saved"].append({
                                    "outfit": outfit,
                                    "reason": saved.get("user_reason", "")
                                })
                                break

                if not was_saved:
                    # Analyze this outfit
                    analysis = await analyze_outfit_failure(
                        outfit=outfit,
                        user_profile=profile,
                        occasion=occasion
                    )
                    user_analysis["not_saved"].append({
                        "outfit": outfit,
                        "occasion": occasion,
                        "analysis": analysis
                    })

        # Analyze patterns if multiple failures
        if len(user_analysis["not_saved"]) >= 2:
            user_analysis["pattern"] = await analyze_failure_patterns(
                user_analysis["not_saved"]
            )

        analysis_results[user_id] = user_analysis

    # Generate and return HTML
    return generate_analysis_email(date_str, analysis_results)
