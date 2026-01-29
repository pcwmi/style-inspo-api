# Daily Usage Digest

Generate a visual HTML digest of Style Inspo usage showing outfit compositions, save rates, and user feedback.

## Usage

Run the HTML digest generator from the backend directory:

```bash
cd /Users/peichin/Projects/style-inspo-api/backend
source venv/bin/activate
python scripts/generate_digest_html.py $ARGUMENTS
```

This generates an HTML file and automatically opens it in your browser.

## Arguments

- No arguments: Shows yesterday's digest (excluding peichin)
- `YYYY-MM-DD`: Shows digest for specific date
- `--exclude user1 user2`: Exclude specific users (default: peichin)
- `--exclude`: Include all users (no exclusions)
- `--include-admin`: Include generations from Pei-Chin's device IDs (by default, these are filtered out even when viewing other users)
- `--no-open`: Generate file without opening browser
- `-o, --output`: Custom output file path

## Examples

```bash
# Yesterday's digest (auto-opens in browser)
python scripts/generate_digest_html.py

# Today's digest
python scripts/generate_digest_html.py 2026-01-19

# Include all users (for debugging)
python scripts/generate_digest_html.py 2026-01-19 --exclude

# Generate without opening browser
python scripts/generate_digest_html.py 2026-01-19 --no-open
```

## What the HTML Shows

Each outfit displayed as a visual card (replicating the OutfitCard pattern):
- **3-column grid** of all items in the outfit
- **Green badge** for saved outfits with user feedback
- **Red badge** for unsaved outfits
- **Styling notes** and "Why it works" explanations
- **Drop-off warning** if user left without saving

**Summary stats at top:**
- Active user count
- Total outfits generated
- Save rate percentage

## Output

- HTML file: `digest-{YYYY-MM-DD}.html` in current directory
- Auto-opens in default browser (unless `--no-open`)

## CLI Text Version (Fallback)

For text-only output, use the original script:

```bash
python scripts/daily_digest.py 2026-01-19
```

## Data Sources

- S3: `{user}/generations/{date}.json` - All generated outfits
- S3: `{user}/saved_outfits.json` - Saved outfit records

## Device ID Filtering

By default, the digest filters out generations made from Pei-Chin's device IDs. This separates real user activity from admin testing (e.g., when Pei-Chin visits `?user=dimple` to test that user's experience).

**How it works:**
- Frontend passes PostHog device_id to backend during outfit generation
- Backend logs device_id with each generation in S3
- Digest script filters out known admin device IDs

**Note:** This filtering only works for generations made AFTER this feature was deployed. Historical generations without device_id will still appear in the digest.

Use `--include-admin` to see all generations including admin testing.

## Note

Generation logging was added on Jan 19, 2026. Historical data before this date is not available.
