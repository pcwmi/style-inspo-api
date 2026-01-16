# Outfit Visualization Feature

## Overview

The outfit visualization feature generates AI-powered images of saved outfits using Runway ML Gen-4 Image API. Each user can set their own **user-level model descriptor** (e.g., "Asian woman, 5'4\", curly hair") to create relatable, personalized visualizations.

## Key Features

✅ **User-Level Model Descriptors** - Each user specifies their own relatable model characteristics
✅ **Permanent Storage** - Generated images are downloaded and stored permanently (S3 or local)
✅ **Async Job Processing** - Non-blocking API with RQ worker processing
✅ **Provider Abstraction** - Easy to swap visualization providers (Runway, Fashn.ai, etc.)

## Architecture

### Components

1. **User Profile** (`services/user_profile_manager.py`)
   - Stores `model_descriptor` field per user

2. **Runway Provider** (`services/visualization/providers/runway.py`)
   - Implements Runway ML Gen-4 Image API
   - Accepts user-level model descriptor as parameter
   - Generates temporary visualization URL (~24-48 hour expiration)

3. **Visualization Manager** (`services/visualization/visualization_manager.py`)
   - Orchestrates the full workflow:
     1. Fetch outfit + user profile
     2. Call Runway provider with user's descriptor
     3. Download from temporary URL
     4. Upload to permanent storage
     5. Update outfit record

4. **API Endpoint** (`api/outfits.py`)
   - `POST /api/outfits/{outfit_id}/visualize?user_id={user_id}`
   - Returns job_id for polling

5. **RQ Worker** (`workers/outfit_worker.py`)
   - `generate_visualization_job()` function
   - Processes visualization requests asynchronously

## API Usage

### 1. Set User's Model Descriptor

```bash
curl -X POST http://localhost:8000/api/users/peichin/profile \
  -H "Content-Type: application/json" \
  -d '{
    "model_descriptor": "Model: ~163 cm, ~150 lb, Asian woman, dark wavy chest-length hair"
  }'
```

### 2. Request Visualization

```bash
curl -X POST "http://localhost:8000/api/outfits/{outfit_id}/visualize?user_id=peichin"
```

**Response:**
```json
{
  "job_id": "abc-123-def",
  "status": "queued",
  "estimated_time": 40
}
```

### 3. Poll Job Status

```bash
curl http://localhost:8000/api/jobs/{job_id}
```

**When complete:**
```json
{
  "status": "complete",
  "progress": 100,
  "result": {
    "image_url": "wardrobe_photos/peichin/items/visualizations/{outfit_id}.jpg",
    "generation_time": 32.5,
    "provider": "Runway ML",
    "metadata": {
      "task_id": "...",
      "model": "gen4_image",
      "user_level_descriptor": true
    }
  }
}
```

## Setup

### 1. Environment Variables

Add to `.env`:

```env
# Runway ML API Key (required)
RUNWAY_API_KEY=your_runway_api_key_here

# Optional default model descriptor (user-level takes precedence)
RUNWAY_MODEL_DESCRIPTOR=""
```

### 2. Start RQ Worker

**On macOS:**
```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
source venv/bin/activate
rq worker visualization --with-scheduler
```

**On Linux:**
```bash
source venv/bin/activate
rq worker visualization --with-scheduler
```

### 3. Verify Setup

```bash
cd backend
source venv/bin/activate
python test_visualization_e2e.py
```

## Technical Details

### Generation Workflow

1. **Preparation** (2s)
   - Fetch outfit data (items, styling notes)
   - Fetch user's model descriptor
   - Encode garment images to base64

2. **AI Generation** (25-40s)
   - Submit to Runway Gen-4 Image API
   - Poll task status every 2s
   - Return temporary URL when complete

3. **Permanent Storage** (2-5s)
   - Download from temporary Runway URL
   - Upload to S3 or local storage
   - Update outfit with permanent URL

**Total Time:** ~30-50 seconds per visualization

### Storage Paths

- **S3**: `s3://{bucket}/peichin/items/visualizations/{outfit_id}.jpg`
- **Local**: `wardrobe_photos/peichin/items/visualizations/{outfit_id}.jpg`

### Cost

- **Runway ML Gen-4 Image**: $0.08 per image generation (8 credits at $0.01/credit)
- **S3 Storage**: ~$0.023/GB/month
- **Data Transfer**: Free (within same region)

## Provider Swapping

To add a new visualization provider (e.g., Fashn.ai):

1. Create `backend/services/visualization/providers/fashn.py`
2. Implement `ImageGenerationProvider` interface
3. Add to `VisualizationProviderFactory.create_provider()`
4. Update `.env` with provider API key

Example:

```python
# In factory.py
if provider_name == "fashn":
    from .providers.fashn import FashnProvider
    return FashnProvider()
```

## Known Issues

### ~~Visualization Update Timeout/Deadlock (FIXED)~~

~~Previously, `update_outfit_visualization()` had nested non-reentrant lock acquisition causing guaranteed deadlock. Image was generated and uploaded to S3 successfully, but outfit record never got updated.~~

**Fixed (Jan 2026):** Removed outer lock to match safe pattern used in other managers. Feature now functional.

### ~~S3 Storage Fallback (FIXED)~~

~~Previously, VisualizationManager didn't read STORAGE_TYPE env var, causing fallback to local storage.~~

**Fixed (Jan 2026):** Now reads `os.getenv("STORAGE_TYPE", "local")` and passes to StorageManager.

### macOS Fork Safety

RQ workers may crash on macOS with:
```
objc[PID]: +[NSMutableString initialize] may have been in progress when fork() was called
```

**Solution:** Export environment variable before starting worker:
```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```

## Testing

### Unit Tests

```bash
# Test Runway provider signature
python test_runway_descriptor.py

# Test VisualizationManager
python test_visualization_manager.py
```

### End-to-End Test

```bash
# Requires:
# - RQ worker running
# - Valid RUNWAY_API_KEY
# - Saved outfit for test user

python test_visualization_e2e.py
```

## Future Enhancements

- [ ] Regenerate visualization (update existing)
- [ ] Delete visualization
- [ ] Multiple visualizations per outfit (different angles, settings)
- [ ] Video generation (Runway Gen-4 Turbo)
- [ ] Cost tracking per user
- [ ] Batch visualization (multiple outfits)

## References

- [Runway Gen-4 Image API Docs](https://docs.dev.runwayml.com)
- [RQ Documentation](https://python-rq.org/)
- [Implementation Plan](/Users/peichin/.claude/plans/sorted-greeting-sky.md)
