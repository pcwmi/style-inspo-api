# Architecture Migration Spec: Streamlit → FastAPI + Next.js

**Created**: Nov 16, 2025
**Owner**: Pei-Chin
**Timeline**: 2-3 weeks
**Status**: Ready for Cursor implementation proposal

---

## Why We're Migrating

### The Problem: Streamlit Limits Product Quality

After 100+ screenshots of mobile usage, we've identified systematic UX issues:

**Performance Issues:**
- Page load latency: 1-2s between pages (full Python script reruns)
- Button flicker during transitions (Flash of Unstyled Content)
- Scroll position not preserved (Streamlit rerun lifecycle)
- Evidence: 4+ second blank screens, janky navigation

**Mobile Polish Issues:**
- Bottom buttons covered by browser bar (CSS safe-area conflicts)
- Excessive spacing (gaps too large on mobile)
- Font sizes too large (36-40px titles on mobile)
- Images unconstrained (take full screen width)

**Root Cause:** Streamlit is a prototyping tool. Every interaction triggers full page reruns, CSS re-injection, and DOM rebuilding. This is fine for internal demos, not for daily-use products.

### The Goal: Polished Mobile Web Experience

**What success looks like:**
- Page navigation: <200ms (vs current 1-2s)
- No visual glitches (no FOUC, no button flicker)
- Proper mobile spacing (comfortable reading, not overwhelming)
- Buttons always tappable (not covered by browser chrome)
- You use it daily without frustration

---

## What Must Be Preserved

### Python Business Logic (100% Reuse)

**These files contain all the product value - do NOT rewrite:**

```
style_engine.py              # AI outfit generation logic
wardrobe_manager.py          # Wardrobe CRUD operations
storage_manager.py           # S3 upload/download
image_analyzer.py            # OpenAI Vision analysis
saved_outfits_manager.py     # Saved outfits persistence
disliked_outfits_manager.py  # Feedback tracking
styling_evaluation.py        # Outfit scoring (if used)
```

**What to do with these:**
- Move to backend/services/ (or equivalent)
- Refactor for async where beneficial (OpenAI, S3 calls)
- Keep all prompts, validation rules, and logic identical
- Expose via REST API endpoints

### User Flows (Feature Parity Required)

**Must implement these exact flows:**

1. **Onboarding** (new users):
   - Three-word style profile → Upload wardrobe → Path choice → First outfit

2. **Occasion-based generation** (P0 feature):
   - Select occasions (checkboxes + custom input)
   - Select weather (dropdowns)
   - Generate 3 outfits
   - See outfit cards with "How to Style" + "Why This Works"
   - Save/dislike with feedback (radio buttons for dislike, checkboxes for save)

3. **Complete my look** (P1 feature):
   - Multi-select wardrobe items
   - Select weather
   - Generate outfits completing the look
   - Same reveal/feedback flow

4. **Dashboard** (returning users):
   - See wardrobe count
   - Access saved/disliked outfits
   - Two CTAs: "Plan My Outfit" + "Complete My Look"
   - Manage closet (upload/delete items)

5. **Multi-user support**:
   - URL routing: `?user=peichin`
   - Each user has separate S3 folders

### Data Persistence (S3 + JSON - No Changes)

**Do NOT change data storage in Phase 1:**
- S3 bucket: `style-inspo-wardrobe`
- File structure: `{user_id}/wardrobe_metadata.json`, `{user_id}/photos/`, `{user_id}/profile.json`, etc.
- JSON schemas: Keep identical to current implementation
- Why: Zero data migration complexity

### Brand Voice & Copy

**All UI copy must follow:** `.claude/COPY_GUIDELINES.md`

Key principles:
- Supportive, not condescending ("Here's what could work" not "I created the perfect outfit")
- Collaborative ("Let's find" not "I'll find")
- User-centric ("Not my style" not "You got my style wrong")

---

## What Must Be Fixed

### Performance Targets

| Metric | Current (Streamlit) | Target (New) |
|--------|---------------------|--------------|
| Page navigation | 1-2s | <200ms |
| Initial load | 2-4s | <1s |
| Outfit generation | 20-30s | Same (AI bottleneck) |
| Button responsiveness | Delayed, flickers | Instant |

### Mobile UX Requirements

**Must work perfectly on iPhone/Android browsers:**
- Bottom buttons: NOT covered by browser bar (use CSS safe-area properly)
- Font sizes: Readable but not overwhelming (16-20px body, 24-32px titles)
- Images: Constrained to reasonable size (max 200-300px width for wardrobe items)
- Spacing: Comfortable (not cramped, not excessive)
- Tap targets: Minimum 44px (iOS standard)

**Test on:**
- iOS Safari
- Chrome mobile
- At least one Android browser

### Critical Bugs to Fix

1. **AI validation**: Already fixed in current code (no two bottoms rule) - must port this
2. **Feedback UX**: Already updated (radio/checkboxes) - must implement same
3. **Multi-occasion copy**: Already updated ("What does this ONE outfit need to do?") - must use this

See `ROADMAP.md` section "AI Quality Issues (Fixed)" for details.

---

## Technical Constraints

### Tech Stack (Non-Negotiable)

**Backend:**
- Framework: FastAPI (Python async, REST API)
- Language: Python 3.9+ (to reuse existing code)
- Storage: S3 (existing bucket)
- Hosting: Railway or similar (auto-deploy from GitHub)

**Frontend:**
- Framework: Next.js (React, mobile-first)
- Language: TypeScript preferred (but JavaScript OK)
- Styling: Your choice (Tailwind, CSS Modules, styled-components - recommend best for mobile)
- Hosting: Vercel (auto-deploy from GitHub)

**Infrastructure:**
- Job queue: Your choice (RQ, Celery, BackgroundTasks, or other - see questions below)
- Redis: Required (for job queue or caching)
- Deployment: Must be simple (max 3 dashboards to manage)

### Architecture Principles

**Separation of concerns:**
- Backend: Pure API (no UI, no session state)
- Frontend: Pure UI (no business logic)
- Styling logic: Python services (reused from current codebase)

**Mobile-first:**
- Design for iPhone screen size first
- Desktop is nice-to-have, not required
- Progressive web app (PWA) features optional but nice

**Developer experience:**
- Auto-deploy on git push (no manual steps)
- Environment variables for secrets (not hardcoded)
- Clear separation of development vs production

---

## Open Questions for Cursor

**Before implementing, please propose answers to:**

### 1. Background Jobs

**Question:** How should we handle long-running outfit generation (20-30s)?

**Options:**
- FastAPI BackgroundTasks (simplest, built-in)
- RQ (Redis Queue - lightweight, Python)
- Celery (heavy but robust)
- Railway background workers (platform-specific)
- Other?

**Requirements:**
- Job must return job_id immediately
- Frontend polls for status (or uses WebSocket/SSE if you recommend)
- Job timeout after 2 minutes
- Failed jobs should be retryable

**Your recommendation:** _______

### 2. Repository Structure

**Question:** How should we organize code to avoid breaking production?

**Options:**
- Separate repo (`style-inspo-v2`) - safest
- Separate branch in current repo
- Monorepo with folders (`/streamlit-app`, `/backend`, `/frontend`)
- Other?

**Requirements:**
- Current Streamlit app must keep working during development
- Easy to test new version without affecting production
- Simple cutover when ready

**Your recommendation:** _______

### 3. API Design Patterns

**Question:** What API patterns should we use?

**Options:**
- RESTful with polling (simple)
- WebSocket for real-time updates (more complex)
- Server-Sent Events (SSE) for job progress
- GraphQL (if you think it's better)

**Requirements:**
- Handle long-running jobs gracefully
- Mobile-friendly (low battery/bandwidth consideration)
- Easy to debug

**Your recommendation:** _______

### 4. Mobile CSS Approach

**Question:** What's the best way to handle mobile styling?

**Options:**
- Tailwind CSS (utility-first, popular)
- CSS Modules (scoped, simple)
- styled-components (CSS-in-JS)
- Plain CSS with media queries
- Other?

**Requirements:**
- Mobile-first responsive design
- Easy to maintain
- Good performance (no runtime CSS-in-JS overhead if possible)

**Your recommendation:** _______

### 5. Image Handling

**Question:** How should we handle image uploads and display?

**Options:**
- Client-side compression before upload (reduce bandwidth)
- Server-side compression (simpler client)
- Direct S3 upload with presigned URLs (fastest)
- Next.js Image component (automatic optimization)

**Requirements:**
- Fast upload on mobile (compress before sending)
- Reasonable file sizes (max 1-2MB per image)
- S3 storage (existing bucket)

**Your recommendation:** _______

### 6. Testing Strategy

**Question:** How should we test before launch?

**Proposed approach:**
1. Backend: Manual API testing (Postman/curl)
2. Frontend: Browser testing (Chrome DevTools mobile emulation)
3. Integration: E2E testing of full flows
4. Mobile: Test on real iPhone/Android devices

**Is this sufficient or do you recommend:**
- Unit tests for critical functions?
- Automated E2E tests (Playwright, Cypress)?
- Load testing for job queue?

**Your recommendation:** _______

---

## Phase 1 Scope

### In Scope: Feature Parity + Performance

**Must deliver:**
- ✅ All 5 user flows working (onboarding, occasion, complete, dashboard, saved/disliked)
- ✅ Multi-user support (?user=peichin)
- ✅ S3 integration (same bucket, same structure)
- ✅ AI outfit generation (reusing style_engine.py)
- ✅ Save/dislike with feedback (radio + checkboxes)
- ✅ Mobile-optimized UI (proper spacing, fonts, button placement)
- ✅ <200ms page navigation (vs current 1-2s)
- ✅ Deployed to production URLs (Vercel + Railway)

### Out of Scope: Phase 2 Features

**NOT building now:**
- ❌ PostgreSQL migration (keep S3 + JSON)
- ❌ Pre-compute/scheduled jobs (nightly outfit generation)
- ❌ Advanced homepage redesign (saved outfits carousel, etc.)
- ❌ Authentication (URL-based multi-user is fine)
- ❌ Calendar integration
- ❌ Weather API auto-fetch
- ❌ Native app features (offline, push notifications)
- ❌ Analytics/monitoring (add later if needed)

**Why defer these:** Validate daily usage first, then add complexity.

---

## Reference Materials

### Existing Codebase

**Key files to reference:**
- `new_onboarding.py` - All current UI flows (lines 1-2000+)
- `style_engine.py` - AI prompt engineering and outfit generation
- `wardrobe_manager.py` - How wardrobe data is stored/retrieved
- `storage_manager.py` - S3 upload/download patterns
- `.claude/COPY_GUIDELINES.md` - Brand voice rules
- `ROADMAP.md` - Strategic context and Phase 2 vision

### Current Data Structures

**Example wardrobe_metadata.json:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Blue button-up shirt",
      "category": "tops",
      "sub_category": "shirts",
      "styling_details": {
        "colors": ["blue", "white"],
        "style_tags": ["casual", "professional"],
        "description": "Light blue oxford button-up"
      },
      "image_path": "s3://bucket/user/photos/uuid.jpg",
      "uploaded_at": "2025-11-10T..."
    }
  ]
}
```

**Example outfit response (from AI):**
```json
{
  "outfits": [
    {
      "items": ["Blue button-up shirt", "Dark jeans", "White sneakers"],
      "styling_notes": "Tuck the shirt halfway for a casual look...",
      "why_it_works": "The blue shirt bridges professional and casual...",
      "confidence_level": "Comfort Zone",
      "vibe_keywords": ["relaxed", "put-together", "approachable"]
    }
  ]
}
```

### Current User Flows (Screenshots)

**Available at:**
- `/Users/peichin/Downloads/Video to Screenshots/` (100+ screenshots showing full app flow)
- Reference these to understand UX expectations

---

## Success Criteria

### Functional Requirements Checklist

**Before considering Phase 1 complete, verify:**

- [ ] New user can complete onboarding (three words → upload → first outfit)
- [ ] Returning user sees dashboard with wardrobe count
- [ ] Occasion-based flow generates 3 outfits in <30s
- [ ] Complete-my-look flow works with multi-select items
- [ ] Save outfit with feedback (checkboxes work)
- [ ] Dislike outfit with reason (radio buttons work)
- [ ] Saved outfits page shows all saved outfits
- [ ] Disliked outfits page shows all disliked with reasons
- [ ] Upload new item → appears in wardrobe immediately
- [ ] Delete item → removed from wardrobe
- [ ] Multi-user: ?user=alice and ?user=bob use separate data
- [ ] Mobile: No buttons covered by browser bar
- [ ] Mobile: Font sizes readable (not too large)
- [ ] Mobile: Images constrained (not full width)
- [ ] Navigation: <200ms between pages

### Performance Benchmarks

**Test on iPhone Safari with throttled network:**
- Dashboard load: <1s
- Page navigation: <200ms
- Outfit generation: <30s (same as current)
- Image upload: <5s per photo (with compression)

### User Acceptance Testing

**Before launch, verify:**
- You can use it daily without frustration
- Mia can upload wardrobe and generate outfits
- No critical bugs in core flows
- Copy follows COPY_GUIDELINES.md

---

## Proposed Timeline

### Week 1: Backend + Infrastructure
- Set up repo structure (based on your recommendation)
- Build FastAPI core endpoints (wardrobe, outfits, profile)
- Implement background job system (your recommended approach)
- Deploy to Railway (or your recommended platform)
- Test all API endpoints work

### Week 2: Frontend Core
- Build Next.js pages (dashboard, occasion, complete, reveal)
- Implement job polling for outfit generation
- Build outfit cards with save/dislike feedback
- Deploy to Vercel
- Test full flow works end-to-end

### Week 3: Polish + Testing
- Mobile CSS optimization (based on your recommended approach)
- Fix any bugs found in testing
- Performance optimization (<200ms navigation)
- Final testing on real mobile devices
- Deploy to production

---

## Deployment Requirements

### Environment Setup

**Backend needs these environment variables:**
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=style-inspo-wardrobe
REDIS_URL=redis://...
RUNWAY_API_KEY=...
```

**Frontend needs:**
```
NEXT_PUBLIC_API_URL=https://api.style-inspo.com
```

### Deployment Targets

**Backend:**
- Platform: Railway (or your recommendation)
- Auto-deploy: On push to main branch
- Domain: TBD (Railway provides one, or custom domain)

**Frontend:**
- Platform: Vercel
- Auto-deploy: On push to main branch
- Domain: TBD (Vercel provides one, or custom domain)

**Total dashboards to manage: 2-3** (Railway, Vercel, maybe Redis provider)

---

## Risk Mitigation

### Known Risks & Mitigations

**Risk: Background job failures**
- Mitigation: Set timeouts, show error states with "Try Again" button, log failures

**Risk: Mobile browser incompatibility**
- Mitigation: Test on iOS Safari, Chrome, Firefox; use CSS feature detection

**Risk: S3 access issues**
- Mitigation: Test with existing bucket before switching; keep Streamlit as backup

**Risk: Deployment complexity**
- Mitigation: Use PaaS (Vercel, Railway) not raw servers; document setup steps

**Risk: Breaking production during development**
- Mitigation: Separate repo/branch; test thoroughly before cutover

---

## Questions?

**If anything is unclear or you need more context:**
- Ask me before implementing
- Reference existing codebase files
- Propose alternatives if you see better approaches

**Remember:**
- This spec defines WHAT and WHY, not always HOW
- You have expertise in FastAPI + Next.js - use it
- Propose better solutions if you see them
- I'll review and approve before you proceed

---

## Next Steps

1. **Cursor reviews this spec**
2. **Cursor proposes answers to open questions** (background jobs, repo structure, etc.)
3. **I approve the approach**
4. **Cursor implements Week 1 (backend)**
5. **I test backend APIs**
6. **Cursor implements Week 2 (frontend)**
7. **I test full flows**
8. **Cursor implements Week 3 (polish)**
9. **Launch!** 🚀

---

**Ready to start? Please propose your implementation approach first.**
