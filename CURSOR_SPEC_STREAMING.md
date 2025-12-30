# Task: Implement Real Streaming for Outfit Generation

## Context
We have built the backend streaming infrastructure:
- `chain_of_thought_streaming_v1` prompt outputs JSON per outfit (not batched)
- `StyleGenerationEngine.generate_outfit_combinations_stream()` yields outfits as they arrive
- Test validated: First outfit at ~7s vs ~16s (9s faster)

Now we need to wire it up to the API and frontend.

## What to Implement

### 1. Backend: Add SSE streaming endpoint

**File:** `backend/api/outfits.py`

Add this endpoint (adapt from existing patterns in `api/jobs.py` for SSE):

```python
from fastapi.responses import StreamingResponse
import asyncio

@router.get("/outfits/generate/stream")
async def generate_outfits_stream(
    user_id: str,
    mode: str = "occasion",
    occasions: str = None,
    anchor_items: str = None,
    weather_condition: str = None,
    temperature_range: str = None,
):
    """
    Stream outfit generation via SSE.
    Returns outfits one-by-one as they're generated (~7s, ~14s, ~21s).
    """
    async def event_generator():
        try:
            # Import here to avoid circular imports
            from services.style_engine import StyleGenerationEngine
            from services.wardrobe_manager import WardrobeManager
            from services.user_profile_manager import UserProfileManager
            from core.config import get_settings

            # Setup - similar to workers/outfit_worker.py
            wardrobe_manager = WardrobeManager(user_id=user_id)
            profile_manager = UserProfileManager(user_id=user_id)

            # Get profile (create default if needed)
            raw_profile = profile_manager.get_profile(user_id)
            if not raw_profile or not raw_profile.get("style_words"):
                raw_profile = {"style_words": ["versatile", "confident", "comfortable"]}

            user_profile = {
                "three_words": {
                    "current": raw_profile["style_words"][0],
                    "aspirational": raw_profile["style_words"][1],
                    "feeling": raw_profile["style_words"][2]
                }
            }

            # Load wardrobe
            all_items = wardrobe_manager.get_wardrobe_items("all")

            # Determine available items and anchor items based on mode
            if mode == "complete" and anchor_items:
                anchor_item_ids = [id.strip() for id in anchor_items.split(",")]
                anchor_item_objects = [item for item in all_items if item.get("id") in anchor_item_ids]
                available_items = [item for item in all_items if item.get("id") not in anchor_item_ids]
                styling_challenges = anchor_item_objects
            else:
                available_items = all_items
                styling_challenges = []

            # Parse occasions
            occasion_str = ", ".join([o.strip() for o in occasions.split(",")]) if occasions else None

            # Create engine with streaming prompt
            engine = StyleGenerationEngine(
                model="gpt-4o",
                temperature=0.7,
                max_tokens=6000,
                prompt_version="chain_of_thought_streaming_v1"
            )

            # Stream outfits
            outfit_num = 0
            for outfit in engine.generate_outfit_combinations_stream(
                user_profile=user_profile,
                available_items=available_items,
                styling_challenges=styling_challenges,
                occasion=occasion_str,
                weather_condition=weather_condition,
                temperature_range=temperature_range
            ):
                outfit_num += 1

                # Enrich outfit with full item data (images, etc.)
                enriched_items = []
                for item_name in outfit.get("items", []):
                    # Find matching item in wardrobe
                    matched = None
                    for item in all_items:
                        if item.get("styling_details", {}).get("name", "").lower() == item_name.lower():
                            matched = item
                            break

                    if matched:
                        enriched_items.append({
                            "id": matched.get("id"),
                            "name": matched.get("styling_details", {}).get("name"),
                            "category": matched.get("styling_details", {}).get("category"),
                            "image_path": matched.get("system_metadata", {}).get("image_path")
                        })
                    else:
                        enriched_items.append({"name": item_name, "category": "unknown"})

                enriched_outfit = {
                    "items": enriched_items,
                    "styling_notes": outfit.get("styling_notes", ""),
                    "why_it_works": outfit.get("why_it_works", ""),
                    "confidence_level": "medium",
                    "vibe_keywords": []
                }

                yield f"event: outfit\ndata: {json.dumps({'outfit_number': outfit_num, 'outfit': enriched_outfit})}\n\n"
                await asyncio.sleep(0)  # Allow event loop to process

            yield f"event: complete\ndata: {json.dumps({'total': outfit_num})}\n\n"

        except Exception as e:
            logger.error(f"Streaming error for {user_id}: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

### 2. Frontend: Update occasion page

**File:** `frontend/app/occasion/page.tsx`

Find the `handleGenerate` function (around line 34). Change from job-based to streaming:

```typescript
// OLD: Creates job, redirects with job_id
const { job_id } = await api.generateOutfits({...})
router.push(`/reveal?user=${user}&job=${job_id}`)

// NEW: Redirect with streaming params
const params = new URLSearchParams({
    user: user,
    mode: 'occasion',
    occasions: selectedOccasions.join(','),
    stream: 'true'
})
if (weatherCondition) params.append('weather_condition', weatherCondition)
if (temperatureRange) params.append('temperature_range', temperatureRange)
router.push(`/reveal?${params.toString()}`)
```

### 3. Frontend: Update complete page

**File:** `frontend/app/complete/page.tsx`

Similar change - find the generate function and change to streaming params:

```typescript
// NEW: Redirect with streaming params
const params = new URLSearchParams({
    user: user,
    mode: 'complete',
    anchor_items: selectedItems.join(','),
    stream: 'true'
})
router.push(`/reveal?${params.toString()}`)
```

### 4. Frontend: Update consider-buying page

**File:** `frontend/app/consider-buying/page.tsx`

Find `handleGenerateOutfits` (around line 220). Change to streaming:

```typescript
// OLD: POST to generate, get job_id, redirect
const res = await fetch(`${API_URL}/api/consider-buying/generate-outfits`, {...})
router.push(`/reveal?user=${user}&job=${jobId}${debugParam}`)

// NEW: Redirect with streaming params (consider-buying item is the anchor)
const params = new URLSearchParams({
    user: user,
    mode: 'complete',
    anchor_items: itemId,  // The consider-buying item ID
    stream: 'true'
})
if (debugMode) params.append('debug', 'true')
router.push(`/reveal?${params.toString()}`)
```

### 5. Frontend: Update reveal page for streaming

**File:** `frontend/app/reveal/page.tsx`

Major changes needed. The page needs to detect streaming mode and handle it differently:

```typescript
// Add to the existing searchParams extraction (around line 14-18)
const streamMode = searchParams.get('stream') === 'true'
const mode = searchParams.get('mode') || 'occasion'
const occasions = searchParams.get('occasions') || ''
const anchorItems = searchParams.get('anchor_items') || ''
const weatherCondition = searchParams.get('weather_condition') || ''
const temperatureRange = searchParams.get('temperature_range') || ''

// Replace the useEffect (lines 29-158) with logic that handles both modes:
useEffect(() => {
    let eventSource: EventSource | null = null
    let pollInterval: NodeJS.Timeout | null = null

    if (streamMode) {
        // NEW: Direct streaming mode
        const params = new URLSearchParams({
            user_id: user,
            mode: mode,
        })
        if (occasions) params.append('occasions', occasions)
        if (anchorItems) params.append('anchor_items', anchorItems)
        if (weatherCondition) params.append('weather_condition', weatherCondition)
        if (temperatureRange) params.append('temperature_range', temperatureRange)

        try {
            eventSource = new EventSource(`${API_URL}/api/outfits/generate/stream?${params.toString()}`)

            eventSource.addEventListener('outfit', (e) => {
                const data = JSON.parse(e.data)
                // APPEND outfit to array (not replace)
                setOutfits(prev => [...prev, data.outfit])
                setCurrentOutfit(data.outfit_number)
                setStreamedContent(`Outfit ${data.outfit_number} ready!`)
            })

            eventSource.addEventListener('complete', (e) => {
                const data = JSON.parse(e.data)
                setStatus('complete')
                eventSource?.close()
            })

            eventSource.addEventListener('error', (e: Event) => {
                console.error('Streaming error, falling back to batch mode')
                eventSource?.close()
                // TODO: Implement fallback to batch mode
                setStatus('error')
                setError('Streaming failed. Please try again.')
            })

        } catch (err) {
            console.error('SSE not supported', err)
            setStatus('error')
            setError('Streaming not supported in this browser.')
        }
    } else if (jobId) {
        // EXISTING: Job-based polling mode (keep existing code)
        // ... existing startSSEStreaming() and startPolling() code ...
    } else {
        setStatus('error')
        setError('No job ID or streaming params provided')
    }

    return () => {
        eventSource?.close()
        if (pollInterval) clearInterval(pollInterval)
    }
}, [streamMode, jobId, mode, occasions, anchorItems, weatherCondition, temperatureRange, user, debugMode])
```

Also update the loading UI to show outfits as they arrive (the current UI waits for all outfits):

In the loading state section (around line 160-198), check if we have partial outfits:
```typescript
if (status === 'loading') {
    return (
        <div className="min-h-screen bg-bone page-container">
            <div className="max-w-2xl mx-auto px-4 py-4 md:py-8">
                {/* Show any outfits we've received so far */}
                {outfits.length > 0 && (
                    <>
                        <h1 className="text-2xl md:text-3xl font-bold mb-5 md:mb-8">
                            Here's what could work for your day
                        </h1>
                        {outfits.map((outfit, idx) => (
                            <OutfitCard
                                key={idx}
                                outfit={outfit}
                                user={user}
                                index={idx + 1}
                            />
                        ))}
                    </>
                )}

                {/* Show loading indicator for remaining outfits */}
                <div className="text-center px-4 py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-4 border-sand border-t-terracotta mx-auto mb-4"></div>
                    <p className="text-ink text-base font-medium">
                        {outfits.length === 0
                            ? 'Creating your first outfit...'
                            : `Creating outfit ${outfits.length + 1} of 3...`}
                    </p>
                </div>
            </div>
        </div>
    )
}
```

## Testing Plan

### Cursor Can Verify (Automated):
1. **Syntax check**: Ensure all files have no TypeScript/Python errors
2. **Import check**: Verify all imports resolve correctly
3. **Build check**: `npm run build` in frontend should succeed

### Manual Testing Required:
1. **Start backend**: `cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000`
2. **Start frontend**: `cd frontend && npm run dev`
3. **Test occasion flow**:
   - Go to `http://localhost:3000/occasion?user=peichin`
   - Select occasions, click Generate
   - Verify reveal page shows outfits progressively (not all at once)
   - First outfit should appear around 7-10 seconds
4. **Test complete flow**:
   - Go to `http://localhost:3000/complete?user=peichin`
   - Select anchor items, click Generate
   - Verify streaming works
5. **Test consider-buying flow**:
   - Go to `http://localhost:3000/consider-buying?user=peichin`
   - Add an item, click "See How to Style It"
   - Verify streaming works
6. **Test fallback**: Open Network tab, block the streaming endpoint, verify error message appears

## Files Summary
| File | Lines Changed (approx) |
|------|----------------------|
| `backend/api/outfits.py` | +100 lines |
| `frontend/app/occasion/page.tsx` | ~10 lines |
| `frontend/app/complete/page.tsx` | ~10 lines |
| `frontend/app/consider-buying/page.tsx` | ~10 lines |
| `frontend/app/reveal/page.tsx` | ~80 lines |

## Important Notes
- Keep all existing job-based code as fallback
- The streaming endpoint bypasses RQ (Redis Queue) - this is intentional
- SSE requires proper CORS headers - backend already has CORS configured
- Test with `?debug=true` to see AI reasoning if needed
