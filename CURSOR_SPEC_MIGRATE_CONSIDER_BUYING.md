# Migrate Consider-Buying to Job Queue Pattern

## Overview
Migrate the `/consider-buying` flow from synchronous direct processing to the job queue pattern used by `/occasion` and `/complete`. This ensures architectural consistency and enables all flows to use chain-of-thought prompts.

**Current Problem:**
- `/occasion` and `/complete` use job queue → get chain-of-thought (4.5-star quality)
- `/consider-buying` uses direct call → stuck on baseline prompt (3.5-star quality)
- Two different code paths = 2x maintenance burden

**Goal:**
- All 3 flows use same job queue pattern
- All 3 flows get chain-of-thought quality
- Single code path = easier streaming implementation later

---

## Current vs. New Architecture

### Current Flow (Synchronous)
```
User clicks "Generate Outfits" on /consider-buying/outfits
    ↓
POST /api/consider-buying/generate-outfits
    ↓
StyleEngine.generate_outfit_combinations() [BLOCKS 20-30s]
    ↓
Returns JSON immediately
    ↓
Display outfits on same page
```

### New Flow (Job Queue)
```
User clicks "Generate Outfits" on /consider-buying/outfits
    ↓
POST /api/consider-buying/generate-outfits
    ↓
Enqueue job → Returns job_id immediately (~100ms)
    ↓
Redirect to /reveal?job={job_id}
    ↓
/reveal polls job status every 2s
    ↓
Display outfits when job completes
```

**UX Impact:** Minimal - same 20-30s wait, just on `/reveal` page instead of inline

---

## Backend Changes

### File 1: `backend/workers/outfit_worker.py`

**Location:** Add new function after existing `generate_outfits_job` function (around line 270+)

**Action:** Add worker function for consider-buying flow

**Implementation:**
```python
def generate_consider_buying_job(
    user_id: str,
    item_id: str,
    use_existing_similar: bool = False,
    include_reasoning: bool = False
) -> Dict:
    """
    Background job for consider-buying outfit generation.

    Args:
        user_id: User identifier
        item_id: ID of the item being considered for purchase
        use_existing_similar: If True, use similar items from wardrobe instead of consider_buying item
        include_reasoning: If True, include chain-of-thought reasoning in response

    Returns:
        Dict with outfits, anchor_items, and optionally reasoning
    """
    try:
        logger.info(f"Starting consider-buying job for user {user_id}, item {item_id}")

        # Initialize managers
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        wardrobe_manager = WardrobeManager(user_id=user_id)

        # Get consider_buying item
        consider_item = next((i for i in cb_manager.get_items() if i["id"] == item_id), None)
        if not consider_item:
            raise ValueError(f"Item {item_id} not found in consider_buying")

        # Get wardrobe items
        wardrobe_items = wardrobe_manager.get_wardrobe_items("all")

        # Get user profile (hardcoded for testing as in original endpoint)
        user_profile = {
            "three_words": {
                "current": "classic",
                "aspirational": "relaxed",
                "feeling": "playful"
            }
        }

        # Determine anchor items
        if use_existing_similar:
            # Use similar items from wardrobe
            similar_item_ids = consider_item.get("similar_items_in_wardrobe", [])
            anchor_items = [item for item in wardrobe_items if item["id"] in similar_item_ids]
        else:
            # Use consider_buying item as anchor
            anchor_items = [consider_item]

        logger.info(f"Anchor items: {len(anchor_items)}")

        # Generate outfits using StyleEngine
        engine = StyleGenerationEngine()

        if include_reasoning:
            combinations, raw_reasoning = engine.generate_outfit_combinations(
                user_profile=user_profile,
                available_items=wardrobe_items,
                styling_challenges=anchor_items,
                occasion=None,
                weather_condition=None,
                temperature_range=None,
                include_raw_response=True
            )
        else:
            combinations = engine.generate_outfit_combinations(
                user_profile=user_profile,
                available_items=wardrobe_items,
                styling_challenges=anchor_items,
                occasion=None,
                weather_condition=None,
                temperature_range=None,
                include_raw_response=False
            )
            raw_reasoning = None

        # Convert to serializable format
        outfit_dicts = [
            {
                "items": combo.items,
                "styling_notes": combo.styling_notes,
                "why_it_works": combo.why_it_works,
                "confidence_level": combo.confidence_level,
                "vibe_keywords": combo.vibe_keywords,
                "constitution_principles": combo.constitution_principles,
                "style_opportunity": combo.style_opportunity
            }
            for combo in combinations
        ]

        # Build result
        result = {
            "outfits": outfit_dicts,
            "anchor_items": anchor_items,
            "count": len(outfit_dicts)
        }

        # Add reasoning if requested
        if include_reasoning and raw_reasoning:
            result["reasoning"] = raw_reasoning

        logger.info(f"Consider-buying job completed: {len(outfit_dicts)} outfits generated")
        return result

    except Exception as e:
        logger.error(f"Error in consider-buying job: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
```

**Add imports at top of file if not already present:**
```python
from services.consider_buying_manager import ConsiderBuyingManager
```

---

### File 2: `backend/api/consider_buying.py`

**Location:** Replace the existing `generate_outfits` function (lines 158-220)

**Action:** Change from synchronous to job queue pattern

**Current code to replace:**
```python
@router.post("/consider-buying/generate-outfits")
async def generate_outfits(
    item_id: str = Form(...),
    use_existing_similar: bool = Form(False),
    user_id: str = Form(...),
    include_reasoning: bool = Form(False)
):
    """Generate outfits with consider_buying item"""
    # ... existing synchronous logic
```

**New implementation:**
```python
from core.redis import get_outfit_queue
from workers.outfit_worker import generate_consider_buying_job

@router.post("/consider-buying/generate-outfits")
async def generate_outfits(
    item_id: str = Form(...),
    use_existing_similar: bool = Form(False),
    user_id: str = Form(...),
    include_reasoning: bool = Form(False)
):
    """
    Generate outfits with consider_buying item (background job).

    Returns job_id immediately. Client should poll /api/jobs/{job_id} for results.
    """
    try:
        # Enqueue outfit generation job
        outfit_queue = get_outfit_queue()
        job = outfit_queue.enqueue(
            generate_consider_buying_job,
            user_id=user_id,
            item_id=item_id,
            use_existing_similar=use_existing_similar,
            include_reasoning=include_reasoning,
            job_timeout=120  # 2 minutes max
        )

        logger.info(f"Enqueued consider-buying job {job.id} for user {user_id}")

        return {
            "job_id": job.id,
            "status": "queued",
            "estimated_time": 30  # seconds
        }

    except Exception as e:
        logger.error(f"Error enqueueing consider-buying job: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
```

**Add imports at top of file:**
```python
from core.redis import get_outfit_queue
from workers.outfit_worker import generate_consider_buying_job
```

---

## Frontend Changes

### File 3: `frontend/app/consider-buying/outfits/page.tsx`

**Location:** Modify the `handleGenerate` function and add navigation state

**Current behavior:**
- Calls API synchronously
- Waits for result
- Displays outfits on same page

**New behavior:**
- Calls API to enqueue job
- Gets job_id
- Redirects to `/reveal` page (which already handles job polling)

**Changes needed:**

**1. Add router import at top:**
```typescript
import { useRouter } from 'next/navigation'
```

**2. Add router hook in component:**
```typescript
export default function ConsiderBuyingOutfitsPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const debugMode = searchParams.get('debug') === 'true'

  // ... existing state
```

**3. Replace handleGenerate function:**

Find the existing `handleGenerate` function and replace it with:

```typescript
const handleGenerate = async () => {
  setGenerating(true)

  try {
    const formData = new FormData()
    formData.append('item_id', itemId)
    formData.append('use_existing_similar', useExistingSimilar.toString())
    formData.append('user_id', user)
    formData.append('include_reasoning', debugMode.toString())

    const res = await fetch(`${API_URL}/api/consider-buying/generate-outfits`, {
      method: 'POST',
      body: formData
    })

    if (!res.ok) {
      throw new Error('Failed to generate outfits')
    }

    const data = await res.json()
    const jobId = data.job_id

    if (!jobId) {
      throw new Error('No job_id returned from API')
    }

    // Redirect to reveal page with job_id and debug param
    const debugParam = debugMode ? '&debug=true' : ''
    router.push(`/reveal?user=${user}&job=${jobId}${debugParam}`)

  } catch (error) {
    console.error('Error generating outfits:', error)
    alert('Failed to generate outfits. Please try again.')
    setGenerating(false)
  }
}
```

**4. Remove outfit display logic (no longer needed on this page):**

The page should no longer display outfits inline. Remove:
- `const [outfits, setOutfits] = useState([])` (if exists on this page specifically for displaying)
- `const [reasoning, setReasoning] = useState<string | null>(null)` (if exists on this page)
- Any `<OutfitCard>` rendering on this page

**Note:** Keep any UI for selecting the item and triggering generation. Only remove the outfit display section.

**5. Update loading state message:**

While generating is true (redirecting), show:
```typescript
{generating && (
  <div className="text-center py-4">
    <p className="text-muted">Starting outfit generation...</p>
  </div>
)}
```

---

## File 4: `frontend/app/reveal/page.tsx`

**No changes needed!**

The `/reveal` page already:
- ✅ Accepts `job` query parameter
- ✅ Polls job status every 2 seconds
- ✅ Displays reasoning when `debug=true`
- ✅ Handles job completion and errors
- ✅ Works for `/occasion`, `/complete`, and now `/consider-buying`

---

## Testing Checklist

### Backend Testing

**Test 1: Verify job enqueues correctly**
```bash
# Start backend
cd backend && uvicorn main:app --reload

# In another terminal, enqueue a job
curl -X POST http://localhost:8000/api/consider-buying/generate-outfits \
  -F "user_id=test" \
  -F "item_id=<valid_item_id>" \
  -F "use_existing_similar=false" \
  -F "include_reasoning=false"

# Expected: JSON response with job_id
# {"job_id": "abc-123", "status": "queued", "estimated_time": 30}
```

**Test 2: Verify job completes and returns outfits**
```bash
# Use job_id from Test 1
curl http://localhost:8000/api/jobs/<job_id>

# Expected (when complete):
# {
#   "status": "complete",
#   "result": {
#     "outfits": [...],
#     "anchor_items": [...],
#     "count": 3
#   }
# }
```

**Test 3: Verify reasoning is included when requested**
```bash
curl -X POST http://localhost:8000/api/consider-buying/generate-outfits \
  -F "user_id=test" \
  -F "item_id=<valid_item_id>" \
  -F "use_existing_similar=false" \
  -F "include_reasoning=true"

# Get job_id, then poll:
curl http://localhost:8000/api/jobs/<job_id>

# Expected: result.reasoning field should be present with chain-of-thought text
```

**Test 4: Verify chain-of-thought is being used**

Check the reasoning output includes:
- ✅ "FUNCTION:" section
- ✅ "ANCHOR:" section
- ✅ "SUPPORTING PIECES:" section
- ✅ "UNEXPECTED ELEMENT:" section
- ✅ "===JSON OUTPUT===" separator

This confirms chain-of-thought prompt is active (not baseline).

---

### Frontend Testing

**Test 5: Basic flow without debug mode**
1. Navigate to: `http://localhost:3000/consider-buying/outfits?user=test`
2. Select an item (or have one selected)
3. Click "Generate Outfits"
4. ✅ Should redirect to `/reveal?user=test&job={job_id}`
5. ✅ Should see loading state with progress
6. ✅ When complete, should see 3 outfit cards
7. ✅ No reasoning displayed (debug mode off)

**Test 6: Flow with debug mode**
1. Navigate to: `http://localhost:3000/consider-buying/outfits?user=test&debug=true`
2. ✅ Should see yellow debug indicator
3. Click "Generate Outfits"
4. ✅ Should redirect to `/reveal?user=test&job={job_id}&debug=true`
5. ✅ Should see loading state
6. ✅ When complete, should see chain-of-thought reasoning section
7. ✅ Reasoning should include FUNCTION, ANCHOR, etc.
8. ✅ Should see outfit cards below reasoning

**Test 7: Error handling**
1. Navigate to consider-buying page
2. Try to generate with invalid item_id (or simulate error)
3. ✅ Should see error message
4. ✅ Should not crash
5. ✅ Should allow retry

**Test 8: Use existing similar items toggle**
1. Navigate to consider-buying page with item that has similar items
2. Toggle "use existing similar" ON
3. Generate outfits
4. ✅ Should use similar wardrobe items as anchors (not consider_buying item)

---

### Integration Testing (All 3 Flows)

**Test 9: Verify all flows work consistently**

Test each flow with debug mode on:

1. **Occasion flow:**
   - Navigate to `/occasion?user=test&debug=true`
   - Select occasion, generate outfits
   - ✅ Redirects to `/reveal?debug=true`
   - ✅ Shows chain-of-thought reasoning
   - ✅ Shows 3 outfits

2. **Complete flow:**
   - Navigate to `/complete?user=test&debug=true`
   - Select anchor items, generate outfits
   - ✅ Redirects to `/reveal?debug=true`
   - ✅ Shows chain-of-thought reasoning
   - ✅ Shows 3 outfits

3. **Consider-buying flow:**
   - Navigate to `/consider-buying/outfits?user=test&debug=true`
   - Select item, generate outfits
   - ✅ Redirects to `/reveal?debug=true`
   - ✅ Shows chain-of-thought reasoning
   - ✅ Shows 3 outfits

**Test 10: Quality comparison**

Generate outfits from all 3 flows and compare:
- ✅ All use same chain-of-thought format
- ✅ All have similar quality (4-5 stars)
- ✅ All include accessories, shoes, complete outfits
- ✅ No flow produces noticeably worse results

---

### Edge Cases

**Test 11: Job timeout**
1. Simulate a job that takes >2 minutes (if possible)
2. ✅ Should show timeout error
3. ✅ Should not crash frontend

**Test 12: Navigation during generation**
1. Start outfit generation (get redirected to `/reveal`)
2. Navigate away (back button or new URL)
3. Navigate back to `/reveal?job={job_id}`
4. ✅ Should resume polling
5. ✅ Should show results when complete

**Test 13: Multiple concurrent generations**
1. Open 2 browser tabs
2. Start generation in both (different jobs)
3. ✅ Both should complete independently
4. ✅ No job interference

---

## Success Criteria

- [ ] Backend: `/consider-buying/generate-outfits` returns job_id immediately
- [ ] Backend: `generate_consider_buying_job` worker function completes successfully
- [ ] Backend: Chain-of-thought reasoning is used (verify with debug mode)
- [ ] Backend: Reasoning is included when `include_reasoning=true`
- [ ] Frontend: `/consider-buying/outfits` redirects to `/reveal` after starting job
- [ ] Frontend: `/reveal` page displays consider-buying outfits correctly
- [ ] Frontend: Debug mode shows reasoning for consider-buying flow
- [ ] Integration: All 3 flows (occasion, complete, consider-buying) work consistently
- [ ] Integration: All 3 flows use same chain-of-thought quality
- [ ] No regressions: Existing `/occasion` and `/complete` flows still work

---

## Rollback Plan

If something breaks, rollback is simple:

**Backend:** Keep the old synchronous endpoint code commented out for 1 week
```python
# @router.post("/consider-buying/generate-outfits-sync")  # OLD VERSION - DEPRECATED
# async def generate_outfits_sync(...):
#     # ... old synchronous code
```

**Frontend:** Revert the redirect logic back to inline display

**Total rollback time:** ~15 minutes

---

## Files Modified Summary

### Backend (2 files)
1. `backend/workers/outfit_worker.py` - Add `generate_consider_buying_job` function
2. `backend/api/consider_buying.py` - Update endpoint to enqueue job instead of direct call

### Frontend (1 file)
1. `frontend/app/consider-buying/outfits/page.tsx` - Redirect to `/reveal` instead of inline display

### No Changes Needed
- `frontend/app/reveal/page.tsx` - Already handles job polling (reused)

**Total:** 3 files modified

**Estimated time:** 1-2 hours

---

## Implementation Order

1. **Backend first** (30-45 min)
   - Add worker function
   - Update endpoint
   - Test with curl

2. **Frontend second** (30-45 min)
   - Update page to redirect
   - Test full flow

3. **Integration testing** (15-30 min)
   - Test all 3 flows
   - Verify quality consistency

---

## Questions for Cursor

If you encounter any of these scenarios, stop and ask:

1. **ConsiderBuyingManager import fails** - Ask for the correct import path
2. **Existing outfit display logic unclear** - Ask which specific code to remove vs keep
3. **Router import issues** - Ask about Next.js version or alternative import
4. **Job queue connection fails** - Ask about Redis configuration
5. **Worker function doesn't execute** - Ask about RQ worker setup

---

**Ready to implement!** This migration unifies the architecture and sets the foundation for clean streaming implementation.
