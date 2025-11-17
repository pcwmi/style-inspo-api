# GitHub Repository Setup Guide

Follow these steps to create and push the new `style-inspo-api` repository to GitHub.

## Step 1: Initialize Git (if not already done)

```bash
cd /Users/peichin/Projects/style-inspo-api

# Initialize git repository
git init

# Check what will be committed
git status
```

## Step 2: Create Initial Commit

```bash
# Add all files (respects .gitignore)
git add .

# Create initial commit
git commit -m "Initial commit: FastAPI + Next.js migration

- FastAPI backend with RQ background jobs
- Next.js frontend with mobile-first design
- Full feature parity with Streamlit app
- Editorial magazine design system (DM Sans, Libre Baskerville)
- Mobile-optimized UX with safe-area support"
```

## Step 3: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `style-inspo-api`
3. Description: `FastAPI + Next.js migration of Style Inspo - AI-powered personal styling assistant`
4. Visibility: **Private** (recommended) or Public
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

## Step 4: Connect and Push

After creating the repo, GitHub will show you commands. Use these:

```bash
# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/style-inspo-api.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

## Step 5: Verify

1. Go to https://github.com/YOUR_USERNAME/style-inspo-api
2. Verify all files are there
3. Check that `venv/`, `node_modules/`, and `wardrobe_photos/` are NOT included (they're in .gitignore)

## What Gets Committed

✅ **Included:**
- All source code (backend/, frontend/)
- Configuration files (package.json, requirements.txt, etc.)
- Documentation (README.md, DEPLOYMENT.md, etc.)
- .gitignore

❌ **Excluded (via .gitignore):**
- `backend/venv/` - Python virtual environment
- `frontend/node_modules/` - Node dependencies
- `backend/wardrobe_photos/` - Local user data
- `.env` files - Environment variables
- `__pycache__/` - Python cache
- `.next/` - Next.js build output

## Next Steps After Pushing

1. **Deploy to Railway:**
   - Connect GitHub repo `style-inspo-api`
   - Set root directory to `backend/`
   - Configure environment variables

2. **Deploy to Vercel:**
   - Connect GitHub repo `style-inspo-api`
   - Set root directory to `frontend/`
   - Set `NEXT_PUBLIC_API_URL` environment variable

See `DEPLOYMENT.md` for detailed deployment instructions.

