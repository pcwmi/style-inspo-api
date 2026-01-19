# Verification Protocol for Feature Development

Use this checklist when building features that require E2E verification.

## Pre-requisites (before running verification)

- [ ] If feature requires data, CREATE test data first (Playwright/API)
- [ ] Identify all external links/URLs the feature outputs
- [ ] Define explicit "PASS" criteria (not just "runs without error")

## Verification Steps

### Step 1: Ensure Non-Empty Data

- [ ] Generate real data via E2E flow (Playwright)
- [ ] Confirm data exists: check S3, DB, or API response
- [ ] If data is date-sensitive, use TODAY's date for testing
- [ ] Never test with empty/mock data and call it "verified"

### Step 2: Functional Verification

- [ ] Run the feature with real data
- [ ] Output should contain expected elements (not empty/zero counts)
- [ ] Capture actual output in the conversation for user review

### Step 3: Link Verification

- [ ] Extract ALL URLs from output
- [ ] For each URL type:
  - **Image URLs**: Navigate with Playwright, confirm image loads (not 404)
  - **Page URLs**: Navigate with Playwright, confirm page renders expected content
  - **API URLs**: Curl or fetch, confirm 200 response with valid data
- [ ] Fix any broken links before marking complete

## PASS Criteria (all must be true)

- [ ] Output shows ≥1 real data point (not empty state)
- [ ] All URLs return 200 (not 404/500)
- [ ] Saved/persisted data can be retrieved and displayed
- [ ] User can click any link in output and see expected content

## Anti-patterns to Avoid

| Anti-pattern | Why it's bad | What to do instead |
|--------------|--------------|-------------------|
| Testing with yesterday's date for new feature | No historical data exists | Generate data for today, then test |
| Assuming URL format without checking | Route may not exist | Verify route exists in codebase first |
| Marking "verified" after code runs | Running ≠ working correctly | Verify output contains expected data |
| Testing only happy path | Misses edge cases | Test empty state, error state too |

## Example: Daily Digest Verification

```bash
# 1. Generate test data (Playwright)
- Navigate to /occasion?user=heather
- Select occasion, click Generate
- Save one outfit with feedback

# 2. Run feature with today's date
python scripts/daily_digest.py 2026-01-19 --exclude

# 3. Verify output
- Shows heather as active user
- Shows generation session with occasion
- Shows outfits with save status
- Shows correct stats (not all zeros)

# 4. Verify all links
- Click each S3 image URL → image loads
- Click saved outfit URL → page shows outfits
```
