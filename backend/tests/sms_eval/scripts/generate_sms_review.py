#!/usr/bin/env python3
"""
Generate interactive HTML review page from SMS eval results.

Displays multi-turn conversations with agent responses, item images,
star ratings, and notes. All ratings persist in localStorage.

Usage:
    cd backend/tests/sms_eval
    python scripts/generate_sms_review.py                    # auto-find latest results
    python scripts/generate_sms_review.py --results-dir results/sms_eval_20260213_120000
"""

import json
import os
import sys
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))
os.environ['STORAGE_TYPE'] = 's3'


def find_latest_results_dir() -> Optional[Path]:
    """Find the most recent results directory."""
    results_base = Path(__file__).parent.parent / 'results'
    if not results_base.exists():
        return None

    dirs = sorted(
        [d for d in results_base.iterdir() if d.is_dir() and d.name.startswith('sms_eval_')],
        key=lambda d: d.name,
        reverse=True
    )
    return dirs[0] if dirs else None


def sanitize_id(text: str) -> str:
    """Create safe HTML ID from text."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', text)


USE_CASE_COLORS = {
    "inspiration_photo": ("#3b82f6", "Inspiration"),
    "selfie_improve": ("#22c55e", "Selfie"),
    "occasion": ("#a855f7", "Occasion"),
}


def generate_html(results: List[Dict], eval_name: str) -> str:
    """Generate the full HTML review page."""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SMS Eval Review: {eval_name}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: #f0f0f0;
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
            color: #1a1a1a;
        }}
        h1 {{ margin-bottom: 5px; }}
        .summary {{ color: #666; margin-bottom: 30px; }}

        .scenario {{
            background: white;
            padding: 25px;
            margin: 25px 0;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .scenario-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }}
        .scenario-header h2 {{
            margin: 0;
            font-size: 18px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            color: white;
        }}
        .meta {{
            font-size: 12px;
            color: #999;
            margin-left: auto;
        }}

        /* Chat bubbles */
        .turn {{ margin: 15px 0; }}
        .user-bubble {{
            background: #007aff;
            color: white;
            padding: 12px 16px;
            border-radius: 18px 18px 4px 18px;
            max-width: 75%;
            margin-left: auto;
            margin-bottom: 4px;
            font-size: 15px;
            line-height: 1.4;
        }}
        .user-photo {{
            max-width: 200px;
            border-radius: 12px;
            margin-top: 8px;
            display: block;
            margin-left: auto;
        }}
        .turn-label {{
            font-size: 11px;
            color: #999;
            margin-bottom: 4px;
            text-align: right;
        }}
        .turn-label.agent-label {{
            text-align: left;
        }}

        .agent-response {{
            background: #f1f1f1;
            padding: 15px;
            border-radius: 18px 18px 18px 4px;
            max-width: 85%;
            margin-top: 8px;
        }}
        .agent-text {{
            font-size: 14px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .agent-text strong {{ color: #333; }}

        /* Item images */
        .item-images {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }}
        .item-images img {{
            width: 120px;
            height: 120px;
            object-fit: cover;
            border-radius: 8px;
            border: 2px solid #ddd;
            transition: transform 0.2s;
            cursor: pointer;
        }}
        .item-images img:hover {{
            transform: scale(2.2);
            z-index: 1000;
            box-shadow: 0 12px 24px rgba(0,0,0,0.4);
            border-color: #007aff;
            position: relative;
        }}

        /* Latency badge */
        .latency {{
            display: inline-block;
            font-size: 11px;
            color: #999;
            margin-left: 8px;
        }}

        /* Rating widget */
        .rating-section {{
            margin-top: 12px;
            padding: 12px;
            background: white;
            border-radius: 8px;
            border: 1px solid #e5e5e5;
        }}
        .rating-row {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .rating-label {{
            font-size: 12px;
            font-weight: 600;
            color: #666;
            min-width: 40px;
        }}
        .rating-stars {{
            display: flex;
            gap: 3px;
        }}
        .star {{
            font-size: 22px;
            cursor: pointer;
            color: #ddd;
            transition: color 0.15s;
            user-select: none;
        }}
        .star:hover, .star.active {{
            color: #ffc107;
        }}
        .notes-input {{
            width: 100%;
            min-height: 40px;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-family: inherit;
            font-size: 13px;
            margin-top: 8px;
            resize: vertical;
        }}
        .notes-input:focus {{
            outline: none;
            border-color: #007aff;
        }}

        /* Overall scenario rating */
        .overall-rating {{
            margin-top: 20px;
            padding-top: 15px;
            border-top: 2px solid #e5e5e5;
        }}
        .overall-rating .rating-label {{
            font-size: 14px;
            font-weight: 700;
            color: #333;
        }}

        /* Error state */
        .error {{
            background: #fee;
            color: #c00;
            padding: 10px;
            border-radius: 8px;
            font-size: 13px;
        }}

        /* No images fallback */
        .text-only-response {{
            font-style: italic;
            color: #666;
            font-size: 13px;
            margin-top: 8px;
        }}
    </style>
    <script>
        function setRating(ratingId, rating) {{
            const stars = document.querySelectorAll('#' + ratingId + ' .star');
            stars.forEach((star, index) => {{
                if (index < rating) {{
                    star.classList.add('active');
                }} else {{
                    star.classList.remove('active');
                }}
            }});
            localStorage.setItem('sms-rating-' + ratingId, rating);
        }}

        function saveNotes(ratingId) {{
            const el = document.getElementById('notes-' + ratingId);
            if (el) localStorage.setItem('sms-notes-' + ratingId, el.value);
        }}

        function loadSavedData() {{
            document.querySelectorAll('[data-rating-id]').forEach(el => {{
                const ratingId = el.dataset.ratingId;
                const savedRating = localStorage.getItem('sms-rating-' + ratingId);
                const savedNotes = localStorage.getItem('sms-notes-' + ratingId);

                if (savedRating) {{
                    setRating(ratingId, parseInt(savedRating));
                }}
                if (savedNotes) {{
                    const notesEl = document.getElementById('notes-' + ratingId);
                    if (notesEl) notesEl.value = savedNotes;
                }}
            }});
        }}

        function exportRatings() {{
            const ratings = {{}};
            for (let i = 0; i < localStorage.length; i++) {{
                const key = localStorage.key(i);
                if (key.startsWith('sms-rating-') || key.startsWith('sms-notes-')) {{
                    ratings[key] = localStorage.getItem(key);
                }}
            }}
            const blob = new Blob([JSON.stringify(ratings, null, 2)], {{type: 'application/json'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'sms_eval_ratings.json';
            a.click();
        }}

        window.addEventListener('load', loadSavedData);
    </script>
</head>
<body>
    <h1>SMS Agent Eval Review</h1>
    <p class="summary">
        <strong>{eval_name}</strong> &mdash;
        {len(results)} scenario run(s) &mdash;
        <a href="#" onclick="exportRatings(); return false;">Export ratings</a>
    </p>
"""

    for result in results:
        scenario_id = sanitize_id(result["scenario_id"])
        use_case = result.get("use_case", "unknown")
        color, label = USE_CASE_COLORS.get(use_case, ("#888", use_case))
        total_time = result.get("total_latency_seconds", 0)
        iteration = result.get("iteration", 0)
        iter_label = f" (iter {iteration + 1})" if iteration > 0 else ""

        html += f"""
    <div class="scenario">
        <div class="scenario-header">
            <span class="badge" style="background: {color};">{label}</span>
            <h2>{result['scenario_name']}{iter_label}</h2>
            <span class="meta">{result['user_id']} | {total_time}s total</span>
        </div>
"""

        # Render each turn
        for turn in result.get("turns", []):
            turn_num = turn["turn"]
            turn_id = f"{scenario_id}_t{turn_num}"

            # User bubble
            html += f"""
        <div class="turn">
            <div class="turn-label">Turn {turn_num}</div>
            <div class="user-bubble">{_escape(turn['user_message'])}</div>
"""
            # User photo (if any)
            if turn.get("image_url"):
                img_type = turn.get("image_type", "photo")
                html += f"""            <img class="user-photo" src="{turn['image_url']}" alt="{img_type} photo" />
"""

            html += "        </div>\n"

            # Agent response
            if not turn.get("success", True):
                html += f"""
        <div class="turn">
            <div class="turn-label agent-label">Agent <span class="latency">{turn.get('latency_seconds', 0)}s</span></div>
            <div class="error">Error: {_escape(turn.get('error', 'Unknown error'))}</div>
        </div>
"""
                continue

            # Get agent output
            output_msgs = turn.get("output_messages", [])
            agent_text = turn.get("agent_text_response", "") or ""

            html += f"""
        <div class="turn">
            <div class="turn-label agent-label">Agent <span class="latency">{turn.get('latency_seconds', 0)}s</span></div>
            <div class="agent-response">
"""

            if output_msgs:
                # Show what was actually sent to user (send_message calls)
                for msg in output_msgs:
                    msg_text = msg.get("text", "")
                    images = msg.get("images", [])

                    if msg_text:
                        html += f"""                <div class="agent-text">{_format_agent_text(msg_text)}</div>
"""
                    if images:
                        html += """                <div class="item-images">
"""
                        for img_url in images:
                            html += f"""                    <img src="{img_url}" alt="outfit item" />
"""
                        html += """                </div>
"""
            else:
                # Text-only response (no send_message called)
                if agent_text:
                    html += f"""                <div class="agent-text">{_format_agent_text(agent_text)}</div>
                <div class="text-only-response">(text only - no outfit images sent)</div>
"""

            # Per-turn rating
            html += f"""
                <div class="rating-section" id="{turn_id}" data-rating-id="{turn_id}">
                    <div class="rating-row">
                        <span class="rating-label">Rate:</span>
                        <div class="rating-stars">
                            {"".join(f'<span class="star" onclick="setRating(\\'{turn_id}\\', {i})">&#9733;</span>' for i in range(1, 6))}
                        </div>
                    </div>
                    <textarea class="notes-input" id="notes-{turn_id}" placeholder="Notes..." oninput="saveNotes('{turn_id}')"></textarea>
                </div>
"""

            html += """            </div>
        </div>
"""

        # Overall scenario rating
        overall_id = f"{scenario_id}_overall"
        html += f"""
        <div class="overall-rating" id="{overall_id}" data-rating-id="{overall_id}">
            <div class="rating-row">
                <span class="rating-label">Overall:</span>
                <div class="rating-stars">
                    {"".join(f'<span class="star" onclick="setRating(\\'{overall_id}\\', {i})">&#9733;</span>' for i in range(1, 6))}
                </div>
            </div>
            <textarea class="notes-input" id="notes-{overall_id}" placeholder="Overall notes for this conversation..." oninput="saveNotes('{overall_id}')"></textarea>
        </div>
    </div>
"""

    html += """
</body>
</html>
"""
    return html


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _format_agent_text(text: str) -> str:
    """Format agent text with basic markdown rendering."""
    text = _escape(text)
    # Bold: **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic: *text*
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text


def main():
    parser = argparse.ArgumentParser(description='Generate SMS eval review HTML')
    parser.add_argument('--results-dir', default=None, help='Results directory (default: latest)')

    args = parser.parse_args()

    # Find results directory
    if args.results_dir:
        results_dir = Path(args.results_dir)
    else:
        results_dir = find_latest_results_dir()
        if not results_dir:
            print("No results found. Run run_sms_eval.py first.")
            sys.exit(1)
        print(f"Using latest results: {results_dir}")

    # Load results
    results_file = results_dir / 'raw_results.json'
    if not results_file.exists():
        print(f"No raw_results.json in {results_dir}")
        sys.exit(1)

    with open(results_file, 'r') as f:
        results = json.load(f)

    print(f"Loaded {len(results)} scenario runs")

    # Generate HTML
    eval_name = results_dir.name
    html = generate_html(results, eval_name)

    # Write HTML
    output_path = results_dir / f'SMS_REVIEW_{eval_name}.html'
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Review page: {output_path}")
    print(f"\nOpen in browser: open '{output_path}'")


if __name__ == '__main__':
    main()
