# Debug Mode Implementation Spec

## Overview
Add `?debug=true` URL parameter to ALL outfit generation flows that displays the AI's chain-of-thought reasoning alongside final outfits.

**Affected flows:**
1. `/occasion` (Plan my outfit) → job queue → displays on `/reveal`
2. `/complete` (Complete my look) → job queue → displays on `/reveal`
3. `/consider-buying/outfits` (See how items work) → synchronous → displays inline

**Environment:** Production uses `PROMPT_VERSION=chain_of_thought_v1`

---

## Chain-of-Thought Output Format

The AI generates reasoning followed by JSON:

```
FUNCTION: Create a polished casual look...

ANCHOR: Camel wool coat
- Why it's the hero: ...
- Style words: classic

SUPPORTING PIECES:
- Black skinny jeans: ... - carries "relaxed"
- White silk blouse: ... - carries "playful"

UNEXPECTED ELEMENT: Chunky gold hoop earrings
- Breaks: Conservative classic expectations
- Works because: Adds personality without competing

STYLE DNA: classic ✓ coat | relaxed ✓ jeans | playful ✓ earrings

COMPLETING THE LOOK:
- Black ankle boots: Complete the silhouette

STORY: "I'm someone who values timeless pieces but isn't afraid to add edge"

PHYSICAL CHECK: Fabrics work (wool + denim + silk)

FINAL OUTFIT:
- Camel wool coat
- Black skinny jeans
- White silk blouse
- Chunky gold hoop earrings
- Black ankle boots

STYLING: Tuck blouse into jeans, cuff sleeves, coat open

===JSON OUTPUT===

[
  {
    "items": ["Camel wool coat", "Black skinny jeans", "White silk blouse", "Chunky gold hoop earrings", "Black ankle boots"],
    "styling_notes": "Tuck blouse into jeans, cuff sleeves, coat open",
    "why_it_works": "Classic coat anchors the outfit while relaxed denim and playful earrings add personality..."
  }
]
```

**Debug mode goal:** Show the reasoning section to users when `?debug=true` is present.

---

## Backend Changes

### File 1: `backend/services/style_engine.py`

**Location:** Method `generate_outfit_combinations` (around line 100-200)

**Change:** Add optional parameter to return raw AI response alongside parsed outfits

**Current signature:**
```python
def generate_outfit_combinations(
    self,
    user_profile: Dict,
    available_items: List[Dict],
    styling_challenges: List[Dict],
    occasion: Optional[str] = None,
    weather_condition: Optional[str] = None,
    temperature_range: Optional[str] = None
) -> List[Dict]:
```

**New signature:**
```python
def generate_outfit_combinations(
    self,
    user_profile: Dict,
    available_items: List[Dict],
    styling_challenges: List[Dict],
    occasion: Optional[str] = None,
    weather_condition: Optional[str] = None,
    temperature_range: Optional[str] = None,
    include_raw_response: bool = False  # NEW
) -> Union[List[Dict], Tuple[List[Dict], str]]:
    """
    Generate outfit combinations.

    Args:
        ... (existing params)
        include_raw_response: If True, return (outfits, raw_ai_response) tuple

    Returns:
        If include_raw_response=False: List[Dict] of outfit dicts
        If include_raw_response=True: Tuple[List[Dict], str] - (outfits, raw AI response)
    """
```

**Implementation:**
```python
# Inside generate_outfit_combinations method

# ... existing prompt building code ...

# Call AI provider (existing code)
ai_result: AIResponse = self.ai_provider.generate_text(
    prompt=prompt,
    system_message=system_message,
    temperature=self.temperature,
    max_tokens=self.max_tokens
)

# Store raw response BEFORE parsing
raw_response = ai_result.content

# ... existing parsing logic to extract JSON and create outfit objects ...

# Return based on flag
if include_raw_response:
    return (parsed_outfits, raw_response)
else:
    return parsed_outfits
```

**Add import at top of file:**
```python
from typing import Dict, List, Optional, Tuple, Union
```

---

### File 2: `backend/api/outfits.py`

**Location:** Request model and endpoint (around line 10-50)

**Change 1: Update OutfitRequest model**

Find the `OutfitRequest` Pydantic model and add:
```python
class OutfitRequest(BaseModel):
    user_id: str
    occasions: Optional[List[str]] = None
    weather_condition: Optional[str] = None
    temperature_range: Optional[str] = None
    mode: str = "occasion"
    anchor_items: Optional[List[str]] = None
    mock: bool = False
    include_reasoning: bool = False  # NEW
```

**Change 2: Pass include_reasoning to worker**

Find the `generate_outfits` endpoint (the one that enqueues jobs) and modify:

```python
@router.post("/outfits/generate", response_model=OutfitGenerationResponse)
async def generate_outfits(request: OutfitRequest):
    """Generate outfits (background job)"""
    try:
        outfit_queue = get_outfit_queue()
        job = outfit_queue.enqueue(
            generate_outfits_job,
            user_id=request.user_id,
            occasions=request.occasions,
            weather_condition=request.weather_condition,
            temperature_range=request.temperature_range,
            mode=request.mode,
            anchor_items=request.anchor_items,
            mock=request.mock,
            include_reasoning=request.include_reasoning,  # NEW
            job_timeout=120
        )

        return {
            "job_id": job.id,
            "status": "queued",
            "estimated_time": 30
        }
    # ... rest of function
```

---

### File 3: `backend/workers/outfit_worker.py`

**Location:** Function `generate_outfits_job` (around line 26)

**Change 1: Add include_reasoning parameter**

```python
def generate_outfits_job(
    user_id: str,
    occasions: List[str] = None,
    weather_condition: str = None,
    temperature_range: str = None,
    mode: str = "occasion",
    anchor_items: List[str] = None,
    mock: bool = False,
    include_reasoning: bool = False  # NEW
) -> Dict:
```

**Change 2: Call engine with include_raw_response and store reasoning**

Find where `engine.generate_outfit_combinations()` is called and modify:

```python
# OLD:
combinations = engine.generate_outfit_combinations(
    user_profile=user_profile,
    available_items=wardrobe_items,
    styling_challenges=styling_challenges,
    occasion=occasion,
    weather_condition=weather_condition,
    temperature_range=temperature_range
)

# NEW:
if include_reasoning:
    combinations, raw_reasoning = engine.generate_outfit_combinations(
        user_profile=user_profile,
        available_items=wardrobe_items,
        styling_challenges=styling_challenges,
        occasion=occasion,
        weather_condition=weather_condition,
        temperature_range=temperature_range,
        include_raw_response=True
    )
else:
    combinations = engine.generate_outfit_combinations(
        user_profile=user_profile,
        available_items=wardrobe_items,
        styling_challenges=styling_challenges,
        occasion=occasion,
        weather_condition=weather_condition,
        temperature_range=temperature_range,
        include_raw_response=False
    )
    raw_reasoning = None
```

**Change 3: Include reasoning in return value**

Find the return statement at the end of the function and modify:

```python
# Build response
result = {
    "outfits": outfit_dicts,
    "count": len(outfit_dicts)
}

# Add reasoning if requested
if include_reasoning and raw_reasoning:
    result["reasoning"] = raw_reasoning

return result
```

---

### File 4: `backend/api/consider_buying.py`

**Location:** Function `generate_outfits` (around line 158-220)

**Change 1: Add include_reasoning parameter**

```python
@router.post("/consider-buying/generate-outfits")
async def generate_outfits(
    item_id: str = Form(...),
    use_existing_similar: bool = Form(False),
    user_id: str = Form(...),
    include_reasoning: bool = Form(False)  # NEW
):
```

**Change 2: Call engine with include_raw_response**

Find where `engine.generate_outfit_combinations()` is called (around line 202) and modify:

```python
# OLD:
combinations = engine.generate_outfit_combinations(
    user_profile=user_profile,
    available_items=wardrobe_items,
    styling_challenges=anchor_items,
    occasion=None,
    weather_condition=None,
    temperature_range=None
)

# NEW:
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
```

**Change 3: Include reasoning in response**

Find the return statement (around line 211) and modify:

```python
# Build response
response_data = {
    "outfits": combinations,
    "anchor_items": anchor_items
}

# Add reasoning if requested
if include_reasoning and raw_reasoning:
    response_data["reasoning"] = raw_reasoning

return response_data
```

---

## Frontend Changes

### File 5: `frontend/app/occasion/page.tsx`

**Location:** Top of component and handleGenerate function

**Change 1: Detect debug URL parameter**

Add at the top of the component:
```typescript
'use client'

import { useSearchParams } from 'next/navigation'

export default function OccasionPage() {
  const searchParams = useSearchParams()
  const debugMode = searchParams.get('debug') === 'true'

  // ... existing state
```

**Change 2: Pass include_reasoning to API**

Find the `handleGenerate` function and modify the API call:

```typescript
const handleGenerate = async () => {
  setGenerating(true)
  try {
    const { job_id } = await api.generateOutfits({
      user_id: user,
      occasions: [...selectedOccasions, customOccasion].filter(Boolean),
      weather_condition: weather.condition,
      temperature_range: weather.temp,
      mode: 'occasion',
      mock: user === 'test',
      include_reasoning: debugMode  // NEW
    })

    // Redirect with debug param if enabled
    const debugParam = debugMode ? '&debug=true' : ''
    router.push(`/reveal?user=${user}&job=${job_id}${debugParam}`)
  } catch (error) {
    // ... error handling
  }
}
```

---

### File 6: `frontend/app/complete/page.tsx`

**Location:** Same changes as occasion page

**Change 1: Detect debug URL parameter**

```typescript
'use client'

import { useSearchParams } from 'next/navigation'

export default function CompletePage() {
  const searchParams = useSearchParams()
  const debugMode = searchParams.get('debug') === 'true'

  // ... existing state
```

**Change 2: Pass include_reasoning to API and redirect with debug param**

Find `handleGenerate` and modify:

```typescript
const handleGenerate = async () => {
  setGenerating(true)
  try {
    const { job_id } = await api.generateOutfits({
      user_id: user,
      mode: 'complete',
      anchor_items: selectedItems.map(i => i.id),
      weather_condition: weather.condition,
      temperature_range: weather.temp,
      mock: user === 'test',
      include_reasoning: debugMode  // NEW
    })

    // Redirect with debug param if enabled
    const debugParam = debugMode ? '&debug=true' : ''
    router.push(`/reveal?user=${user}&job=${job_id}${debugParam}`)
  } catch (error) {
    // ... error handling
  }
}
```

---

### File 7: `frontend/app/reveal/page.tsx`

**Location:** Top of component, job polling, and display section

**Change 1: Detect debug URL parameter**

```typescript
'use client'

import { useSearchParams } from 'next/navigation'

export default function RevealPage() {
  const searchParams = useSearchParams()
  const debugMode = searchParams.get('debug') === 'true'

  const [outfits, setOutfits] = useState([])
  const [reasoning, setReasoning] = useState<string | null>(null)  // NEW

  // ... existing state
```

**Change 2: Extract reasoning from job result**

Find where job result is processed (in the polling useEffect, when `result.status === 'complete'`):

```typescript
// Inside polling logic
if (result.status === 'complete') {
  const outfitsArray = result.result?.outfits || []
  setOutfits(outfitsArray)

  // Extract reasoning if present
  if (debugMode && result.result?.reasoning) {
    setReasoning(result.result.reasoning)
  }

  setStatus('complete')
  clearInterval(pollInterval)
}
```

**Change 3: Display reasoning when debug mode is active**

Find the render section where outfits are displayed and add:

```typescript
return (
  <div className="min-h-screen bg-bone">
    {/* ... existing header */}

    <div className="max-w-4xl mx-auto px-4 py-8">

      {/* Debug mode indicator */}
      {debugMode && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">
            🐛 Debug Mode Active - Showing AI reasoning
          </p>
        </div>
      )}

      {/* Loading state */}
      {status === 'loading' && (
        // ... existing loading UI
      )}

      {/* Complete state */}
      {status === 'complete' && (
        <>
          {/* Show reasoning if debug mode is on */}
          {debugMode && reasoning ? (
            <div className="space-y-6 mb-8">
              <div className="bg-white rounded-lg shadow-sm border border-sand p-6">
                <h2 className="text-lg font-semibold text-ink mb-4">
                  Chain-of-Thought Reasoning
                </h2>
                <pre className="whitespace-pre-wrap text-sm text-muted font-mono bg-bone p-4 rounded border border-sand overflow-x-auto max-h-96 overflow-y-auto">
                  {reasoning}
                </pre>
              </div>

              <div className="border-t border-sand pt-6">
                <h2 className="text-lg font-semibold text-ink mb-4">
                  Final Outfits
                </h2>
              </div>
            </div>
          ) : null}

          {/* Outfit cards */}
          <div className="space-y-8">
            {outfits.map((outfit, idx) => (
              <OutfitCard key={idx} outfit={outfit} user={user} />
            ))}
          </div>
        </>
      )}

      {/* Error state */}
      {status === 'error' && (
        // ... existing error UI
      )}
    </div>
  </div>
)
```

---

### File 8: `frontend/app/consider-buying/outfits/page.tsx`

**Location:** Top of component, handleGenerate, and display section

**Change 1: Detect debug URL parameter**

```typescript
'use client'

import { useSearchParams } from 'next/navigation'

export default function ConsiderBuyingOutfitsPage() {
  const searchParams = useSearchParams()
  const debugMode = searchParams.get('debug') === 'true'

  const [outfits, setOutfits] = useState([])
  const [reasoning, setReasoning] = useState<string | null>(null)  // NEW

  // ... existing state
```

**Change 2: Request reasoning when debug mode is enabled**

Find the `handleGenerate` function and modify:

```typescript
const handleGenerate = async () => {
  setGenerating(true)

  try {
    const formData = new FormData()
    formData.append('item_id', itemId)
    formData.append('use_existing_similar', useExistingSimilar.toString())
    formData.append('user_id', user)
    formData.append('include_reasoning', debugMode.toString())  // NEW

    const res = await fetch(`${API_URL}/api/consider-buying/generate-outfits`, {
      method: 'POST',
      body: formData
    })

    if (!res.ok) throw new Error('Failed to generate outfits')

    const data = await res.json()
    setOutfits(data.outfits)

    // Store reasoning if present
    if (debugMode && data.reasoning) {
      setReasoning(data.reasoning)
    }

  } catch (error) {
    console.error('Error generating outfits:', error)
    alert('Failed to generate outfits. Please try again.')
  } finally {
    setGenerating(false)
  }
}
```

**Change 3: Display reasoning when debug mode is active**

Find the render section and modify:

```typescript
return (
  <div className="min-h-screen bg-bone">
    {/* ... existing header/navigation */}

    <div className="max-w-4xl mx-auto px-4 py-8">

      {/* Debug mode indicator */}
      {debugMode && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">
            🐛 Debug Mode Active - Showing AI reasoning
          </p>
        </div>
      )}

      {/* ... existing generate button and UI */}

      {/* Show reasoning if debug mode is on */}
      {debugMode && reasoning ? (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm border border-sand p-6">
            <h2 className="text-lg font-semibold text-ink mb-4">
              Chain-of-Thought Reasoning
            </h2>
            <pre className="whitespace-pre-wrap text-sm text-muted font-mono bg-bone p-4 rounded border border-sand overflow-x-auto max-h-96 overflow-y-auto">
              {reasoning}
            </pre>
          </div>

          {/* Still show outfits below reasoning */}
          <div className="border-t border-sand pt-6">
            <h2 className="text-lg font-semibold text-ink mb-4">
              Final Outfits
            </h2>
            <div className="space-y-6">
              {outfits.map((outfit, idx) => (
                <OutfitCard key={idx} outfit={outfit} />
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Normal mode: just show outfit cards */
        <div className="space-y-6">
          {outfits.map((outfit, idx) => (
            <OutfitCard key={idx} outfit={outfit} />
          ))}
        </div>
      )}
    </div>
  </div>
)
```

---

### File 9: `frontend/lib/api.ts` (if exists)

**Location:** The `generateOutfits` method

**Change:** Add `include_reasoning` to the request interface:

```typescript
async generateOutfits(request: {
  user_id: string
  occasions?: string[]
  weather_condition?: string
  temperature_range?: string
  mode: 'occasion' | 'complete'
  anchor_items?: string[]
  mock?: boolean
  include_reasoning?: boolean  // NEW
}) {
  const res = await fetch(`${API_URL}/api/outfits/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  })
  if (!res.ok) throw new Error('Failed to generate outfits')
  return res.json()
}
```

---

## Testing Checklist

### Backend Testing

**Test 1: StyleEngine returns reasoning when requested**
```bash
# From backend directory, start Python shell
python3 -c "
from services.style_engine import StyleGenerationEngine

engine = StyleGenerationEngine()
outfits, reasoning = engine.generate_outfit_combinations(
    user_profile={'three_words': {'current': 'classic', 'aspirational': 'bold', 'feeling': 'confident'}},
    available_items=[],  # Add mock items
    styling_challenges=[],
    include_raw_response=True
)

print('Reasoning includes FUNCTION:', 'FUNCTION:' in reasoning)
print('Reasoning includes ===JSON OUTPUT===:', '===JSON OUTPUT===' in reasoning)
"
```

**Test 2: Job worker stores reasoning**
```bash
# Start backend
cd backend && uvicorn main:app --reload

# In another terminal, trigger job with include_reasoning
curl -X POST http://localhost:8000/api/outfits/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "occasions": ["casual"],
    "mode": "occasion",
    "include_reasoning": true
  }'

# Note the job_id, then check result
curl http://localhost:8000/api/jobs/{job_id}

# Expected: result should have "reasoning" field with chain-of-thought text
```

**Test 3: Consider-buying endpoint returns reasoning**
```bash
curl -X POST http://localhost:8000/api/consider-buying/generate-outfits \
  -F "user_id=test" \
  -F "item_id=some_valid_item_id" \
  -F "use_existing_similar=false" \
  -F "include_reasoning=true"

# Expected: JSON response with "reasoning" field
```

### Frontend Testing

**Test 4: Occasion flow with debug mode**
1. Navigate to: `http://localhost:3000/occasion?user=test&debug=true`
2. ✅ See yellow debug indicator
3. Select occasion and click "Create Outfits"
4. ✅ Should redirect to `/reveal?user=test&job=xxx&debug=true`
5. ✅ When complete, see "Chain-of-Thought Reasoning" section
6. ✅ See reasoning text with FUNCTION, ANCHOR, etc.
7. ✅ See "Final Outfits" section below

**Test 5: Complete flow with debug mode**
1. Navigate to: `http://localhost:3000/complete?user=test&debug=true`
2. ✅ See yellow debug indicator
3. Select items and click "Create Outfits"
4. ✅ Should redirect to `/reveal?user=test&job=xxx&debug=true`
5. ✅ When complete, see reasoning section
6. ✅ See final outfits below

**Test 6: Consider-buying flow with debug mode**
1. Navigate to: `http://localhost:3000/consider-buying/outfits?user=test&debug=true`
2. ✅ See yellow debug indicator
3. Click "Generate Outfits"
4. ✅ See reasoning section appear when generation completes
5. ✅ See final outfits below reasoning

**Test 7: Normal mode (no debug parameter)**
1. Navigate to all flows WITHOUT `&debug=true`
2. ✅ No debug indicator
3. ✅ No reasoning displayed
4. ✅ Only outfit cards shown
5. ✅ Everything works as before

**Test 8: Debug parameter variations**
- `?debug=false` → Normal mode ✅
- `?debug=true` → Debug mode ✅
- `?debug=1` → Normal mode (only "true" activates) ✅
- No debug param → Normal mode ✅

### Edge Cases

**Test 9: Error handling with debug mode**
1. Enable debug mode
2. Trigger an error (invalid parameters)
3. ✅ Error message appears
4. ✅ No crash when reasoning is null

**Test 10: Reasoning display formatting**
1. Enable debug mode and generate outfits
2. ✅ Text preserves line breaks (whitespace-pre-wrap)
3. ✅ Monospace font for readability
4. ✅ Scrollable if content is long (max-h-96)
5. ✅ `===JSON OUTPUT===` separator is visible

---

## Success Criteria

- [ ] Backend: StyleEngine returns reasoning when `include_raw_response=True`
- [ ] Backend: Job worker stores reasoning in result when `include_reasoning=True`
- [ ] Backend: All 3 endpoints accept and handle `include_reasoning` parameter
- [ ] Frontend: All 3 flows detect `?debug=true` URL parameter
- [ ] Frontend: Debug indicator appears when debug mode is on
- [ ] Frontend: Reasoning text displays in monospace, properly formatted
- [ ] Frontend: Final outfits still display below reasoning
- [ ] Frontend: Normal mode (without `?debug=true`) unchanged
- [ ] No console errors in either mode
- [ ] Reasoning text includes expected sections: FUNCTION, ANCHOR, SUPPORTING PIECES, etc.

---

## Implementation Notes

**Type safety (TypeScript):**
```typescript
// Add to type definitions
interface OutfitGenerationResult {
  outfits: Outfit[]
  count: number
  reasoning?: string  // Optional, only when include_reasoning=true
}

interface ConsiderBuyingResult {
  outfits: Outfit[]
  anchor_items: Item[]
  reasoning?: string  // Optional, only when include_reasoning=true
}
```

**Import required:**
```typescript
import { useSearchParams } from 'next/navigation'
```

**Styling classes to use:**
- `bg-bone`, `text-ink`, `text-muted`, `border-sand` (existing colors)
- `font-mono` for reasoning text
- `whitespace-pre-wrap` to preserve formatting
- `max-h-96 overflow-y-auto` for scrollable reasoning

---

## Files Modified Summary

### Backend (4 files)
1. `backend/services/style_engine.py` - Add `include_raw_response` parameter
2. `backend/workers/outfit_worker.py` - Store reasoning in job result
3. `backend/api/outfits.py` - Add `include_reasoning` to request model
4. `backend/api/consider_buying.py` - Add `include_reasoning` parameter

### Frontend (5 files)
1. `frontend/app/occasion/page.tsx` - Detect debug, pass to API, redirect with param
2. `frontend/app/complete/page.tsx` - Detect debug, pass to API, redirect with param
3. `frontend/app/reveal/page.tsx` - Detect debug, extract and display reasoning
4. `frontend/app/consider-buying/outfits/page.tsx` - Detect debug, request and display reasoning
5. `frontend/lib/api.ts` - Add `include_reasoning` to interface (if file exists)

**Total:** 9 files modified

**Estimated time:** 60-90 minutes

---

## Questions for Cursor

If you encounter any of these scenarios, stop and ask:

1. **Type mismatches** - If TypeScript types don't match, ask for the correct type definitions
2. **Missing imports** - If components like `OutfitCard` aren't found, ask for import paths
3. **API_URL not defined** - Ask where to import it from
4. **Styling classes don't exist** - Ask if you should use alternatives
5. **Method signature different** - If `generate_outfit_combinations` has different params, ask for clarification
6. **useSearchParams not available** - Ask if using a different Next.js version

---

**Ready to implement!** This spec covers all three outfit generation flows with consistent debug mode functionality.
