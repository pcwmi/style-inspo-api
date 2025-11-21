# Quick Deploy Guide - You're Ready! 🚀

Your code is now on GitHub at: `https://github.com/pcwmi/style-inspo-api`

## Step 1: Deploy Backend to Railway

1. **Go to Railway**: https://railway.app
2. **Sign up/Login** (can use GitHub to sign in)
3. **New Project** → **Deploy from GitHub repo**
4. **Select**: `pcwmi/style-inspo-api`
5. **Set Root Directory** (⚠️ **IMPORTANT!**):
   - After selecting the repo, Railway will create a service
   - Click on the **service** (it will have a name like "style-inspo-api")
   - Go to the **Settings** tab
   - Scroll down to **"Root Directory"** section
   - Enter: `backend`
   - Click **"Save"**
   - Railway will auto-detect it's a Python app and use the `Procfile`

6. **Add Redis Service**:
   - In your Railway project, click **"+ New"**
   - Select **"Redis"**
   - Railway will provision it automatically
   - ✅ **Good news**: Railway often auto-configures `REDIS_URL` for you!
   - If you see `REDIS_URL` already in your backend service variables, you're all set
   - If not, check the Redis service's **Variables** tab and copy it manually

7. **Set Environment Variables**:
   - Go to your **backend service** → **Variables** tab
   - Add these variables (Railway may have already added `REDIS_URL`):
     ```
     OPENAI_API_KEY=sk-...
     STORAGE_TYPE=s3
     AWS_ACCESS_KEY_ID=...
     AWS_SECRET_ACCESS_KEY=...
     AWS_S3_BUCKET=style-inspo-wardrobe
     ```
   - **Note**: `REDIS_URL` should already be there if Railway auto-configured it
   - **For testing without S3**, you can use:
     ```
     STORAGE_TYPE=local
     ```
     (But images won't persist across deployments)

8. **Add Worker Process** (for background jobs):
   - **At project level**, click **"+ Create"** or **"New"** button
   - Type "service" in the search box
   - **Select "GitHub Repo"** (preferred) or "Empty Service"
   
   **Option A: GitHub Repo (Recommended)**
   - Select **"GitHub Repo"**
   - Choose `pcwmi/style-inspo-api` again
   - Railway will create a new service from the same repo
   - **Configure the worker service:**
     - Click on the new service
     - Go to **Settings** tab
     - Set **Root Directory**: `backend`
     - Scroll to **Deploy** section
     - Set **Start Command**: `rq worker outfits analysis --url $REDIS_URL`
     - Save
   - **Add environment variables** to worker service:
     - Go to **Variables** tab
     - Add `REDIS_URL` (should auto-populate) and `OPENAI_API_KEY`
   
   **Option B: Empty Service** (if GitHub Repo not available)
   - Select **"Empty Service"**
   - You'll need to configure it manually (more complex)
   - Better to use GitHub Repo option if possible

9. **Get Backend URL**:
   - Click on your **"style-inspo-api"** service (the one with GitHub icon)
   - Look for the **"Settings"** tab
   - Scroll down to **"Networking"** or **"Domains"** section
   - You'll see a **"Generate Domain"** button or an existing domain
   - Click **"Generate Domain"** if you don't see one
   - Railway will create a URL like: `https://style-inspo-api-production.up.railway.app`
   - **OR** check the service's **"Deployments"** tab - the URL might be shown there
   - Copy this URL - you'll need it for the frontend!

## Step 2: Deploy Frontend to Vercel

1. **Go to Vercel**: https://vercel.com
2. **Sign up/Login** (can use GitHub to sign in)
3. **Add New Project**
4. **Import**: `pcwmi/style-inspo-api`
5. **Configure**:
   - Framework Preset: **Next.js** (auto-detected)
   - Root Directory: `frontend` ⚠️ **IMPORTANT!**
   - Build Command: `npm run build` (default)
   - Output Directory: `.next` (default)

6. **Set Environment Variable**:
   - Go to **Environment Variables**
   - Add:
     ```
     NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app
     ```
   - Replace `your-railway-url` with your actual Railway backend URL from Step 1

7. **Deploy**:
   - Click **"Deploy"**
   - Vercel will build and deploy automatically
   - You'll get a URL like: `https://style-inspo-api.vercel.app`

## Step 3: Test Everything

1. **Backend Health Check**:
   - Visit: `https://your-railway-url.railway.app/health`
   - Should return: `{"status":"healthy","version":"1.0.0"}`

2. **Frontend**:
   - Visit your Vercel URL
   - Try: `https://your-vercel-url.vercel.app?user=test`
   - Should see the dashboard

3. **Test Full Flow**:
   - Upload a wardrobe item
   - Generate outfits
   - Save/dislike outfits

## Troubleshooting

### Backend Issues

**"Worker not processing jobs"**
- Make sure you added the worker service in Railway
- Check worker logs in Railway dashboard
- Verify Redis URL is correct

**"Redis connection failed"**
- Check Redis service is running in Railway
- Verify `REDIS_URL` environment variable is set correctly

### Frontend Issues

**"API calls failing"**
- Check `NEXT_PUBLIC_API_URL` is set correctly
- Verify backend is running (check `/health` endpoint)
- Check browser console for CORS errors

**"Build fails"**
- Check Vercel build logs
- Make sure root directory is set to `frontend/`
- Verify all dependencies are in `package.json`

## Next Steps

Once deployed:
1. Test on mobile device
2. Set up custom domains (optional)
3. Configure error tracking (Sentry, etc.)
4. Set up monitoring

You're all set! 🎉

