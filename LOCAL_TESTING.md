# Local Testing Guide

This guide will help you run the Style Inspo application locally for testing.

## Prerequisites

1. **Python 3.8+** (check with `python --version`)
2. **Node.js 18+** (check with `node --version`)
3. **Redis** (for background jobs)
4. **OpenAI API Key** (for outfit generation and image analysis)

## Quick Start

### 1. Start Redis

Redis is required for background job processing (outfit generation, image analysis).

**Option A: Using Homebrew (macOS)**
```bash
brew install redis
brew services start redis
# Or run manually: redis-server
```

**Option B: Using Docker**
```bash
docker run -d -p 6379:6379 --name redis redis
```

**Option C: Check if Redis is running**
```bash
redis-cli ping
# Should return: PONG
```

### 2. Set Up Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (if not already created)
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (if it doesn't exist)
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
REDIS_URL=redis://localhost:6379/0
STORAGE_TYPE=local
EOF

# Start the FastAPI server
uvicorn main:app --reload --port 8000
```

The API will be available at: **http://localhost:8000**

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 3. Start Background Worker (Required!)

**In a NEW terminal window:**

```bash
cd backend
source venv/bin/activate  # Activate virtual environment

# Start RQ worker to process background jobs
rq worker outfits analysis --url redis://localhost:6379/0
```

**Important:** The worker must be running for:
- Outfit generation (takes 20-30 seconds)
- Image analysis after upload

You'll see job processing logs in this terminal.

### 4. Set Up Frontend

**In a NEW terminal window:**

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Create .env.local file for API URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start Next.js dev server
npm run dev
```

The frontend will be available at: **http://localhost:3000**

## Testing the Full Flow

### 1. Open the App
Navigate to: http://localhost:3000?user=test

### 2. Upload a Wardrobe Item
- Click "Manage Closet" or go to `/upload?user=test`
- Upload a photo of clothing
- Wait for analysis (check worker terminal for progress)

### 3. Generate Outfits
- Go to "What should I wear today?" (`/occasion?user=test`)
- Select occasions and weather
- Click "Create Outfits"
- You'll be redirected to `/reveal?user=test&job={job_id}`
- The page will poll for completion (20-30 seconds)
- Check worker terminal to see generation progress

### 4. Save/Dislike Outfits
- On the reveal page, click "Save Outfit" or "👎"
- Provide feedback
- Check saved/disliked pages

## Troubleshooting

### Redis Connection Error
```
Error: Error 111 connecting to localhost:6379. Connection refused.
```

**Solution:** Make sure Redis is running:
```bash
redis-cli ping  # Should return PONG
# If not, start Redis (see step 1)
```

### Worker Not Processing Jobs
- Make sure the worker terminal is running: `rq worker outfits analysis --url redis://localhost:6379/0`
- Check Redis is running: `redis-cli ping`
- Check job queue: `rq info --url redis://localhost:6379/0`

### API Connection Error (Frontend)
- Make sure backend is running on port 8000
- Check `.env.local` has: `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Restart Next.js dev server after changing `.env.local`

### CORS Errors
- Backend is configured to allow all origins in development
- If you see CORS errors, check that `allow_origins=["*"]` is set in `backend/main.py`

### Outfit Generation Fails
- Check OpenAI API key is set in `backend/.env`
- Check worker terminal for error messages
- Verify user profile exists (may need to complete onboarding in original Streamlit app first)

## Environment Variables

### Backend (`backend/.env`)
```bash
OPENAI_API_KEY=sk-...              # Required for outfit generation
REDIS_URL=redis://localhost:6379/0  # Required for background jobs
STORAGE_TYPE=local                  # "local" or "s3"
AWS_ACCESS_KEY_ID=...              # Optional (for S3 storage)
AWS_SECRET_ACCESS_KEY=...         # Optional (for S3 storage)
AWS_S3_BUCKET=...                 # Optional (for S3 storage)
RUNWAY_API_KEY=...                 # Optional (for outfit visualization)
```

### Frontend (`frontend/.env.local`)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Testing Without Redis (Limited)

If you want to test the UI without Redis:
- **Uploads will fail** (requires analysis worker)
- **Outfit generation will fail** (requires generation worker)
- **You can still browse** saved/disliked outfits if they exist

## Checking Everything is Running

Open 4 terminal windows:

1. **Terminal 1 - Redis:**
   ```bash
   redis-server
   ```

2. **Terminal 2 - Backend API:**
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn main:app --reload --port 8000
   ```

3. **Terminal 3 - Background Worker:**
   ```bash
   cd backend
   source venv/bin/activate
   rq worker outfits analysis --url redis://localhost:6379/0
   ```

4. **Terminal 4 - Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

## Quick Health Checks

```bash
# Check Redis
redis-cli ping

# Check Backend API
curl http://localhost:8000/health

# Check Frontend
curl http://localhost:3000

# Check Worker (should show queues)
rq info --url redis://localhost:6379/0
```

## Next Steps

Once everything is running:
1. Test the full user flow
2. Check mobile responsiveness (open on phone or use browser dev tools)
3. Test error handling (disconnect Redis, invalid API keys, etc.)
4. Review the polished mobile UI

Happy testing! 🎨

