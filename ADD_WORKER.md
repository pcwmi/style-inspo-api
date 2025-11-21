# How to Add Worker Process in Railway

The worker process needs to be a **separate service** in your Railway project, not a setting within your existing service.

## Step-by-Step

1. **Go to Project View**:
   - If you're inside a service (like in Settings), click the **project name** at the top or close the service panel
   - You should see all your services listed (backend service, Redis service)

2. **Add New Service**:
   - Look for a **"+ New"** button
   - It might be:
     - Top right corner of the project view
     - A button in the services list
     - A "+" icon next to your services

3. **Select Service Type**:
   - Click **"+ New"**
   - Choose **"GitHub Repo"** (preferred) or **"Empty Service"**
   - If "GitHub Repo": Select `pcwmi/style-inspo-api` again

4. **Configure Worker Service**:
   - Click on the **new service** that was created
   - Go to **Settings** tab
   - Set **Root Directory**: `backend`
   - Go to **Deploy** section (scroll down in Settings)
   - Find **"Start Command"** or **"Command"** field
   - Enter: `rq worker outfits analysis --url $REDIS_URL`
   - Save

5. **Set Environment Variables**:
   - Go to **Variables** tab of the worker service
   - Add the same variables as your backend:
     - `REDIS_URL` (should auto-populate if Redis is in same project)
     - `OPENAI_API_KEY` (needed for outfit generation)
     - `STORAGE_TYPE` (if using S3)
     - AWS credentials (if using S3)

## Visual Guide

```
Railway Project View
  ├── [Backend Service] ← Your API
  ├── [Redis Service] ← Redis
  └── [+ New] ← Click here to add worker
      └── Select "GitHub Repo"
          └── [New Worker Service] ← Configure this
              ├── Settings → Root Directory: backend
              ├── Settings → Deploy → Start Command: rq worker...
              └── Variables → Add REDIS_URL, OPENAI_API_KEY
```

## Alternative: Use Procfile (Simpler)

Actually, Railway can run multiple processes from one Procfile! You might not need a separate service.

**Check if this works first:**
- Your `backend/Procfile` already has both `web` and `worker` defined
- Railway might run both automatically
- Check your backend service logs to see if the worker is running

**If the worker isn't running automatically**, then create the separate service as described above.

## Verify Worker is Running

1. Go to your worker service (or backend service if using Procfile)
2. Check the **Logs** tab
3. You should see: `*** Listening on outfits, analysis...`

If you see that message, your worker is running! ✅

