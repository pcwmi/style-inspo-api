# Deployment Guide

This guide covers deploying the Style Inspo application to production.

## Architecture

- **Backend**: FastAPI on Railway
- **Frontend**: Next.js on Vercel
- **Redis**: Railway Redis or Upstash
- **Storage**: AWS S3 (or local for development)

## Backend Deployment (Railway)

### Prerequisites
- Railway account (https://railway.app)
- GitHub repository: `pcwmi/style-inspo-api` ✅ (Already created!)

### Steps

1. **Create New Project on Railway**
   - Go to Railway dashboard: https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose `pcwmi/style-inspo-api` repository
   - Railway will create a service automatically
   
2. **Set Root Directory** (⚠️ **CRITICAL!**):
   - Click on the **service** that was created
   - Go to the **Settings** tab
   - Scroll to **"Root Directory"** section
   - Enter: `backend` (without trailing slash)
   - Click **"Save"**
   - Railway will redeploy with the correct root directory

3. **Add Redis Service**
   - In Railway project, click "+ New"
   - Select "Redis"
   - Railway will provision Redis automatically
   - **Find the Redis URL**:
     - Click on the **Redis service** in your project
     - Go to the **Variables** tab
     - Look for `REDIS_URL` or `DATABASE_URL`
     - Click the **👁️ eye icon** to reveal the value
     - Copy the entire URL (format: `redis://default:password@host:port`)
     - **Alternative**: Check the **Connect** or **Info** tab in the Redis service

4. **Configure Environment Variables**
   - Go to your **backend service** → **Variables** tab
   - Railway may have already added `REDIS_URL` automatically (check first!)
   - Add these environment variables:

   **Required:**
   ```
   OPENAI_API_KEY=sk-...
   STORAGE_TYPE=s3
   AWS_ACCESS_KEY_ID=...
   AWS_SECRET_ACCESS_KEY=...
   AWS_S3_BUCKET=style-inspo-wardrobe
   ```

   **Optional:**
   ```
   RUNWAY_API_KEY=... (for outfit visualization)
   RUNWAY_MODEL_DESCRIPTOR=... (for outfit visualization)
   ```

   **Note**: If `REDIS_URL` is not automatically added, you'll need to:
   - Go to Redis service → Variables tab
   - Copy the `REDIS_URL` value
   - Add it to your backend service variables

5. **Deploy Backend**
   - Railway auto-detects `backend/Procfile` in the root directory
   - It will run:
     - `web`: FastAPI server (uvicorn)
     - `worker`: RQ worker (separate process - see step 6)
   - Railway will build and deploy automatically

6. **Add Worker Process** (for background jobs):
   - **At the project level** (not inside a service), click **"+ New"** button
   - Select **"GitHub Repo"** (or "Empty Service" if that's not available)
   - If "GitHub Repo": Select `pcwmi/style-inspo-api` again
   - **Configure the worker service:**
     - Click on the new service
     - Go to **Settings** tab
     - Set **Root Directory**: `backend`
     - Go to **Deploy** section (in Settings)
     - Set **Start Command**: `rq worker outfits analysis --url $REDIS_URL`
   - **Set Environment Variables** (same as backend):
     - Go to **Variables** tab
     - Add `REDIS_URL` (should auto-populate) and `OPENAI_API_KEY`
   - This service runs the background job worker separately from your API server

7. **Get Backend URL**
   - Railway provides a URL like: `https://style-inspo-api-production.up.railway.app`
   - Copy this URL for frontend configuration

### Backend Health Check
```bash
curl https://your-railway-url.railway.app/health
```

Should return: `{"status":"healthy","version":"1.0.0"}`

## Frontend Deployment (Vercel)

### Prerequisites
- Vercel account (https://vercel.com)
- GitHub repository: `pcwmi/style-inspo-api` ✅ (Already created!)

### Steps

1. **Import Project to Vercel**
   - Go to Vercel dashboard: https://vercel.com
   - Click "Add New Project"
   - Import `pcwmi/style-inspo-api` repository
   - **Important**: Set root directory to `frontend` (not root!)

2. **Configure Build Settings**
   - Framework Preset: Next.js
   - Root Directory: `frontend`
   - Build Command: `npm run build` (default)
   - Output Directory: `.next` (default)

3. **Set Environment Variables**
   In Vercel project settings, add:

   ```
   NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app
   ```

   **Important**: Use the Railway backend URL from step 5 above.

4. **Deploy**
   - Click "Deploy"
   - Vercel will build and deploy automatically
   - You'll get a URL like: `https://style-inspo-api.vercel.app`

### Frontend Environment Variables
- `NEXT_PUBLIC_API_URL`: Your Railway backend URL
- This is the only required variable for frontend

## Post-Deployment Checklist

### Backend
- [ ] Health check endpoint works: `/health`
- [ ] API docs accessible: `/docs`
- [ ] Redis connection working (check logs)
- [ ] RQ worker running (check Railway logs for "Listening on outfits, analysis")
- [ ] Environment variables set correctly

### Frontend
- [ ] Frontend loads at Vercel URL
- [ ] API calls work (check browser console)
- [ ] CORS configured correctly (backend allows Vercel origin)
- [ ] Images load correctly
- [ ] Mobile responsive

### Integration Testing
- [ ] Upload wardrobe item → Check worker processes it
- [ ] Generate outfits → Check job polling works
- [ ] Save/dislike outfits → Check persistence
- [ ] View saved/disliked pages → Check data loads

## CORS Configuration

The backend currently allows all origins (`allow_origins=["*"]`). For production, update `backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-vercel-app.vercel.app",
        "https://www.yourdomain.com"  # If using custom domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Custom Domains

### Backend (Railway)
- Railway provides free `.railway.app` domain
- Can add custom domain in Railway project settings

### Frontend (Vercel)
- Vercel provides free `.vercel.app` domain
- Can add custom domain in Vercel project settings
- Update `NEXT_PUBLIC_API_URL` if backend domain changes

## Monitoring

### Railway
- Check logs in Railway dashboard
- Monitor Redis usage
- Set up alerts for errors

### Vercel
- Check deployment logs
- Monitor function execution
- Set up error tracking (Sentry, etc.)

## Troubleshooting

### Backend Issues

**Redis Connection Failed**
- Check `REDIS_URL` is set correctly
- Verify Redis service is running in Railway
- Check network connectivity

**Worker Not Processing Jobs**
- Check Railway logs for worker process
- Verify worker is running: `rq worker outfits analysis`
- Check Redis connection

**API Returns 500 Errors**
- Check Railway logs for stack traces
- Verify environment variables are set
- Check OpenAI API key is valid

### Frontend Issues

**API Calls Fail**
- Check `NEXT_PUBLIC_API_URL` is correct
- Verify CORS is configured
- Check browser console for errors
- Verify backend is running

**Build Fails**
- Check Vercel build logs
- Verify all dependencies in `package.json`
- Check for TypeScript errors

## Rollback

### Railway
- Go to project → Deployments
- Click on previous deployment
- Click "Redeploy"

### Vercel
- Go to project → Deployments
- Find previous deployment
- Click "..." → "Promote to Production"

## Cost Estimates

### Railway
- Free tier: $5 credit/month
- Backend + Redis: ~$10-20/month (depending on usage)
- Worker process: Included in backend cost

### Vercel
- Free tier: Unlimited personal projects
- Hobby: $20/month (if needed for team features)
- Bandwidth: Generous free tier

### Total Estimated Cost
- **Development/Personal Use**: Free (within limits)
- **Production with moderate traffic**: ~$20-30/month

## Next Steps

1. Set up custom domains (optional)
2. Configure error tracking (Sentry, etc.)
3. Set up monitoring/analytics
4. Configure CDN for images (if using S3)
5. Set up CI/CD for automated deployments

