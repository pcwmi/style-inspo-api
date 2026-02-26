# Brain Dump - 2026-02-26

## 07:00 - Feedback Loop + Viz Quality Wrap-Up

### What We Did (3 Workstreams)

**Workstream 1: Positive + Negative Feedback in `get_feedback_patterns`** (SHIPPED)
- Agent was flying half-blind — only saw negative feedback (dislikes), never saw what users loved
- Added positive feedback from saved outfits (with reasons, worn status) alongside existing negatives
- Signal strength hierarchy: explicit dislikes (strongest) > explicit saves (strong) > save rate (useful) > GPT pattern guess (directional)
- Files: `backend/primitives/feedback.py`, `backend/agent/agent.py`, `backend/agent/tools.py`, `backend/agent/prompts.py`

**Workstream 2: Silent Feedback Persistence** (SHIPPED)
- Daily digest already computed "generated but not saved" patterns — but never persisted them
- Added `_persist_silent_feedback()` to `daily_analysis.py` — rolling 30-day window to S3 (`{user_id}/silent_feedback_patterns.json`)
- Added `_load_silent_feedback()` to `primitives/feedback.py` — loads into `get_feedback_patterns` response
- Agent now sees: `silent_patterns: { overall_save_rate: "7%", recent_pattern: "User rejects clashing colors...", last_updated: "2026-02-20" }`
- Backfilled data for heather (3 dates) and alexi (1 date)
- Latency impact: `get_feedback_patterns` went from ~2.1s to ~4.8s (~3s added for S3 load)

**Workstream 3: Visualization Quality — Brand Reference Trick** (SHIPPED)
- fal.ai Flux 2 Pro was exaggerating body size with honest descriptors ("size 10 curvy", "125 lbs curvy")
- Tested 3 approaches: raw descriptors (bad), full rewrite (broke skin tone), append-only (winner)
- Shipped one-line fix in `flux2pro.py:148`: append "Proportions similar to a J.Crew or Madewell catalog model." to descriptor
- Key insight: brand reference anchors body proportions without rewriting ethnicity/skin context

### Feedback Eval Infrastructure (NEW)
- Built `backend/tests/feedback_eval/` — generates outfits in "before" (negative only) vs "after" (full signals) mode
- Monkey-patches `_execute_tool` to control what feedback agent sees
- HTML review page with item images, star ratings, winner picker, agent reasoning
- Ran expanded eval: 9 prompts x 2 modes (heather x3, peichin x3, dana x3)
- Verdict: hard to tell if quality is meaningfully better from the eval alone — the outfits are reasonable in both modes. May need more user sessions to see the difference emerge naturally.

### Key Decisions
- Append-only for viz descriptors (don't rewrite, just anchor)
- Silent feedback as weakest signal tier (summary + rate, not raw data)
- Added "GATE: Before Running Evals" to CLAUDE.md — always generate outfit images, not just text

### What's Left / Next
- More real user sessions to see if feedback signals improve outfit quality over time
- Consider A/B testing in production (some users get full signals, some get negative-only)
- Backfill silent feedback for more users when daily digest runs
- Eval showed Dana's closet is small (lots of repeat pieces across outfits) — may need more items

---

## 14:30 - Editorial Flat-Lay Collage - Implementation Progress

### What We Built
Implemented Phase 1 of the editorial flat-lay collage system for SMS/MMS outfit delivery. This replaces the old rigid 2x2/2x3 grid collages with magazine-style flat-lay images inspired by MyMika Closet and Indyx.

### New Files
- `backend/services/bg_removal.py` — rembg wrapper with S3 caching. Removes backgrounds from item photos, caches results as PNGs. Parallel processing via ThreadPoolExecutor (4 workers). S3 download fix: uses StorageManager.load_file() for private S3 objects instead of plain HTTP requests.
- `backend/services/collage.py` — Complete rewrite from grid to body-silhouette layout engine. 1200x1600 canvas (3:4), JPEG quality 92. Items placed WHERE they'd be worn on the body.

### Modified Files
- `backend/agent/output.py` — SMSOutput now resolves item category metadata before calling collage generator
- `backend/main.py` — rembg model warm-up on startup (lifespan handler)

### Layout System (v3 - body silhouette)
- Outerwear: behind everything, offset left (z=0)
- Mid-layer: behind top, slight offset (z=1)
- Top/Dress: centered upper torso (z=2)
- Bottom: overlaps top at waist ~15% (z=3)
- Shoes: at feet, shifted left if bag present (z=4)
- Bag: hip height, offset right (z=5)
- Accessories: near neckline beside top (z=6)
- Drop shadows on all items for editorial depth
- Hanger cropping (top 12%) for hung garments

### What We Tried and Abandoned
- **Frontend CSS flat-lay** (Phase 2): Attempted CSS absolute positioning on OutfitCard.tsx and VisualizedOutfitCard.tsx. Looked terrible — rectangular photos with messy backgrounds can't look editorial no matter how positioned. Reverted all frontend changes. Flat-lay only works with bg-removed cutouts (server-side PIL).
- **flatlay.ts**: Created shared positioning logic file, then deleted it.

### Iterations
- v1: 600x800 canvas, basic stacking — too low quality, hangers visible, layout too literal
- v2: 1200x1600, hanger cropping for tops only — scarf floating above everything, pants still had hangers
- v3 (current): Body-silhouette layout, hanger cropping for all garments including bottoms, accessories near neckline

### Test Results (5 outfit collages generated)
Generated 5 diverse outfits: Smart Casual (5 items), Dress & Boots (3 items), Weekend Casual (4 items), Full Winter (6 items), Dressy Night Out (4 items).

**What's working well:**
- Body silhouette reads naturally — items flow top to bottom like a body
- Layering (outerwear behind top) looks good
- Accessories (earrings, necklace, scarf) sized and placed appropriately
- Waist overlap between top and bottom looks natural
- Shoes + bag balance at bottom

**Known issues remaining:**
1. Hangers still visible on some items (12% crop too conservative for items on thick hangers)
2. Dark items (black tote bag) render poorly after bg removal — become dark blobs
3. Sparse layouts for 2-3 item outfits (e.g. dress + boots has big gap)
4. No rotation applied yet (plan mentioned -5 to +5 degrees)

### Key Technical Decisions
- S3 caching of bg-removed PNGs avoids reprocessing (~3-4s first time, ~0.5s cached)
- Bypassed StorageManager.save_image() for S3 collage upload to avoid 800x800 thumbnail + quality 85 downgrade
- Used outfit_validator.get_slot() to classify items into body slots
- Graceful fallback: if rembg fails, original image used with RGBA conversion

---

## The Mira Rebrand: From Style Inspo to Mirror Moment

### What Happened

Full rebrand from "Style Inspo" to "Mira" — repositioning from outfit planning app to "the stylish friend you text." Landing page + frontend rename (not backend).

### The Positioning Shift

**Before:** "Style Inspo — AI Styling Assistant." Tool-centric, planning-mode, sounds like every other closet app.

**After:** "Mira — your stylist friend." Relationship-centric, text-first, owns the "second opinion" moment.

Key insight from brand strategy brief: The product isn't about outfit generation. It's about the universal moment of standing in front of a closet full of clothes and needing someone to tell you "yes, go" or "swap the shoes."

### Name: Mira

Chosen from candidates (Charis, Mira, Cleo, Thea). Mira = Spanish imperative "Look!", one letter from "mirror", universally pronounceable, warm. Tagline: "Mira — your stylist friend."

### Landing Page Structure (shipped)

1. **Hero:** "You have the clothes. You just need a second opinion." + phone mockup showing SMS conversation + "Meet Mira" CTA
2. **Proof:** "What it sounds like" — reused sms-iterate.mp4 and sms-inspo.mp4 videos
3. **How it works:** 3 honest steps (tell her who you are, show her your closet, text her when you need her) + "Most people finish setup in one Sunday morning"
4. **She remembers everything:** Closet view reframed as Mira's memory
5. **Social proof:** Real user quotes
6. **Bottom CTA:** "Your closet, your style, your Mira. 20 minutes once. Then it's just texting."

### The SMS vs Web Tension

From brain-dump-2026-02-13: "SMS is the Front Door, Web is the Living Room." The value is in texting but setup requires web (upload closet photos, ~20 min). This creates a promise/delivery gap.

**Growth expert scored original plan 5/10.** Key issues:
- CTA verb must match first action after click. "Start texting" → web upload = broken. Changed to "Meet Mira."
- Honest framing about setup is better than hiding it, but transparency isn't a conversion strategy.
- Maximum commitment (20 min) from minimum-trust users (first visit) is backwards.

**Tier comparison:** 5/10 (landing page only, ~1 day) → 7.5/10 (text-first entry, ~2-3 days) → 10/10 (zero-setup magic, ~1-2 weeks). Shipped 5/10, planning toward 7.5.

### Hero Copy Process

Original "The 15 seconds in front of the mirror just got easier" was rejected as insider baseball / IYKYK. Consulted user researcher, UX designer, and growth expert in parallel. All three converged:
- "Full closet, nothing to wear" is the universal entry point
- Phone mockup is the strongest asset — copy should amplify, not compete

Four finalists:
- **A: "You have the clothes. You just need a second opinion." (PICKED)** — Maps to texting-a-friend behavior.
- B: "Text a photo. Get dressed." — Ultra-concise.
- C: "Full closet. Nothing to wear. Sound familiar?"
- D: "Your closet is full. Your outfit is in there. Mira finds it."

### Files Changed

- `ShowcaseLanding.tsx` — Full rewrite: new structure, CSS phone mockup, new copy
- `layout.tsx` — Metadata: "Mira — your stylist friend"
- `get-started/page.tsx`, `login/page.tsx`, `DashboardClient.tsx` — "Style Inspo" → "Mira"
- `ShareImageGenerator.tsx` — Canvas text, share copy, filenames → Mira/textmira
- `lib/auth.ts`, `lib/api.ts` — Comment updates

### What's Next

1. **Text-first entry (7.5/10):** CTA shows phone number, Mira greets, sends setup link from within SMS
2. **Zero-setup magic (10/10):** Advice with just the photo sent, no closet needed upfront
3. **Domain:** textmira.vercel.app for now, peichinwang.com available for future
4. **OG image:** Still shows old branding — needs regeneration

### Key Learnings

- Three-agent consultation in parallel produces better copy than any single perspective. Convergence = signal.
- "Insider baseball" is the #1 risk when founders write copy. Mirror moment is real but founder language, not user language.
- Growth expert's rule: "the verb on the CTA must match the first action after the click."
- Kate's raw quote ("spend 30 minutes trying random shit on") is more vivid than any polished marketing line.
