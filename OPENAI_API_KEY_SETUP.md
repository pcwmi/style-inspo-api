# OpenAI API Key Setup Guide

## Problem
Getting "invalid_api_key" error when generating outfits.

## Solution: Get Fresh API Key from OpenAI Platform

### Step 1: Get API Key from OpenAI (Not Streamlit)
1. Go to https://platform.openai.com/account/api-keys
2. Sign in to your OpenAI account
3. Click **"Create new secret key"**
4. Give it a name (e.g., "Style Inspo Production")
5. **Copy the key immediately** - you won't be able to see it again!

### Step 2: Set in Railway Worker Service
1. Go to Railway dashboard → **Worker service** → **Variables** tab
2. Find `OPENAI_API_KEY` variable
3. Click to edit it
4. **Paste the fresh key from OpenAI platform**
5. Make sure there are:
   - No extra spaces before/after
   - No quotes around it
   - The full key (starts with `sk-` and is very long)
6. Save

### Step 3: Set in Railway Backend Service (if needed)
1. Go to Railway dashboard → **Backend service** → **Variables** tab
2. Verify `OPENAI_API_KEY` is set (should match worker service)
3. If not set, add it with the same key

### Step 4: Redeploy
- Railway should auto-redeploy after variable changes
- If not, manually redeploy both services

## Important Notes

**DO NOT:**
- ❌ Copy from Streamlit secrets (might be old/expired)
- ❌ Add quotes around the key
- ❌ Add extra spaces
- ❌ Use a key that's been revoked

**DO:**
- ✅ Get fresh key from https://platform.openai.com/account/api-keys
- ✅ Copy the entire key (it's very long)
- ✅ Set it in both Worker and Backend services
- ✅ Verify no extra characters

## Verify Key Format
A valid OpenAI API key:
- Starts with `sk-` or `sk-proj-`
- Is very long (50+ characters)
- Has no spaces
- Has no quotes

## Testing
After setting the key:
1. Check Railway logs for worker service
2. Try generating outfits again
3. Should see successful API calls (no "invalid_api_key" errors)

## If Still Getting Errors
1. **Check key is active**: Go to OpenAI platform → API keys → verify key status
2. **Check billing**: Make sure your OpenAI account has credits/quota
3. **Check key permissions**: Some keys might have restrictions
4. **Try creating a new key**: Old keys might be expired

## Key Security
- Never commit API keys to git
- Never share keys publicly
- Rotate keys periodically
- Use different keys for dev/prod if possible

