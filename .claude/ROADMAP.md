# Style Inspo Product Roadmap

*Last updated: 2026-02-04 (Post-User Research)*

## Current Status
- ✅ **Agent-Native Architecture** - 32 primitives, SMS/WhatsApp flow working (~21s E2E)
- ✅ **Visualization** - Runway Gen-4 integration, relatable model approach validated
- ✅ **GPT-5.2 Production** - Upgraded from 5.1 (faster + better quality)
- 🎯 **Current Phase**: Trust & Taste Learning
- 🔍 **Focus Areas**: Output quality, taste learning loop, onboarding friction

---

## 🎯 Core Strategy (Feb 2026 Update)

### The Reframe (from User Research)

**From:** "AI generates your outfit"
**To:** "AI that knows your taste and helps you look good"

### Key Insight: Taste Learning is the Moat

Dana's ChatGPT is sticky because it says "this is very you" and "not the most Dana version of this." That's what we're missing.

**The sequence:**
1. **Build taste** (diagnostic mode) — conversational, back-and-forth
2. **Unlock speed** (busy mom mode) — one-shot, confident

You can't skip to step 2 without step 1.

### User Segmentation

| | Power User (Dana) | Busy Mom (Mia/Heather) |
|---|---|---|
| **Mode** | Iterating, refining | Quick decision, move on |
| **Time** | Has time to engage | 5 minutes or less |
| **Goal** | "Make this outfit better" | "Just tell me what to wear" |
| **What they need** | Taste feedback | Confident recommendations |

**Infrastructure insight:** Taste learning enables BOTH modes. Power users train the system. Busy moms benefit from a system that already knows them.

---

## 🚨 The Trust Problem

**Evidence from user research:**
- Alexi: Generated 6 outfits, saved 0, churned (garment physics)
- Dana: "it put like 3 sweaters together"
- Kate: Won't save until she can see it on a model

**Current state:** Users don't trust complete outfit generation.
- Dimple uses it for purchase validation ("buy smart")
- Alexi uses it for single-item inspiration
- Neither uses it for what we built it for

**The fix:** Stop breaking trust BEFORE adding features.

---

## 🎯 Prioritized Roadmap (Feb 2026)

### Tier 1: Fix Trust Breakers (P0)
*Without these, nothing else matters.*

| # | Item | Why | Effort | Status |
|---|------|-----|--------|--------|
| 1.1 | **Post-generation filtering** | "3 sweaters together" kills trust. Filter impossible combos before showing. | Medium | ⏳ |
| 1.2 | **Garment physics in prompt** | Strengthen system prompt with layering/tucking/proportion rules. | Low | ⏳ |

**Evidence:** Alexi generated 6 outfits, saved 0, churned. Dana complained about 3 sweaters. Neither trusts complete outfit generation.

---

### Tier 2: Build Taste Learning Infrastructure (P1)
*This is what makes Dana's ChatGPT sticky.*

| # | Item | Why | Effort | Status |
|---|------|-----|--------|--------|
| 2.1 | **Free-text feedback field** | Replace checkbox feedback. "Any thoughts?" after save/dislike. | Low | ⏳ |
| 2.2 | **`get_feedback_patterns` enhancement** | Extract patterns from free text → feed to agent. | Medium | ⏳ |
| 2.3 | **"This is very you" signals** | Agent references learned patterns in output. | Medium | ⏳ |

**Evidence:** Dana's ChatGPT says "not the most Dana version" — that's why she keeps using it.

---

### Tier 3: Reduce Onboarding Friction (P1)
*67% drop-off at welcome→words. Kate was "mystified."*

| # | Item | Why | Effort | Status |
|---|------|-----|--------|--------|
| 3.1 | **Visual style picker** | Show mood boards, user picks 3. App gives them the words. | Medium | ⏳ |
| 3.2 | **5-item MVP validation** | Dimple loved synthetic suggestions. Test smaller wardrobes. | Low | ✅ Works |

**Evidence:** Kate: "I didn't know my style until ChatGPT gave me words."

---

### Tier 4: Progressive Visualization UX (P2)
*Kate's core ask: see outfit on model BEFORE deciding to save.*

| # | Item | Why | Effort | Status |
|---|------|-----|--------|--------|
| 4.1 | **Auto-trigger visualization** | Generate in background after outfit creation. | Medium | ⏳ |
| 4.2 | **Progressive reveal** | Show outfit card immediately. "See on model" appears when ready. | Medium | ⏳ |
| 4.3 | **Runway retry logic** | Handle intermittent `BAD_OUTPUT` failures. | Low | Plan exists |

**Evidence:** Kate: "Save felt like confirming it was worth saving, which I wouldn't know until I tried it on."

---

### Tier 5: Trust-Building Sequence (P3)
*Kate wants "fashion therapist" — sequence matters more than features.*

| # | Item | Why | Effort | Status |
|---|------|-----|--------|--------|
| 5.1 | **Reorder first message** | Start with empathy: "What's one piece you love but never wear?" | Low | ⏳ |
| 5.2 | **Diagnostic mode** | "What's not working about this outfit?" before generating new. | Medium | ⏳ |

**Evidence:** Kate: "I think I need a fashion therapist and getting me to share would help build trust."

---

### NOT Prioritized (Explicitly Deferred)

| Item | Why Defer |
|------|-----------|
| Pinterest API integration | Nice to have, doesn't fix core problems |
| iOS native app | Distribution doesn't matter if product doesn't retain |
| More acquisition (promo video) | "Growth can't fix a product people don't want" |
| Full chat-based onboarding | Sequence matters more than full feature |
| Calendar/weather integration | Validate daily usage first |

---

### The Strategic Sequence

```
Phase 1: Stop breaking trust
    → Post-gen filtering + physics prompt tuning
    → Users stop seeing obviously broken outfits

Phase 2: Start learning taste
    → Free-text feedback + pattern extraction
    → App begins to "know" users

Phase 3: Smooth the funnel
    → Visual onboarding + 5-item MVP
    → More users get to the "aha" moment

Phase 4: Enhance the experience
    → Progressive visualization
    → "See before save" unlocked

Phase 5: Deepen the relationship
    → Fashion therapist sequence
    → Diagnostic mode
```

---

### The Eigenquestion

> "Does fixing garment physics + adding taste learning make this a product users would miss?"

If yes → invest in distribution
If no → keep iterating on core

---

## 👥 User Research (Jan-Feb 2026)

### Users Interviewed

| User | Profile | Key Insight |
|------|---------|-------------|
| **Dimple** | Busy professional, RTO context | Uses for purchase validation, not outfit generation |
| **Alexi** | 100+ items, churned | Doesn't trust physics, uses for single-item inspiration |
| **Kate** | Decision paralysis | Wants to "de-risk" before opening closet, needs trust first |
| **Dana** | Power user, trained ChatGPT | Stickiness = taste learning. "This is very you." |
| **Rana** | 50s, self-image gap | "I don't want to see my own picture." Aspiration > accuracy. |

### The Five Problems (from Kate & Dana)

1. **Visualization latency blocks "see before save"** — 60-90s too slow for first-look
2. **No taste learning loop** — Checkbox feedback teaches nothing
3. **Words are hard for style identity** — Visual selection preferred
4. **Trust-building before utility** — Fashion therapist vibe before styling
5. **Garment physics errors break trust** — AI can explain but won't avoid

### Jobs-to-be-Done (Actual vs Expected)

| User | Expected Job | Actual Job |
|------|--------------|------------|
| Dimple | Plan work outfits | Validate purchases ("buy smart") |
| Alexi | Generate complete outfits | Remember forgotten items, single-item inspiration |
| Kate | Get outfit suggestions | De-risk getting dressed, see before committing |
| Dana | Get styled | Get taste feedback, iterate on existing outfits |

---

## 👥 Design Partners / Collaborators (Historical)

### Mia Simon (Primary User / Design Partner)
- **Background**: Works with professional stylist (Roz Kaur), has curated capsule wardrobe
- **Problem**: Decision fatigue on daily execution despite having good clothes
- **Quote**: "Can get 60% there but needs help with final 40% (forgotten accessories, shoes)"
- **Use Case**: "Here's what I'm doing today - tell me what to wear" (school drop-off → investor meeting → coffee)
- **Value**: Product direction, real usage feedback, access to stylist principles
- **Status**: Will upload wardrobe and test, follow up in 2 weeks

### Charity Lu (Technical Co-Builder)
- **Background**: 23 years Google Search, joining DeepMind/Meta AI, wants hands-on AI building experience
- **Expertise**: Search algorithms, subjective evaluation, AI stack
- **Offers**: Manual evaluation, dynamic prompting, try-on API research
- **Quote**: Connected problem to Google's "subjective UGC" work
- **Value**: Technical depth, Google AI expertise, evaluation systems
- **Status**: Will test product and potentially collaborate on building

---

## 📋 Historical: Nov 2025 Sprint (Completed)

<details>
<summary>Click to expand Nov 2025 sprint details (archived)</summary>

### Occasion-Based Generation ✅
- Occasion selection with chips (business meeting, casual, date night, etc.)
- Full outfit generation working

### Complete the Outfit ✅
- Select anchor pieces, AI fills the rest
- Working in production

### Onboarding UX Improvements ✅
- Dynamic encouragement copy
- Category balance indicators

</details>

---

## 📊 Success Metrics (Feb 2026)

### Immediate (Next 2 Weeks)
- ⏳ Post-generation filtering implemented (no more "3 sweaters")
- ⏳ Free-text feedback field added
- ⏳ At least 1 user says "it gets me now"

### Medium Term (1 Month)
- ⏳ Visual onboarding tested with 2+ users
- ⏳ Taste learning patterns visible in agent output
- ⏳ Kate/Dana use it weekly

### Long Term (2-3 Months)
- ⏳ Users trust complete outfit generation
- ⏳ "Would you miss this if it disappeared?" → "Very disappointed"
- ⏳ Clear path to monetization (taste learning as premium feature?)

---

## 🔄 Deferred / On Hold (Feb 2026)

### Explicitly NOT Doing
- ⏸️ **Pinterest API integration**: Doesn't fix core trust/taste problems
- ⏸️ **iOS native app**: Distribution doesn't matter if product doesn't retain
- ⏸️ **More acquisition tactics**: "Growth can't fix a product people don't want"
- ⏸️ **Full chat-based onboarding**: Sequence > feature
- ⏸️ **Calendar/weather integration**: Validate daily usage first

### Completed (Historical)
- ✅ **Save Outfits Feature**: Implemented Nov 2025
- ✅ **Agent-Native Architecture**: 32 primitives, Jan 2026
- ✅ **SMS/WhatsApp Flow**: Working, ~21s E2E
- ✅ **Visualization**: Runway Gen-4 integrated
- ✅ **GPT-5.2 Upgrade**: Faster + better quality

---

## 📝 Decision Log

### Active Decisions
1. ⏳ **Charity collaboration structure?** → PENDING (discuss after she tests)
2. ⏳ **Encode Roz's stylist principles?** → PENDING (waiting for Mia to share notes)
3. ⏳ **Pricing model?** → PENDING (validate usage first)
4. ⏳ **B2B2C stylist channel?** → PENDING (validate product first)

### Recent Decisions (Nov 7)
- ✅ **Challenge items vs occasion-based?** → DECIDED: Occasion-based is P0
- ✅ **Build P1 vs P2a first?** → DECIDED: Build both in parallel (complement each other)
- ✅ **Over-index on Mia's feedback?** → DECIDED: No, but her use case aligns with builder-user needs
- ✅ **Virtual try-on priority?** → DECIDED: P3, defer until core validated

### Previous Decisions (Oct 22)
- ✅ **Demo vs personal wardrobe?** → DECIDED: Personal wardrobe
- ✅ **5-7 vs 10 items?** → DECIDED: 10 items minimum, no hard cap
- ✅ **URL-based multi-user?** → DECIDED: Yes (simple, works for testing)

---

## 🎨 Design Principles

### Core UX Principles
1. **Reduce mental load**: Decision made for you, complete, ready to go
2. **Visual guides**: Show the outfit, don't just describe it
3. **Complete outfits**: Include shoes, accessories, outerwear (not just top/bottom)
4. **Daily utility**: Make it easy to use every morning
5. **Forgiving UX**: Imperfect photos OK, easy to adjust suggestions

### From Mia's Feedback
- "Way more polished than expected" = quality bar to maintain
- "Ease of following visual guides without mental load" = core value
- "Can use as blueprint and adjust" = give flexibility, not rigidity

### From Stylist Insights (Roz Kaur)
- "Do you live a white blazer life?" = match suggestions to actual lifestyle
- Breaking repetitive buying patterns = show what they already own
- Focused capsule wardrobes = work with 10-15 pieces, not full closet
- Texture/layering techniques = suggestions should teach subtly

---

## 🚀 Immediate Next Actions (Feb 2026)

### This Week: Trust Foundation

1. **Post-generation filtering** (P0)
   - [ ] Define rules for impossible combos (3 sweaters, 2 bottoms, etc.)
   - [ ] Add validation layer before showing outfits to user
   - [ ] Log filtered outfits for debugging

2. **Garment physics prompt tuning** (P0)
   - [ ] Review current system prompt for physics rules
   - [ ] Add specific rules: tucking bulk, layering proportions, etc.
   - [ ] Test with known failure cases (Alexi's ruffled shirt, Dana's sweaters)

3. **Free-text feedback field** (P1)
   - [ ] Add "Any thoughts?" field after save/dislike
   - [ ] Store in feedback primitives
   - [ ] Start collecting training data

### Next Week: Taste Learning

4. **Pattern extraction from feedback**
   - [ ] Parse free-text feedback for patterns
   - [ ] Feed patterns to `get_feedback_patterns` primitive
   - [ ] Test: does agent reference patterns in output?

5. **Visual onboarding prototype**
   - [ ] Create 6-9 mood board options
   - [ ] Build selection UI
   - [ ] Test with Kate/Dana

---

## 💭 Open Strategic Questions

1. **Monetization**:
   - When to introduce pricing? (after seeing value vs before)
   - What's the right price point? ($10-15/month? $5? $20?)
   - Should there be a free tier?

2. **Stylist Channel**:
   - Can we partner with stylists to recommend the app?
   - What would stylists need? (Client management? Progress tracking?)
   - Is there a B2B2C business model here?

3. **Tech Stack**:
   - Stay with Streamlit or migrate to web app?
   - Mobile native needed or is web good enough?
   - When does Streamlit become the bottleneck?

4. **Team & Collaboration**:
   - What does Charity want out of this? (learning, building, equity?)
   - Should we bring on other collaborators?
   - Is this a side project or a company?

---

## 📚 Reference: Previous Insights

**Oct 18-19 Breakthrough**:
- "Seeing outfit on a person makes it WAY more exciting" - Runway validation
- Shifted from builder to user of own product - unlocked true product intuition

**Nov 7 Breakthrough**:
- "Tell me what to wear for THIS occasion" > "Style my challenge items"
- Mental load reduction is the moat, not style education
- Complement stylists, don't compete with them

---

## 🏗️ Architecture & Technical Decisions

### Current Tech Stack (Streamlit-based)
**Status**: ⚠️ Needs migration
**Issues Identified** (Nov 16, 2025):

1. **Performance Problems (Streamlit Limitations)**:
   - Page load latency: 1-2s between pages (full Python script reruns)
   - Button flicker/duplicate UI during transitions (FOUC - Flash of Unstyled Content)
   - Scroll position not preserved (Streamlit rerun lifecycle)
   - Bottom buttons covered by browser bar (CSS safe-area conflicts)
   - Evidence: 100+ mobile screenshots show 4+ seconds blank screens, janky UI

2. **Mobile Polish Issues**:
   - Excessive spacing on mobile (gaps between elements too large)
   - Font sizes too large (titles appear 36-40px on mobile)
   - Images too large (belt photo takes entire screen width)
   - CSS fixes attempted but keep breaking on Streamlit reruns

3. **AI Quality Issues** (Fixed):
   - ✅ AI generated invalid outfits (two bottoms) - Fixed with validation function
   - ✅ Multi-occasion copywriting unclear - Fixed with updated copy
   - ✅ Feedback UX too laborious - Fixed with radio/checkboxes

**Root Cause**: Streamlit is a prototyping tool, not a production framework. Every interaction triggers full page reruns, CSS re-injection, and DOM rebuilding.

---

### Architecture Migration Decision (Nov 16, 2025)

**DECIDED**: Migrate to FastAPI (backend) + Next.js (frontend)

**Rationale**:
1. **Fixes performance**: React eliminates full page reruns (0ms navigation vs 1-2s)
2. **Mobile polish**: Full control over CSS, safe-area, responsive design
3. **Future-proof**: Same REST API works for web AND native app later
4. **Reuses logic**: 100% of Python styling code (style_engine.py, wardrobe_manager.py) transfers

**Timeline**: 2-3 weeks
- Week 1-2: FastAPI backend + RQ workers
- Week 2-3: Next.js frontend (mobile-first)
- Week 3: Polish + dogfooding

**Deployment**:
- Vercel (Next.js frontend) - auto-deploy from GitHub
- Railway (FastAPI backend) - auto-deploy from GitHub
- Upstash (Redis for job queue) - serverless
- **Total dashboards: 3** (manageable DevOps)

**Out of Scope for Phase 1**:
- PostgreSQL (still using S3 + JSON)
- Pre-compute/scheduled jobs (Phase 2)
- Advanced homepage design (iterate after migration)

---

### Migration Implementation Plan (Nov 17, 2025)

**Status**: 🚀 In Progress (Cursor implementing)

**Tech Stack Decisions** (aligned with Cursor):

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Backend Framework** | FastAPI | Python async, REST API, reuses existing code |
| **Background Jobs** | RQ (Redis Queue) | Lightweight, persistent, retryable (vs Celery overkill) |
| **Frontend Framework** | Next.js + TypeScript | Mobile-first React, automatic code splitting |
| **Styling** | Tailwind CSS | Mobile-first utility classes, fast iteration |
| **API Pattern** | REST + polling | Simple, mobile-friendly, debuggable |
| **Image Handling** | Client compression + Next.js Image | Fast uploads, automatic optimization |
| **Repository** | Separate repo | Protect production, easier iteration |
| **Testing** | Manual + smoke tests | Fast for Phase 1, E2E in Phase 2 |

**Performance Bottleneck Analysis**:

Current outfit generation latency breakdown:
- **OpenAI API call**: 15-20s (GPT-4o with complex Style Constitution prompt)
- **Prompt construction**: 100-200ms (negligible)
- **Post-processing**: 500ms-1s (JSON parsing, item matching, validation)
- **Total**: 20-30s

**Why 20s+ is acceptable for Phase 1**:
- ✅ Non-blocking (job queue returns job_id instantly)
- ✅ Frontend shows progress/loading state
- ✅ User can browse other parts of app while waiting
- ❌ NOT acceptable: Blocking UI like current Streamlit

**Phase 2 optimization approaches** (deferred):
1. Streaming response (perceived latency: ~7s to first outfit)
2. Parallel generation (actual latency: ~8-10s, 3x API cost)
3. Caching + smart prompts (latency: <5s for cache hits)

**Deployment URLs**:

Frontend (user-facing):
```
https://style-inspo.vercel.app/?user=peichin
```

Backend API (internal):
```
https://style-inspo-api.up.railway.app
```

**Multi-user approach**: Keep query params (`?user=peichin`) for Phase 1
- Zero migration complexity
- Easy friend testing
- Can upgrade to path-based (`/peichin`) or subdomain (`peichin.styleinspo.com`) in Phase 2

**Custom domain**: Deferred to Phase 2 (keep `.vercel.app` for now)

---

### Mobile Web vs Native App Decision

**DECIDED**: Mobile web first, native app later

**Tradeoffs Analysis**:

| Factor | Mobile Web | Native App |
|--------|------------|------------|
| Iteration speed | ✅ Fast (no app store) | ❌ Slow (approval delays) |
| User access | ✅ URL only | ❌ Install required |
| Performance | ⚠️ Good enough | ✅ Best |
| Gestures | ⚠️ Limited | ✅ Full native |
| Offline mode | ❌ No | ✅ Yes |
| Push notifications | ❌ No | ✅ Yes |
| Development time | ✅ 2-3 weeks | ❌ 4-6 weeks |

**Migration Path**:
- Phase 1: Mobile web (FastAPI + Next.js)
- Phase 2: PWA improvements (offline, install prompt)
- Phase 3: React Native (when daily usage + offline/push requests emerge)

**What Transfers to Native**:
- ✅ 100% backend (FastAPI REST API)
- ✅ 100% business logic (styling, AI, validation)
- ✅ 95% UI (same flows, layouts)
- ❌ 5% polish (rebuild for native gestures, animations)

**Doors This Closes**:
- Native app performance ceiling (but PWA gets 80% there)
- Native OS integrations (widgets, share sheets) - can add later

**Doors This Opens**:
- ✅ Faster iteration (no app store reviews)
- ✅ Lower barrier to entry (URL > install)
- ✅ Same codebase for desktop/tablet too

---

### Phase 2: Pre-Compute Vision (Future)

**Status**: ⏸️ Deferred until Phase 1 complete
**Goal**: Zero-latency morning outfit experience

**User Experience**:
```
User wakes up at 7am
  ↓
Opens app at 7:15am
  ↓
Homepage INSTANTLY shows:
  - "3 outfits ready for your day"
  - Based on: today's weather, calendar events, typical routine
  ↓
User taps one → Wearing it in 30 seconds
```

**vs Current (Reactive Model)**:
```
User opens app
  ↓
Picks occasions manually
  ↓
Waits 20-30s for AI generation
  ↓
Total time: 2-3 minutes
```

**Why This Is The Moat**:
- Every competitor is reactive (requires user input)
- Proactive = anticipatory AI = feels magical
- Aligns with "busy women don't have time" insight

**Technical Requirements**:
1. **Database** (PostgreSQL): Store pre-computed outfits with freshness/context
2. **Job Queue** (Celery upgrade from RQ): Nightly batch jobs for all users
3. **Context Predictor**: Weather API + calendar sync + pattern learning
4. **Caching Layer** (Redis): <100ms homepage load with pre-computed results
5. **Scheduled Jobs** (APScheduler): 11pm nightly generation

**When to Build**:
- After migrating to FastAPI + Next.js (Phase 1 complete)
- After daily usage validated (you're using it every morning)
- After pattern data collected (know what occasions are common)

**Estimated Timeline**: 2-3 weeks after Phase 1

---

### Homepage Design Ideas (Deferred)

**Status**: ⏸️ To be decided after migration
**Goal**: Define ideal returning user experience

**Current Thinking** (Nov 16):
- **Saved outfits carousel**: Context-aware (filter by today's weather)
- **Two CTAs**: "What should I wear today?" (primary) + "Start with a piece" (secondary)
- **Hamburger menu**: All secondary features (profile, settings, disliked)
- **Progressive disclosure**: Show features only when user can use them

**Open Questions**:
- Visual hierarchy: Saved outfits above or below CTAs?
- Pre-computed outfits placement (when Phase 2 built)?
- Bottom nav vs hamburger for key features?

**Decision Approach**:
1. Ship FastAPI + Next.js with current dashboard as baseline
2. Dogfood the migrated app daily
3. Iterate on homepage based on real usage patterns

---

---

**Last Updated**: Feb 4, 2026
**Next Review**: After Tier 1 & 2 implementation
**Owner**: Pei-Chin
