# Post-Deploy Verification

Verify all 3 agent channels work on production after deploy. Run this after pushing to Railway.

**Production backend:** `https://style-inspo-api-production.up.railway.app`

## Checks

Run these sequentially. Abort early if health check fails.

### 1. Backend health (fast gate)
```bash
curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://style-inspo-api-production.up.railway.app/health
```
- Expected: HTTP 200
- If non-200: **FAIL** — backend is down, skip remaining checks

### 2. SMS channel health
```bash
curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://style-inspo-api-production.up.railway.app/api/sms/health"
```
- Expected: HTTP 200
- Note: Health check only — we don't send real SMS in verification

### 3. Web channel (SSE stream starts)
```bash
curl -s --max-time 30 -N "https://style-inspo-api-production.up.railway.app/api/outfits/generate/agent-stream?user_id=peichin&mode=occasion&occasions=casual+brunch" 2>&1 | head -c 500
```
- Expected: Contains `event: outfit` and `data:` with items array
- Only read first 500 chars — enough to verify stream starts, don't wait for full generation

### 4. API channel (outfits vs messages separation)
```bash
curl -s --max-time 60 -X POST "https://style-inspo-api-production.up.railway.app/api/agent/run" -H "Content-Type: application/json" -d '{"user_id":"peichin","message":"Create 1 outfit for casual brunch"}'
```
- Expected: JSON with `outfits` array (length >= 1), `messages` array, `text_response` not null
- Use jq to validate: `| jq '{outfit_count: (.outfits | length), has_text: (.text_response != null)}'`

## Output format

- **All green:** `✅ Deploy verified — all 4 checks passed` with timestamp
- **Any failure:** Show which check failed with the response body

## Important

- Checks 3 and 4 trigger real outfit generation (~$0.01-0.02 OpenAI cost). Don't loop this.
- API check (4) blocks ~30-40s while agent runs synchronously.
- If web stream check times out, check Railway logs for OpenAI errors.
