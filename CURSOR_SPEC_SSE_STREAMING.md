# SSE Streaming Implementation Spec

## Overview
Add Server-Sent Events (SSE) streaming to outfit generation to improve perceived latency. Users will see progressive output ("Creating outfit 1 of 3...") instead of waiting 20-30 seconds with a blank screen.

**Current Experience:**
- User clicks "Generate Outfits" → redirects to `/reveal` page
- Loading spinner for 20-30 seconds (no progress feedback)
- All 3 outfits appear at once when complete

**New Experience:**
- User clicks "Generate Outfits" → redirects to `/reveal` page
- Sees "Creating outfit 1 of 3..." within 1-2 seconds
- Sees "Creating outfit 2 of 3..." as generation progresses
- Sees "Creating outfit 3 of 3..."
- Outfits display as they complete (or all at once when done)

**Key Benefit:** Same total time (~25-30s) but feels much faster due to immediate feedback

---

## Architecture Decision Summary

Based on tech-lead review, we're implementing:
- **Approach:** SSE (Server-Sent Events) for real-time streaming
- **Pattern:** Job queue + SSE (all 3 flows use same pattern now)
- **Progress detection:** Backend sends explicit events (not text parsing)
- **Error handling:** Show error + partial results if available
- **Debug mode:** Works with streaming (shows reasoning when `?debug=true`)

---

## Backend Changes

### File 1: `backend/services/ai/providers/openai.py`

**Goal:** Add streaming support to OpenAI provider

**Location:** Add new method after existing `generate_text()` method (around line 140)

**Implementation:**
```python
def generate_text_stream(
    self,
    prompt: str,
    system_message: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> Iterator[str]:
    """
    Stream text generation from OpenAI.

    Yields:
        str: Text chunks as they're generated
    """
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    stream = self.client.chat.completions.create(
        model=self.config.model,
        messages=messages,
        temperature=temperature or self.config.temperature,
        max_tokens=max_tokens or self.config.max_tokens,
        stream=True  # Enable streaming
    )

    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content
```

**Add import at top:**
```python
from typing import Dict, Optional, Iterator
```

---

### File 2: `backend/workers/outfit_worker.py`

**Goal:** Store partial streaming output in job.meta for SSE endpoint to read

**Changes needed:**

**1. Modify `generate_outfits_job()` to track progress during generation**

Find where `engine.generate_outfit_combinations()` is called (around lines 222-241 for occasion mode, 278-295 for complete mode).

**Add streaming progress tracking:**

```python
# Inside generate_outfits_job, before calling generate_outfit_combinations

# Track which outfit we're generating (for progress events)
if job:
    job.meta['current_outfit'] = 1
    job.meta['total_outfits'] = 3
    job.meta['partial_reasoning'] = ""
    job.save_meta()

# Existing generation call
if include_reasoning:
    combinations, raw_reasoning = engine.generate_outfit_combinations(...)

    # Update job.meta with partial reasoning as we go
    # (Note: OpenAI doesn't support true mid-generation updates without streaming)
    # For now, just update progress markers
    if job:
        job.meta['current_outfit'] = 2  # Update after first outfit conceptually
        job.save_meta()
else:
    combinations = engine.generate_outfit_combinations(...)
```

**Note:** True streaming during generation requires using `generate_text_stream()` in StyleEngine. For MVP, we'll emit progress events at job milestones rather than during AI generation.

**2. Add progress milestones:**

Update progress tracking to emit at key points:

```python
# At key milestones in generate_outfits_job:

# After loading wardrobe (line ~214)
if job:
    job.meta['progress'] = 30
    job.meta['status_message'] = "Wardrobe loaded, starting generation..."
    job.save_meta()

# Before starting generation (line ~220)
if job:
    job.meta['progress'] = 40
    job.meta['status_message'] = "Creating outfit 1 of 3..."
    job.meta['current_outfit'] = 1
    job.save_meta()

# After generation completes (line ~299)
if job:
    job.meta['progress'] = 90
    job.meta['status_message'] = "Finalizing outfits..."
    job.save_meta()

# Before returning (line ~337)
if job:
    job.meta['progress'] = 100
    job.meta['status_message'] = "Complete!"
    job.save_meta()
```

**Same changes for `generate_consider_buying_job()`** - add progress milestones.

---

### File 3: `backend/api/jobs.py`

**Goal:** Add SSE streaming endpoint for job updates

**Location:** Add new endpoint after existing `/jobs/{job_id}` endpoint

**Implementation:**
```python
from fastapi.responses import StreamingResponse
import asyncio
import json

@router.get("/jobs/{job_id}/stream")
async def stream_job_updates(job_id: str):
    """
    Stream job updates via Server-Sent Events (SSE).

    Sends events:
    - progress: {progress: number, message: string}
    - outfit: {outfit_number: number} (when outfit completes)
    - complete: {result: object} (when job finishes)
    - error: {error: string} (if job fails)
    """

    async def event_generator():
        from core.redis import get_redis_connection
        from rq.job import Job

        redis_conn = get_redis_connection()

        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': 'Job not found'})}\n\n"
            return

        last_progress = -1
        last_outfit = 0

        # Poll job status every 500ms
        while True:
            try:
                job.refresh()
                status = job.get_status()

                # Send progress updates
                meta = job.meta or {}
                current_progress = meta.get('progress', 0)
                current_outfit = meta.get('current_outfit', 0)
                status_message = meta.get('status_message', '')

                # Emit progress event if changed
                if current_progress > last_progress:
                    progress_data = {
                        'progress': current_progress,
                        'message': status_message,
                        'current_outfit': current_outfit
                    }
                    yield f"event: progress\ndata: {json.dumps(progress_data)}\n\n"
                    last_progress = current_progress

                # Emit outfit event if we moved to next outfit
                if current_outfit > last_outfit and current_outfit <= 3:
                    outfit_data = {'outfit_number': current_outfit}
                    yield f"event: outfit\ndata: {json.dumps(outfit_data)}\n\n"
                    last_outfit = current_outfit

                # Check if job is complete
                if status == 'finished':
                    result = job.result
                    yield f"event: complete\ndata: {json.dumps(result)}\n\n"
                    break

                elif status == 'failed':
                    error_message = str(job.exc_info) if job.exc_info else "Job failed"
                    yield f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
                    break

                # Wait before next poll
                await asyncio.sleep(0.5)

            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
```

---

## Frontend Changes

### File 4: `frontend/app/reveal/page.tsx`

**Goal:** Replace polling with SSE streaming

**Current implementation:** Polls `/api/jobs/{job_id}` every 2 seconds

**New implementation:** Use EventSource to stream updates

**Changes:**

**1. Add state for streaming:**

```typescript
const [streamedContent, setStreamedContent] = useState<string>('')
const [currentOutfit, setCurrentOutfit] = useState<number>(0)
```

**2. Replace polling useEffect with SSE streaming:**

Find the existing polling `useEffect` (lines 23-91) and replace with:

```typescript
useEffect(() => {
  if (!jobId) return

  let eventSource: EventSource | null = null
  let pollInterval: NodeJS.Timeout | null = null

  const startSSEStreaming = () => {
    try {
      eventSource = new EventSource(`${API_URL}/api/jobs/${jobId}/stream`)

      eventSource.addEventListener('progress', (e) => {
        const data = JSON.parse(e.data)
        setProgress(data.progress)
        setCurrentOutfit(data.current_outfit || 0)

        // Update status message
        if (data.message) {
          setStreamedContent(data.message)
        }
      })

      eventSource.addEventListener('outfit', (e) => {
        const data = JSON.parse(e.data)
        console.log(`Outfit ${data.outfit_number} being generated...`)
        setCurrentOutfit(data.outfit_number)
      })

      eventSource.addEventListener('complete', (e) => {
        const result = JSON.parse(e.data)
        const outfitsArray = result.outfits || []
        setOutfits(outfitsArray)

        // Extract reasoning if debug mode
        if (debugMode && result.reasoning) {
          setReasoning(result.reasoning)
        }

        setStatus('complete')
        eventSource?.close()
      })

      eventSource.addEventListener('error', (e) => {
        console.warn('SSE error, falling back to polling', e)
        eventSource?.close()

        // Fall back to polling
        startPolling()
      })

    } catch (err) {
      console.warn('SSE not supported, using polling', err)
      startPolling()
    }
  }

  const startPolling = () => {
    // Existing polling logic as fallback
    let pollCounter = 0
    const MAX_POLLS = 90

    const pollJob = async () => {
      pollCounter++
      setPollCount(pollCounter)

      if (pollCounter > MAX_POLLS) {
        setStatus('error')
        setError('Generation taking longer than expected...')
        return
      }

      try {
        const result = await api.getJobStatus(jobId)

        if (result.status === 'complete') {
          const outfitsArray = result.result?.outfits || []
          setOutfits(outfitsArray)

          if (debugMode && result.result?.reasoning) {
            setReasoning(result.result.reasoning)
          }

          setStatus('complete')
          if (pollInterval) clearInterval(pollInterval)
        } else if (result.status === 'failed') {
          setStatus('error')
          setError(result.error || 'Generation failed')
          if (pollInterval) clearInterval(pollInterval)
        }
      } catch (err: any) {
        console.error('Polling error:', err)
      }
    }

    pollJob()
    pollInterval = setInterval(pollJob, 2000)
  }

  // Try SSE first
  startSSEStreaming()

  return () => {
    eventSource?.close()
    if (pollInterval) clearInterval(pollInterval)
  }
}, [jobId, debugMode])
```

**3. Update loading state display to show progress:**

Find the loading state UI (lines 93-116) and update:

```typescript
{status === 'loading' && (
  <div className="min-h-screen bg-bone flex items-center justify-center page-container">
    <div className="text-center px-4 max-w-sm">
      <div className="animate-spin rounded-full h-12 w-12 border-4 border-sand border-t-terracotta mx-auto mb-4"></div>

      {/* Show current progress message */}
      <p className="text-ink text-base font-medium mb-2">
        {streamedContent || 'Creating your outfits...'}
      </p>

      {/* Show which outfit is being created */}
      {currentOutfit > 0 && (
        <p className="text-muted text-sm mb-2">
          Outfit {currentOutfit} of 3
        </p>
      )}

      {/* Progress bar */}
      {progress > 0 && (
        <div className="mt-4">
          <div className="w-full bg-sand rounded-full h-2 mb-2">
            <div
              className="bg-terracotta h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <p className="text-xs text-muted">{progress}% complete</p>
        </div>
      )}

      {pollCount > 30 && (
        <p className="text-xs text-muted mt-2">
          Still processing... ({Math.floor(pollCount * 2)}s elapsed)
        </p>
      )}
    </div>
  </div>
)}
```

---

## Testing Checklist

### Backend Testing

**Test 1: OpenAI streaming works**
```bash
# From backend directory, test streaming in Python shell
python3 -c "
from services.ai.providers.openai import OpenAIProvider
from services.ai.providers.base import AIProviderConfig

config = AIProviderConfig(
    provider='openai',
    model='gpt-4o',
    temperature=0.7,
    max_tokens=100
)

provider = OpenAIProvider(config)

print('Testing streaming...')
for chunk in provider.generate_text_stream('Write a haiku about coding'):
    print(chunk, end='', flush=True)
print('\nDone!')
"
```

Expected: See text streaming character by character

**Test 2: SSE endpoint streams job updates**
```bash
# Start backend
cd backend && uvicorn main:app --reload

# In another terminal, start a job
curl -X POST http://localhost:8000/api/outfits/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "occasions": ["casual"],
    "mode": "occasion",
    "include_reasoning": false
  }'

# Get job_id from response, then stream updates
curl -N http://localhost:8000/api/jobs/{job_id}/stream

# Expected: See SSE events streaming:
# event: progress
# data: {"progress": 30, "message": "Wardrobe loaded..."}
#
# event: progress
# data: {"progress": 40, "message": "Creating outfit 1 of 3..."}
#
# event: complete
# data: {"outfits": [...]}
```

**Test 3: Verify job.meta updates during generation**

Add temporary logging to worker:
```python
# In outfit_worker.py
logger.info(f"Job meta: {job.meta}")  # After each job.save_meta()
```

Run job and check logs - should see progress updates being saved.

---

### Frontend Testing

**Test 4: SSE streaming works end-to-end**
1. Navigate to: `http://localhost:3000/occasion?user=test`
2. Select occasion, click "Create Outfits"
3. ✅ Should redirect to `/reveal?user=test&job={job_id}`
4. ✅ Within 1-2 seconds, should see "Creating outfit 1 of 3..." or similar message
5. ✅ Progress bar should update (30% → 40% → 90% → 100%)
6. ✅ Should see "Outfit X of 3" update (1 → 2 → 3)
7. ✅ When complete, outfits display

**Test 5: Polling fallback works**
1. Disable SSE in browser (or simulate error)
2. Generate outfits
3. ✅ Should fall back to polling (every 2s)
4. ✅ Should still complete successfully

**Test 6: Debug mode works with streaming**
1. Navigate to: `http://localhost:3000/occasion?user=test&debug=true`
2. Generate outfits
3. ✅ Should see streaming progress updates
4. ✅ When complete, should see reasoning section
5. ✅ Reasoning should include chain-of-thought text

**Test 7: All 3 flows work with streaming**

Test each flow:
- `/occasion?user=test` → SSE streaming ✅
- `/complete?user=test` → SSE streaming ✅
- `/consider-buying/outfits?user=test` → SSE streaming ✅

All should show progressive updates, not blank waiting screens.

---

### Performance Testing

**Test 8: Multiple concurrent users**
1. Open 3 browser tabs
2. Start generation in all 3 simultaneously
3. ✅ All streams should work independently
4. ✅ No interference between jobs
5. ✅ All complete successfully

**Test 9: Latency improvement**

Measure perceived latency:
- **Before streaming:** Time from click → first visual feedback = 20-30s
- **After streaming:** Time from click → first visual feedback = 1-2s (progress message)

Even though total time is the same, perceived latency should feel much better.

---

## Success Criteria

- [ ] Backend: OpenAI provider has `generate_text_stream()` method
- [ ] Backend: SSE endpoint `/api/jobs/{job_id}/stream` works
- [ ] Backend: Worker emits progress events in job.meta
- [ ] Frontend: `/reveal` page uses EventSource for SSE
- [ ] Frontend: Shows progressive messages ("Creating outfit X of 3...")
- [ ] Frontend: Progress bar updates in real-time
- [ ] Frontend: Falls back to polling if SSE fails
- [ ] Integration: All 3 flows show streaming progress
- [ ] Integration: Debug mode works with streaming
- [ ] UX: First feedback appears within 1-2 seconds (not 20-30s)

---

## Rollback Plan

If streaming causes issues:

**Backend:** Comment out SSE endpoint, workers still work normally
**Frontend:** Set feature flag to skip SSE, use polling only

```typescript
// In reveal/page.tsx
const USE_SSE_STREAMING = false  // Set to false to disable streaming

useEffect(() => {
  if (USE_SSE_STREAMING) {
    startSSEStreaming()
  } else {
    startPolling()
  }
}, [jobId])
```

**Total rollback time:** ~5 minutes (change flag, redeploy)

---

## Files Modified Summary

### Backend (3 files)
1. `backend/services/ai/providers/openai.py` - Add `generate_text_stream()` method
2. `backend/workers/outfit_worker.py` - Add progress milestones to job.meta
3. `backend/api/jobs.py` - Add `/jobs/{job_id}/stream` SSE endpoint

### Frontend (1 file)
1. `frontend/app/reveal/page.tsx` - Replace polling with SSE, update loading UI

**Total:** 4 files modified

**Estimated time:** 2-3 hours

---

## Implementation Order

**Phase 1: Backend Foundation (1 hour)**
1. Add `generate_text_stream()` to OpenAI provider
2. Test streaming in Python shell
3. Add progress milestones to workers

**Phase 2: SSE Endpoint (30 min)**
1. Add `/jobs/{job_id}/stream` endpoint
2. Test with curl

**Phase 3: Frontend Integration (1 hour)**
1. Update `/reveal` page to use EventSource
2. Update loading UI with progress messages
3. Test end-to-end

**Phase 4: Polish & Testing (30 min)**
1. Test all 3 flows
2. Test debug mode
3. Test fallback to polling

---

## Future Enhancements (Not in This Spec)

These would further improve streaming but are out of scope for MVP:

1. **True mid-generation streaming:** Stream reasoning text as AI generates it (requires StyleEngine changes)
2. **Partial outfit display:** Show outfit 1 while generating outfit 2 (requires parsing mid-stream)
3. **Retry logic:** Auto-retry if SSE connection drops mid-generation
4. **Parallel generation:** Generate 3 outfits simultaneously (reduces total time but 3x cost)

For now, we're doing progress milestones which gives 90% of the UX benefit with 10% of the complexity.

---

## Questions for Cursor

If you encounter any of these scenarios, stop and ask:

1. **EventSource not available** - Ask about browser compatibility or alternative approach
2. **SSE events not firing** - Ask about nginx/proxy configuration
3. **Job.meta not persisting** - Ask about Redis configuration
4. **Streaming too slow/fast** - Ask about polling interval tuning
5. **Type errors with EventSource** - Ask about TypeScript definitions

---

**Ready to implement!** This adds streaming progress updates to all outfit generation flows, making the 20-30s wait feel much faster with immediate feedback.
