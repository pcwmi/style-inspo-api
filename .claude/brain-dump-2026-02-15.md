# Brain Dump - 2026-02-15

## 02:50 - Alta-Style Progressive Extraction — Shipped and Verified

### What We Built (Feb 12-15, 2026)

Speed up outfit extraction from 2-3 min blocking to ~15s first results with background prettify.

### The Insight
Compared our extraction to Alta's screen recording. Alta doesn't skip heavy processing - they **spread the delay via UX**. Raw crops appear in ~5s, "prettify" runs in background, images update progressively. Total time is similar but perceived time is ~5s.

### Architecture: Two-Phase Pipeline

**Phase A - Fast Extraction (~15s, blocking):**
- Upload photo → GPT-4o identifies items + bounding boxes (3-5s)
- Crop each item from source image (instant, NO rembg)
- Save raw crop images + identification-stage metadata (name, category, colors)
- Return items to frontend immediately

**Phase B - Background Prettify (non-blocking, per item):**
- Auto-enqueue prettify jobs on RQ "analysis" queue after Phase A
- Each job: rembg → gpt-image-1 reconstruction
- Update wardrobe item image when done, set prettified=True
- Frontend polls /prettify-status every 3s, swaps images with shimmer animation

### Files Changed
- `backend/workers/outfit_worker.py` - Simplified extraction loop (no rembg/analysis/reconstruct), added `prettify_extracted_item_job`, auto-enqueue prettify
- `backend/services/wardrobe_manager.py` - Added `update_item_image` method
- `backend/api/wardrobe.py` - Added `/prettify-status` endpoint
- `frontend/components/OutfitExtractModal.tsx` - Polling, shimmer animation, image swap
- `frontend/lib/api.ts` - Added `getPrettifyStatus()`

### Key Decisions
- Skip GPT-4o per-item analysis entirely - identification stage already provides name/category/colors. Per-item analysis adds marginal value but costs 10s/item
- No "Prettify" button - auto-prettify is simpler, matches Alta's behavior
- Prettify queue uses "analysis" (not "default") since that's where RQ Worker listens
- Source photo NOT cleaned up after extraction (prettify jobs need it)

### Bugs Hit During Implementation
- macOS fork() safety crash: RQ worker needs `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`
- GPT-4o transient None content: pre-existing, retry works
- Wrong RQ queue: initially enqueued on "default" but no worker listening, changed to "analysis"
- Playwright file upload sandbox: had to copy test file into project directory

### Verification (Ralph Loop, 6 gates, all passed)
1. Backend imports ✓
2. Frontend build ✓
3. Local E2E fast extraction (~17s for 4 items) ✓
4. Local E2E prettify (all 4 prettified in ~90s) ✓
5. Production Playwright E2E (uploaded photo, 4 items found, Done→Closet works) ✓
6. Existing flows not broken (category tabs, upload modal, SMS health) ✓

### Commit
`0990609` - "Speed up outfit extraction with Alta-style progressive enhancement"

### What's NOT Done
- Enrichment of extracted items (fabric, fit, design_details etc.) - skipped for now, identification-stage data is good enough
- Source photo cleanup after all prettify jobs complete
- Error handling if prettify job fails (item just stays with raw crop, which is fine)
