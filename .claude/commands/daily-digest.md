# Daily Usage Digest

Generate a daily briefing of Style Inspo usage showing who used the app, what they did, and the outcomes.

## Usage

Run the digest script from the backend directory:

```bash
cd /Users/peichin/Projects/style-inspo-api/backend
source venv/bin/activate
python scripts/daily_digest.py $ARGUMENTS
```

## Arguments

- No arguments: Shows yesterday's digest (excluding peichin)
- `YYYY-MM-DD`: Shows digest for specific date
- `--exclude user1 user2`: Exclude specific users (default: peichin)
- `--exclude`: Include all users (no exclusions)
- `-v, --verbose`: Show full details (default is compact mode with URLs)
- `--users`: List all users with data

## Examples

```bash
# Yesterday's digest (compact mode, ~30 lines with URLs)
python scripts/daily_digest.py

# Today's digest
python scripts/daily_digest.py 2026-01-19

# Include all users (for debugging)
python scripts/daily_digest.py 2026-01-19 --exclude

# Full verbose output (153+ lines with all item details)
python scripts/daily_digest.py 2026-01-19 -v

# List users
python scripts/daily_digest.py --users
```

## What it Shows

**Compact mode (default):**
- Each user with session count and save count
- Drop-off warning if user left without saving
- Each outfit with S3 image URL (first item)
- Save status with feedback

**Verbose mode (-v):**
- Full outfit details with all item names and URLs
- Complete styling context

**Summary stats:**
- Active user count
- Total outfits generated
- Save rate

## Data Sources

- S3: `{user}/generations/{date}.json` - All generated outfits
- S3: `{user}/saved_outfits.json` - Saved outfit records
- PostHog (optional): Enhanced event data when configured

## Note

Generation logging was added on Jan 19, 2026. Historical data before this date is not available.
