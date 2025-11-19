# Railway Worker Environment Variables Setup

## Problem
The worker service is using local storage while the API service uses S3 storage, causing "User profile not found" errors.

## Solution: Configure Worker Service Environment Variables

### Step 1: Access Railway Dashboard
1. Go to https://railway.app
2. Navigate to your project
3. Find the **Worker service** (separate from the backend API service)

### Step 2: Add Environment Variables
1. Click on the **Worker service**
2. Go to the **Variables** tab
3. Add/Verify these environment variables (must match backend service):

**Required Variables:**
```
STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=<your-aws-access-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-key>
S3_BUCKET_NAME=style-inspo-wardrobe
```

**Note:** The code supports both `S3_BUCKET_NAME` (primary) and `AWS_S3_BUCKET` (fallback) for backward compatibility, but `S3_BUCKET_NAME` is the preferred variable name.

**Also Required:**
```
REDIS_URL=<your-redis-url>
OPENAI_API_KEY=<your-openai-key>
```

### Step 3: Verify Variables Match Backend
- Go to **Backend service** → **Variables** tab
- Compare all variables with Worker service
- They should be identical (especially storage-related ones)

### Step 4: Redeploy Worker
1. After adding variables, Railway should auto-redeploy
2. If not, go to **Deployments** tab → Click **"Redeploy"**
3. Check **Logs** tab to verify:
   - Should see: "✅ Using S3 storage for user: [user]"
   - Should NOT see: "Reading profile JSON for user [user] (storage: local)"

### Step 5: Verify Worker is Running
Check logs for:
```
*** Listening on outfits, analysis...
```

## Quick Checklist
- [ ] STORAGE_TYPE=s3 is set in Worker service
- [ ] AWS_ACCESS_KEY_ID matches backend service
- [ ] AWS_SECRET_ACCESS_KEY matches backend service  
- [ ] S3_BUCKET_NAME matches backend service (or AWS_S3_BUCKET as fallback)
- [ ] REDIS_URL is set (should auto-populate)
- [ ] OPENAI_API_KEY is set
- [ ] Worker service redeployed after changes
- [ ] Logs show "Using S3 storage" (not "local storage")

## Testing
After setup, test both flows:
1. **Plan my outfit** - Should work without profile errors
2. **Complete my look** - Should work without profile errors

Check Railway logs to verify:
- No "User profile not found" errors
- Jobs complete successfully
- Worker shows "Using S3 storage" in logs

