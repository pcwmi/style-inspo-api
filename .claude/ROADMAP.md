# Style Inspo Product Roadmap

*Last updated: 2025-12-01 (Post-Migration)*

## Current Status
- ✅ **Migration Complete** - FastAPI backend + Next.js frontend deployed and working E2E
- ✅ **Buy Smarter Feature** - URL paste flow working with smart extraction algorithm
- 🎯 **Current Phase**: Quality, Polish & Growth (Post-Feature-Building)
- 🔍 **Focus Areas**: Eval quality, product polish, business model, onboarding flow

---

## 🎯 Core Strategy (Nov 7 Pivot)

**The Insight**: People want their decision made for them, complete, with zero mental load.

**What Users Actually Want**:
- "Tell me what to wear TODAY for THIS occasion"
- "Complete my outfit - I'm 60% there but need the finishing touches"
- "Show me what I already own so I don't buy duplicates"

**What They DON'T Want**:
- More inspiration (Pinterest has that)
- Style education (stylists do that)
- Shopping suggestions (apps push that)

### The Moat: Mental Load Reduction

**Not**: "Here are some outfit ideas" (low value)
**But**: "Here's THE outfit, fully complete, just put it on" (high value)

The more we reduce friction between "I need to get dressed" → "I'm dressed and feel good," the more valuable we become.

---

## 👥 Design Partners / Collaborators

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

## 📋 Active Sprint: Occasion-Based Outfit Completion

### **Phase 1: Occasion-Based Generation** - Week 1
**Status**: 🎯 Next to build
**Priority**: P0 (Core value prop)

**Goal**: "Tell me what to wear for [occasion]" as the main entry point

**What Gets Built:**
- Occasion selection with default chips:
  - Business meeting
  - Casual day
  - Date night
  - Weekend errands
  - Formal event
  - School pickup
- Natural language fallback: "school drop-off then investor meeting then coffee"
- Full outfit generation (top, bottom, shoes, accessories, outerwear)
- Visual presentation of complete outfit

**Why This First:**
- Mia's #1 use case
- Daily utility value (not one-off)
- Reduces mental load (core moat)
- Easy to explain and demo

**Success Metrics:**
- Mia uses it daily for a week
- She actually wears the suggested outfits
- She says "this saved me time this morning"

---

### **Phase 2: Complete the Outfit** - Week 1-2
**Status**: 🎯 Next to build (parallel with Phase 1)
**Priority**: P1 (Builder-user validated)

**Goal**: "I want to wear this blue sweater - complete the outfit for me"

**What Gets Built:**
- Select 1-2 "anchor pieces" (must-have items for today)
- AI fills in the rest (complementary pieces, shoes, accessories)
- Reuses existing challenging item flow code (just allow multi-select)

**Why This Matters:**
- Addresses Mia's "60% to 40%" gap
- Builder (me) wants this for daily use
- Code already exists, simple to implement
- Different use case from occasion-based (starts with piece not occasion)

**Success Metrics:**
- I use this daily myself
- Mia tries it when she has a specific piece she wants to wear
- Complete outfit feels cohesive (not random accessories)

---

### **Phase 2.5: Onboarding UX Improvements** - TBD
**Status**: ⏸️ Designed, ready to implement
**Priority**: P1 (UX Designer validated - Dec 7, 2025)

**Goal**: Make the 10-photo upload requirement feel lighter, faster, and more motivating

**Context from UX Critique:**
- 10-photo minimum is firm product constraint (required to unlock value)
- Users most likely to abandon during "slog zone" (photos 3-7)
- Need motivation design, not just friction removal

**Tier 1 Improvements (High Impact, Low Effort - 2-4 hours each):**

1. **Dynamic Encouragement Copy**
   - Change header/subheader based on photo count progress
   - 0 photos: "Welcome back [Name]!"
   - 3-4 photos: "Great start! Keep going..."
   - 5-7 photos: "You're over halfway there!"
   - 8-9 photos: "Almost done!"
   - 10+ photos: "Your closet is ready!"
   - **Impact**: Reduces perceived effort by 20-30% through motivational anchoring

2. **"Why 10 Photos?" Transparency Callout**
   - Dismissible info callout explaining minimum requirement
   - "Our AI needs at least 10 pieces to create outfits that feel like you..."
   - **Impact**: Reduces friction perception by 15-25% through rationale disclosure

3. **Micro-Celebration at Photo 5**
   - Brief celebratory modal/toast when user hits halfway point
   - "Halfway there! 🎉 Just 5 more and you'll unlock..."
   - **Impact**: Reduces abandonment at photos 5-7 by 30-40%

**Tier 2 Improvements (Medium Impact, Medium Effort - 4-8 hours):**

4. **Category Balance Visual Indicator**
   - Show category breakdown: "3 tops | 2 bottoms | 1 shoes | 0 accessories"
   - Gentle nudge: "Tip: Add shoes or accessories for more outfit variety"
   - **Impact**: Improves first outfit quality by 40-60% through better distribution

5. **Preview of Value at Photo 8-9**
   - Show blurred teaser of outfit generation
   - Creates curiosity gap to motivate completion
   - **Impact**: Increases completion rate by 20-30% for users who reach photo 8

**Success Metrics to Track:**
- Upload completion rate by photo count (track abandonment at 3, 5, 7, 9 photos)
- Time spent on upload page by photo count
- Category distribution quality (% users with balanced mix)
- First outfit generation quality rating

**Alternative Ideas (Research/Test Later):**
- Social proof testimonials during upload
- Upload challenge framing ("The 10-Piece Challenge")
- Quick start mode with deferred completion (V2)

**Why P1:**
- Directly impacts onboarding completion (core activation metric)
- Low effort implementations (Tier 1 = 6-10 hours total)
- Evidence-based from UX principles (Peak-End Rule, Goal-Gradient Effect, Fogg Behavior Model)
- Can validate quickly with returning users

**Files to Update:**
- `/frontend/app/upload/page.tsx` - Upload page component
- Consider extracting dynamic copy to config for easy iteration

---

### **Phase 3: Natural Language Closet Search** - Week 2
**Status**: ⏸️ Pending Phase 1-2 completion
**Priority**: P2 (Prevents duplicate buying)

**Goal**: "Show me all my grey sweaters" / "Do I have a white blazer?"

**What Gets Built:**
- Natural language search on existing wardrobe metadata
- Filter by: category, color, brand, style tags
- Visual grid of matching items
- "You already own 5 grey sweaters" before shopping

**Why This Matters:**
- Mia + Heather both mentioned duplicate buying problem
- Enables better anchor piece selection for Phase 2
- ROI justification: "$200 saved > $10/month subscription"
- Simpler to build than outfit generation

**Success Metrics:**
- Users check before shopping
- Reduced duplicate purchases (self-reported)
- Increased awareness of what they own

---

### **Phase 4: Virtual Try-On (Future)** - TBD
**Status**: ⏸️ Deferred until demand validated
**Priority**: P3 (Nice-to-have)

**Goal**: "Try this new item I'm considering with my existing wardrobe"

**What Gets Built:**
- Product image upload or URL
- Runway visualization with new item + existing pieces
- See outfit on model before buying

**Why Deferred:**
- Most complex to build (try-on API, product images)
- Unclear if this is core value or nice-to-have
- Validate daily usage first, then add shopping features

---

## 🏗️ Build Order & Timeline

**Week 1: Core Experience**
- Day 1-2: P0 - Occasion-based chips + outfit generation
- Day 2-3: P1 - Complete the outfit (anchor pieces + fill)
- Day 4-5: Testing with Mia, iterate

**Week 2: Enhanced Search + Iteration**
- Day 1-2: P2 - Natural language closet search
- Day 3-5: Mia/Charity feedback, bug fixes, polish

**Week 3+: Scale & Iterate**
- More user testing (2-3 additional people)
- Build based on actual usage patterns
- Consider P3 (try-on) if demand emerges

---

## 💡 Key Insights from Demos (Nov 7, 2025)

### Product Insights

**The Pivot:**
| Original Assumption | Actual Reality |
|---------------------|----------------|
| Challenge items as hero feature | Daily occasion-based as hero |
| "Help me wear things I never wear" | "Help me complete outfits without mental load" |
| Styling education | Execution assistance |
| One-off outfit generation | Daily utility tool |
| Compete with stylists | Complement stylists |

**Mia's 60% to 40% Problem:**
- She can get 60% of the way to a good outfit herself
- Needs help with final 40% (forgotten accessories, shoes)
- Has good clothes but wears "same sweater 4 days straight"
- **This is our sweet spot**: Daily execution for people who know their style

**Stylist Integration Opportunity:**
- Stylists do strategic work (capsule curation, style education, periodic sessions)
- We do tactical work (daily outfit suggestions, on-demand execution)
- **B2B2C potential**: Stylists recommend app to clients to make their work stick

### User Personas Emerging

**Primary User:**
- Women who work with stylists OR curate their own wardrobes
- Have good clothes, know their style
- Decision fatigue on daily execution
- Want "complete the outfit" not "teach me style"

**Use Cases (Priority Order):**
1. **Daily**: "What should I wear for [occasion]?"
2. **Completion**: "I want to wear this piece - finish the outfit"
3. **Prevention**: "Do I already own this before I buy it?"
4. **Challenging items**: "Help me wear this expensive thing I never wear"

**NOT the user:**
- People who need basic style education (different product)
- People who don't care about clothes (no problem to solve)
- People who already have effortless style (don't need help)

### Collaboration Paths

**Two Different Validations:**
1. **Charity**: Technical credibility (someone with 23 years Google Search experience wants to build this)
2. **Mia**: User demand (paying for stylists, will upload wardrobe and use daily)

**Strategic Decision Needed**: What does Charity collaboration look like?
- Advisor (occasional brainstorming)?
- Co-builder (regular pairing sessions)?
- Co-founder (equity conversation)?

---

## 📊 Success Metrics

### Immediate (Next 2 Weeks)
- ✅ Do Mia and Charity upload their wardrobes? (activation)
- ⏳ Do they generate outfits? (usage)
- ⏳ Do they come back? (retention)
- ⏳ What do they actually WEAR? (real value validation)

### Medium Term (1-2 Months)
- Daily usage: Do they check the app before getting dressed?
- Outfit quality: Are suggestions wearable or random?
- Mental load reduction: "This saved me time" feedback
- Duplicate prevention: "I didn't buy X because I saw I already own it"

### Long Term (3-6 Months)
- **Willingness to pay**: $10-15/month make sense?
- **ROI justification**: Saved money > subscription cost?
- **Word of mouth**: Do they tell friends?
- **Stylist validation**: Do stylists recommend the app?

---

## 🔄 Deferred / On Hold

### From Previous Roadmap (Oct 22)
- ⏸️ **Enhanced Runway Visualization**: Deferred until core daily usage validated
- ⏸️ **Save Outfits Feature**: Now implemented! (Nov 6)
- ⏸️ **Proper Authentication**: URL-based good enough for now
- ⏸️ **Mobile Native App**: Web works, reassess if mobile UX becomes blocker

### New Items to Defer
- ⏸️ **Challenge Items as Primary Flow**: Moved to secondary use case
- ⏸️ **Style Education Features**: Users who work with stylists don't need this
- ⏸️ **Shopping Integration**: Focus on using what you own, not buying more (for now)

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

## 🚀 Immediate Next Actions (Dec 2025)

### **NEW PHASE: Quality, Polish & Growth**

**Status**: ✅ Feature building complete → 🎯 Focus on quality & strategy

**What Changed (Dec 1 Update):**
- ✅ Migration to FastAPI + Next.js: DONE (tested E2E, all key flows working)
- ✅ Buy Smarter feature: DONE (URL paste + smart extraction working)
- ⏳ Eval system: IN PROGRESS (haven't reviewed results, no model conclusion yet)
- 🎯 NEW INSIGHT: "Built enough features, time for quality/polish/business"

---

### Priority 1: Eval Quality & Model Selection (Week 1)
**Status**: 🎯 ACTIVE - Complete the eval work
**Goal**: Make data-driven decisions on outfit quality

**Tasks:**
1. **Review eval results** (Dec 1-2)
   - [ ] Analyze `eval_20251128_124930/` results with updated prompts
   - [ ] Compare `gemini_comparison/` results
   - [ ] Document: Which model performs better? On what dimensions?
   - [ ] Extract 3-5 specific insights (e.g., "Gemini better at X, GPT better at Y")

2. **Turn insights into improvements** (Dec 3-4)
   - [ ] Pick ONE specific weakness from eval (e.g., "shoes don't match occasion")
   - [ ] Update prompt/logic in `style_engine.py` to address it
   - [ ] Re-run eval on THAT specific scenario
   - [ ] Validate improvement

3. **Model decision** (Dec 5)
   - [ ] Decide: Stick with GPT-4o, switch to Gemini, or hybrid approach?
   - [ ] Document rationale (quality vs cost vs latency trade-offs)
   - [ ] Update production config if switching models

**Success Criteria:**
- Clear answer to "Which model should we use and why?"
- At least 1 measurable quality improvement from eval insights
- Documented eval → improvement feedback loop for future use

---

### Priority 2: Onboarding Flow Optimization (Week 1-2)
**Status**: 🎯 ACTIVE - Migration done but onboarding unclear
**Goal**: Define the ideal new user experience

**Open Questions to Answer:**
- What's the minimum viable wardrobe? (10 items still right?)
- What's the onboarding sequence? (Upload → profile → first outfit?)
- Mobile photo upload UX good enough or needs polish?
- Do users understand what to upload? (Need examples/guidance?)

**Tasks:**
1. **Dogfood the current onboarding** (Dec 2-3)
   - [ ] Fresh install: Go through onboarding as new user
   - [ ] Time each step, note friction points
   - [ ] Document: Where did I get confused? What felt slow?

2. **Test with 1-2 fresh users** (Dec 4-6)
   - [ ] Send app to someone who hasn't seen it (not Mia/Charity)
   - [ ] Watch them go through onboarding (screen share or in-person)
   - [ ] Document drop-off points and confusion

3. **Iterate based on findings** (Dec 7-8)
   - [ ] Update onboarding copy/flow based on learnings
   - [ ] Add guidance if needed (photo examples, progress indicators)
   - [ ] Re-test with same user

**Success Criteria:**
- New user can complete onboarding in <10 mins
- Clear documentation of "ideal onboarding flow v2"
- At least 1 user gives feedback "this was easy to understand"

---

### Priority 3: Product Polish (Ongoing)
**Status**: 🎯 ACTIVE - Post-migration refinement
**Goal**: Fix bugs, improve UX, raise quality bar

**Tasks:**
- [ ] Daily dogfooding (use app every morning, document bugs)
- [ ] Mobile polish pass (fonts, spacing, safe-area edge cases)
- [ ] Error handling audit (what happens when AI fails? when S3 is down?)
- [ ] Performance check (any latency regressions from migration?)
- [ ] Copy audit (does all copy match COPY_GUIDELINES.md tone?)

**Success Criteria:**
- You use the app daily without workarounds
- Mobile experience feels "polished" not "functional"
- All error states handled gracefully

---

### Priority 4: Business Model & Growth Strategy (Week 2-3)
**Status**: ⏳ PENDING - After quality foundation solid
**Goal**: Clarify monetization path and growth approach

**Strategic Questions to Answer:**
1. **Monetization timing**
   - When to introduce pricing? (now vs after more validation)
   - Free tier or paid-only?
   - Trial period? (7 days, 14 days, first outfit free?)

2. **Pricing model**
   - Per-outfit? Subscription? One-time payment?
   - What's the right price? ($5/month, $10/month, $15/month?)
   - How to communicate value/ROI?

3. **Growth channels**
   - Stylist B2B2C channel? (Roz Kaur partnership?)
   - Word of mouth? (referral system?)
   - Paid ads? (Instagram, TikTok?)
   - Content marketing? (style tips, outfit inspiration?)

4. **User acquisition**
   - Who's the ICP? (women who work with stylists? busy professionals?)
   - What's the acquisition funnel? (landing page → demo → signup?)
   - How do we measure PMF? (retention? NPS? word-of-mouth?)

**Approach:**
- [ ] Write out current thinking on each question (brain dump style)
- [ ] Research 3-5 comp apps (pricing, positioning, channels)
- [ ] Talk to Mia + Charity: "Would you pay? How much? Why?"
- [ ] Draft business model hypothesis doc

**Success Criteria:**
- Clear hypothesis on pricing model
- Clear hypothesis on primary growth channel
- Validation plan (how we'll test these hypotheses)

---

### DEFERRED (Explicitly Not Doing Now)

**Why:** Feature set is good enough. Focus on quality of what exists, not adding more.

- ⏸️ Pre-compute outfits (Phase 2 vision) - too early, need usage data first
- ⏸️ Advanced homepage design - iterate after real usage patterns emerge
- ⏸️ PostgreSQL migration - S3+JSON works fine for now
- ⏸️ Style education features - not core value prop
- ⏸️ Try-on API integration - nice-to-have, not must-have
- ⏸️ Calendar/weather integration - defer until daily usage validated

---

### Migration Retrospective (Completed Nov 17 - Dec 1)

**What Went Well:**
- ✅ FastAPI backend: All endpoints working, job queue reliable
- ✅ Next.js frontend: Mobile-first, fast navigation, no Streamlit jank
- ✅ Buy Smarter: Shipped alongside migration (scope creep but valuable)
- ✅ E2E testing: Caught issues before user-facing

**What Could've Been Better:**
- ⚠️ Timeline: 2 weeks → ~2 weeks (on track but felt long)
- ⚠️ Testing: Could've caught more edge cases with formal test plan
- ⚠️ Scope: Buy Smarter added mid-migration (extended timeline)

**Key Learnings:**
- Migration unlocked polish opportunities (CSS control, performance)
- Feature work during migration = scope creep (but sometimes worth it)
- E2E testing invaluable even without formal framework

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

## 📊 Updated Success Metrics (Dec 2025)

### Immediate (Next 2 Weeks)
**Focus**: Quality & Polish
- ⏳ Eval results reviewed and model decision made
- ⏳ At least 1 quality improvement shipped from eval insights
- ⏳ Onboarding flow tested with 2+ fresh users
- ⏳ Daily dogfooding for 7+ days straight
- ⏳ Mobile polish pass complete

### Medium Term (2-4 Weeks)
**Focus**: User Testing & Business Model
- ⏳ Send new app to Mia and Charity for testing
- ⏳ Business model hypothesis documented
- ⏳ Pricing strategy decided
- ⏳ Primary growth channel identified
- ⏳ Willingness-to-pay validated (at least 2 users)

### Long Term (1-2 Months)
**Focus**: Early PMF Signals
- ⏳ 5+ active users (not just friends)
- ⏳ 3+ users using app 3+ times per week
- ⏳ At least 1 user says "I'd pay for this"
- ⏳ Clear answer to "stylist B2B2C channel viable?"
- ⏳ Documented path to 100 users

---

**Last Updated**: Dec 1, 2025
**Next Review**: After Eval & Onboarding work (Mid-Dec 2025)
**Owner**: Pei-Chin
