# Style Inspo API Backend

FastAPI backend for Style Inspo - AI-powered personal styling assistant.

## Setup

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
- `OPENAI_API_KEY` - OpenAI API key for GPT-4o
- `AWS_ACCESS_KEY_ID` - AWS credentials for S3
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `S3_BUCKET_NAME` - S3 bucket name (or `AWS_S3_BUCKET` as fallback)
- `REDIS_URL` - Redis connection URL (for job queue)

Optional:
- `RUNWAY_API_KEY` - For outfit visualization
- `STORAGE_TYPE` - "s3" or "local" (default: "local")

### 3. Run Redis (for background jobs)

**Local development:**
```bash
# Install Redis (macOS)
brew install redis
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis
```

**Production:** Use Upstash or Railway Redis

### 4. Run the API Server

```bash
# Development
uvicorn main:app --reload --port 8000

# Or
python main.py
```

### 5. Run Background Workers

In a separate terminal:

```bash
# Activate virtual environment first
source venv/bin/activate

# Run RQ worker
rq worker outfits analysis --url $REDIS_URL
```

## API Endpoints

### Health Check
- `GET /` - Basic health check
- `GET /health` - Detailed health status

### Wardrobe
- `GET /api/wardrobe/{user_id}` - Get user's wardrobe
- `POST /api/wardrobe/{user_id}/upload` - Upload new item (returns job_id)
- `GET /api/wardrobe/{user_id}/items/{item_id}` - Get single item
- `DELETE /api/wardrobe/{user_id}/items/{item_id}` - Delete item

### Outfits
- `POST /api/outfits/generate` - Generate outfits (returns job_id)
- `POST /api/outfits/save` - Save outfit to favorites
- `POST /api/outfits/dislike` - Dislike outfit with feedback

### Jobs
- `GET /api/jobs/{job_id}` - Poll job status

### User Profile
- `GET /api/users/{user_id}/profile` - Get user profile
- `POST /api/users/{user_id}/profile` - Update user profile

## Testing

### Manual Testing with curl

```bash
# Health check
curl http://localhost:8000/

# Get wardrobe
curl http://localhost:8000/api/wardrobe/peichin

# Generate outfits
curl -X POST http://localhost:8000/api/outfits/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "peichin",
    "occasions": ["Business meeting", "Coffee"],
    "mode": "occasion"
  }'

# Check job status
curl http://localhost:8000/api/jobs/{job_id}
```

### Interactive API Docs

FastAPI provides automatic interactive documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
backend/
├── main.py              # FastAPI app entry point
├── api/                 # API route handlers
│   ├── wardrobe.py     # Wardrobe CRUD endpoints
│   ├── outfits.py      # Outfit generation endpoints
│   ├── jobs.py         # Job status endpoints
│   └── user.py         # User profile endpoints
├── services/           # Business logic (reused from Streamlit)
│   ├── style_engine.py
│   ├── wardrobe_manager.py
│   ├── storage_manager.py
│   └── ...
├── workers/            # Background job workers
│   └── outfit_worker.py
├── models/             # Pydantic schemas
│   └── schemas.py
└── core/               # Configuration
    ├── config.py
    └── redis.py
```

## Deployment

### Railway

1. Connect GitHub repo to Railway
2. Set environment variables in Railway dashboard
3. Railway will auto-detect `Procfile` and deploy:
   - `web` process: FastAPI server
   - `worker` process: RQ worker

### Environment Variables for Production

Make sure to set all required variables in Railway:
- `OPENAI_API_KEY`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_S3_BUCKET`
- `REDIS_URL` (Upstash or Railway Redis)
- `STORAGE_TYPE=s3`

## Background Jobs

The API uses RQ (Redis Queue) for background jobs:

1. **Outfit Generation** (`outfits` queue)
   - Long-running OpenAI API calls (20-30s)
   - Returns job_id immediately
   - Frontend polls `/api/jobs/{job_id}` for status

2. **Image Analysis** (`analysis` queue)
   - OpenAI Vision API for clothing analysis
   - Processes uploaded images
   - Returns analysis results

Workers must be running separately:
```bash
rq worker outfits analysis --url $REDIS_URL
```

# Force redeploy Fri Dec 19 09:29:38 PST 2025
