# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Style Inspo is an AI-powered personal styling assistant that helps users create outfits from their existing wardrobe. The app is inspired by Allison Bornstein's "Wear it Well" methodology to generate personalized outfit combinations that honor the user's natural style while incorporating challenging pieces they struggle to wear.See **`PRODUCT_VISION.md`** and **`STYLE_CONSTITUTION.md`** to understand the broader context. 

## Current Priorities & Roadmap

**IMPORTANT**: For current sprint priorities, strategic decisions, and AI delegation strategy, see **`ROADMAP.md`** (if available)

To understand historical context, reference **`.claude/brain-dump*.md`** files to understand the progression of thinking and decisions.

**Current Phase (Oct 22, 2025)**: Mobile-First Quick Onboarding
- Validating mobile web photo upload UX (Phase 1)
- Building URL-based multi-user system for friend testing
- Core strategy: Skip demo → direct personal wardrobe upload → fast aha moment

Key decisions captured in ROADMAP.md:
- Skip demo mode (fashion is identity-driven, demo adds friction)
- Target 10 items minimum for quick onboarding
- Heavy AI delegation (85-90% AI-driven implementation)

## Architecture

**Core Components:**
- **`app.py`** - Main Streamlit application with UI layout and navigation
- **`style_engine.py`** - AI-powered outfit generation engine using OpenAI GPT
- **`wardrobe_manager.py`** - Photo upload, storage, and wardrobe item management
- **`style_profile.py`** - User style profile collection (three-word method + daily emotions)
- **`outfit_visualizer.py`** - Magazine-style outfit presentation and visualization
- **`ai_detection.py`** - AI content detection for uploaded images
- **`mock_wardrobe.py`** - Sample data for testing and fallback scenarios

**Data Management:**
- **`wardrobe_photos/`** - User-uploaded clothing photos organized by category
  - `regular_wear/` - Go-to pieces representing natural style
  - `styling_challenges/` - Items loved but difficult to style
- **`wardrobe_metadata.json`** - Structured metadata for all wardrobe items
- **`style_env/`** - Python virtual environment

## Development Commands

```bash
# Virtual environment (recommended)
source style_env/bin/activate  # Activate virtual environment
pip install -r requirements.txt  # Install dependencies

# Main application
streamlit run app.py            # Start the web interface with auto-reload

# Testing and development
python3 test_styling.py         # Test styling engine with sample data
python3 -c "import streamlit; print(streamlit.__version__)"  # Check Streamlit version

# Direct module testing
python3 -c "from style_engine import StyleGenerationEngine; print('Engine loaded')"
```

## E2E Testing with Playwright

Use the Playwright MCP for E2E testing when making UI changes or fixing bugs. **Test locally first**, using real user profiles.

**Local URLs:**
- Dashboard: `http://localhost:3003/?user=peichin`
- Profile: `http://localhost:3003/profile?user=peichin`
- Wardrobe: `http://localhost:3003/wardrobe?user=peichin`

**Production URLs:**
- Dashboard: `https://styleinspo.vercel.app/?user=peichin`
- Profile: `https://styleinspo.vercel.app/profile?user=peichin`

**E2E Testing Workflow:**
1. **Navigate** to the page being tested
2. **Interact** like a real user would - click buttons, fill forms, trigger actions
3. **Verify** the expected behavior with snapshots or screenshots
4. **If broken**: revise the fix, then test again
5. **Iterate** until the E2E flow works completely

**Example E2E test flow:**
```
1. browser_navigate → http://localhost:3003/profile?user=peichin
2. browser_snapshot → verify page loaded correctly
3. browser_click → "Edit" button on Style Identity
4. browser_fill_form → update the three words
5. browser_click → "Save" button
6. browser_snapshot → verify changes persisted
```

**Key principle:** Don't just verify the page loads - walk through the actual user flow. If users click a button and fill a form, the E2E test should do the same.

## Key Implementation Details

**Style Generation Flow:**
1. **Profile Collection** - Three-word method (current/aspirational style) + daily emotion
2. **Wardrobe Analysis** - Categorizes items as "regular wear" vs "styling challenges"
3. **AI Prompt Engineering** - Creates detailed styling prompts incorporating user profile and wardrobe
4. **Outfit Generation** - Generates 3 combinations with confidence levels (Comfort Zone/Gentle Push/Bold Move)
5. **Visual Presentation** - Magazine-style cards with styling notes and philosophy

**Data Structure:**
- Items stored with: name, category, colors, description, style_tags, image_path
- Outfits include: items list, styling_notes, why_it_works, confidence_level, vibe_keywords
- User profiles: three_words dict, daily_emotion dict, timestamp

**Configuration:**
- OpenAI API key required for AI styling generation
- Streamlit configuration in app.py for page layout and custom CSS
- Image uploads automatically processed and stored with unique IDs

## Tech Stack Dependencies

- **Streamlit** - Web interface framework
- **OpenAI** - GPT integration for outfit generation
- **PIL (Pillow)** - Image processing for uploads
- **python-dotenv** - Environment variable management

Virtual environment handles all dependencies via `requirements.txt`.

## PostHog Analytics

PostHog MCP is configured for autonomous analytics queries.

**MANDATORY: Always filter out Pei-Chin's devices in ALL user analytics queries.** Without this filter, data is corrupted by Pei-Chin viewing other users' wardrobes.

**Pei-Chin's Device IDs (exclude from queries):**
```
019b5d53-2130-76a8-943e-4a5552e0758b
019bc998-094e-7309-a042-2e017cc5bd45
019b6b77-3a3e-7343-942f-80c2bb67787a
019b5d2f-f5cc-7329-bc3a-26f01842e4bd
peichin
```

**Standard filter clause for HogQL queries:**
```sql
AND properties.$device_id NOT IN (
  '019b5d53-2130-76a8-943e-4a5552e0758b',
  '019bc998-094e-7309-a042-2e017cc5bd45',
  '019b6b77-3a3e-7343-942f-80c2bb67787a',
  '019b5d2f-f5cc-7329-bc3a-26f01842e4bd',
  'peichin'
)
```

**Key events tracked:**
- `$pageview` - Page views (automatic)
- `words_completed` - Onboarding step 1 complete
- `upload_completed` - Onboarding step 2 complete
- `outfit_generated` - User generated an outfit
- `outfit_saved` / `outfit_disliked` - User actions on outfits
- `visualization_complete` / `visualization_failed` - Runway visualization events
- `descriptor_saved` - Model descriptor updates
- `$rageclick` - Frustration signal (rapid clicks)

**Why filter devices:** Pei-Chin often visits other user URLs (e.g., `?user=dimple`) to view their wardrobes, which inflates those users' event counts. The device filter ensures we see true user behavior.

## Agent-Native Architecture (Jan 2026)

Style Inspo is transitioning to "agent as first-class citizen" - the app's value is the **capability** ("help me look good"), not the website. Website, SMS, email are just access points.

### Core Principles

1. **Primitives are CRUD** - Tools are dumb data operations. Intelligence lives in prompts.
2. **Eigenquestion**: "To change behavior, edit prompt or refactor code?" If refactor → primitive is too coarse.
3. **No `generate_outfit` primitive** - Outfit generation is agent REASONING, not a tool. Tools provide DATA (items, feedback), agent provides JUDGMENT (what works together).

### Current Primitives (32 total)

| Entity | Primitives |
|--------|------------|
| Wardrobe | `get_items`, `get_item`, `add_item`, `update_item`, `rotate_item_image`, `delete_item` |
| Profile | `get_profile`, `update_profile`, `update_descriptor` |
| Outfits | `save_outfit`, `get_saved_outfits`, `get_outfit`, `delete_outfit`, `mark_worn`, `upload_worn_photo`, `get_not_worn_outfits`, `get_worn_outfits` |
| Feedback | `save_feedback`, `get_feedback`, `get_feedback_patterns` |
| Consider-Buy | `add_considering_item`, `get_considering_items`, `get_considering_stats`, `update_considering_item`, `rotate_considering_image`, `decide_considering_item`, `delete_considering_item` |

### SMS/WhatsApp Flow (Jan 2026)

```
User texts → Agent generates item NAMES → Fuzzy match to wardrobe → Grid collage → MMS
```

**Key files:**
- `backend/api/sms.py` - Twilio webhook, background processing
- `backend/primitives/matching.py` - Fuzzy item name matching
- `backend/services/collage.py` - 2x2/3x2 grid generation

**Timing:** ~21 seconds E2E (ack → outfit delivered)

### No Framework Needed

The agent loop is ~20 lines. Frameworks (LangGraph, CrewAI) are overkill for "single skilled worker with tools."

**Where differentiation lives:**
- Agent loop: Commoditized (minimal investment)
- Primitives: Medium (design thoughtfully)
- System prompt: **High** (this is where taste lives)
- Domain knowledge: **Highest** (garment physics, feedback patterns)

## User Research Insights (Jan 2026)

### What Users Actually Do

| User | Expected Use | Actual Use |
|------|--------------|------------|
| Dimple | Plan work outfits | Validate purchases ("buy smart") |
| Alexi | Generate complete outfits | Remember forgotten items, single-item inspiration |

**Key insight:** Neither user uses it for complete outfit generation. Dimple can't (timing/access), Alexi won't (doesn't trust physics).

### The Garment Physics Problem

Users reject outfits that violate physical reality:
- Ruffled shirt tucked into jeans (bulky)
- Oversized sweatshirt + tight jacket (proportions wrong)
- Two bottoms that can't layer

**This is in the system prompt** (`backend/agent/prompts.py`) but needs continued tuning.

### The Reframe

**From:** "AI generates your outfit"
**To:** "AI reminds you what's possible in your closet"

## Future Architecture Considerations

**Mobile App Migration (High Priority):**
- Current architecture uses Streamlit session state - will need mobile-friendly alternatives
- File storage system (local folders) requires cloud storage for mobile (AWS S3, Google Cloud)
- No user authentication system currently - mobile will need Firebase Auth or similar
- API architecture needed - mobile apps require REST API communication
- Keep data models JSON-serializable for mobile compatibility

**Performance Optimization (Active Investigation):**
- Image analysis latency: ~6.7s baseline → ~14.6s with enhanced logo prompt
- Need systematic A/B testing across diverse clothing photos to determine if brand detection improvement justifies 2x latency increase
- Token count optimization: Current prompts use ~1,200-1,400 tokens per analysis
- Consider prompt complexity vs. speed trade-offs for production use

**Development Guidelines for Mobile Readiness:**
- Design functions as pure input/output (no UI coupling)
- Use abstract data structures that work as JSON APIs
- Comment Streamlit-specific code that will need mobile alternatives
- Keep file storage patterns abstracted for future cloud migration

## Critical Debugging & Implementation Lessons

**From Nov 5, 2025 debugging session: EXIF orientation and code path analysis**

### Lesson 1: Always Check Dual Storage Systems (Local vs Production)
**Problem**: Fixed EXIF orientation for local files, but production uses S3 URLs which bypassed the fix entirely.

**What happened**:
- Fixed `outfit_visualizer.py` to apply `ImageOps.exif_transpose()` for local files
- Code worked in local dev (files on disk)
- Failed in production (S3 URLs) because `if image_path.startswith("http")` bypassed the fix
- Spent 2 hours before realizing local != production storage

**Prevention checklist**:
- [ ] Check `STORAGE_TYPE` environment variable (local vs s3)
- [ ] Test fixes with BOTH local files AND S3 URLs
- [ ] Search codebase for `if image_path.startswith("http")` - these branches handle storage differently
- [ ] When fixing image processing, verify the fix applies to ALL storage backends

### Lesson 2: Verify Actual Code Paths in Use
**Problem**: Fixed `outfit_visualizer.py` but `new_onboarding.py` used completely different rendering code.

**What happened**:
- Assumed new onboarding flow used `OutfitVisualizer` class
- Actually used custom `_build_collage_html()` function instead
- Fixed wrong code path, wasted time

**Prevention checklist**:
- [ ] Use `grep` to find actual function calls in the flow
- [ ] Trace from user-facing page backwards to rendering logic
- [ ] Don't assume shared component usage - verify with code search
- [ ] Check git history: "When was this file last modified?" vs "When was the flow built?"

### Lesson 3: Visual Regression Testing Before Pushing
**Problem**: Switched from custom editorial styling to generic `OutfitVisualizer` style, regressing UX.

**What happened**:
- Replaced custom rendering with `OutfitVisualizer.display_magazine_style_outfit()`
- Assumed functional fix = UX preserved
- OutfitVisualizer had completely different visual design
- Lost editorial "How to Style" aesthetic

**Prevention checklist**:
- [ ] Before pushing visual changes, ask: "What does this page look like NOW vs AFTER?"
- [ ] If replacing rendering code, compare HTML/CSS output
- [ ] Check for custom CSS classes that will be lost
- [ ] Screenshots before/after when touching UI code

### Lesson 4: Fix at the Source, Not the Symptoms
**Problem**: Tried fixing orientation at display time (multiple locations) instead of upload time (one location).

**What happened**:
- Initially planned to add EXIF fix to 6+ display locations
- Realized images should be saved correctly ONCE at upload
- Upload handler fix (wardrobe_manager.py line 88) solved ALL downstream issues

**Prevention checklist**:
- [ ] Map the data flow: Where is data created? Where is it used?
- [ ] Fix at creation/upload, not at every display location
- [ ] Ask: "If we fix this at the source, what downstream fixes become unnecessary?"
- [ ] One-time processing > repeated processing at every render

### Lesson 5: Cursor vs Claude Code Workflow
**Problem**: Spent time with Cursor on wrong approach, then repeated with Claude Code.

**What works**:
- Use **Cursor** for: Rapid implementation, known patterns, UI polish
- Use **Claude Code** for: Architecture diagnosis, multi-file analysis, tracing code paths
- When stuck with Cursor for >20 min: Switch to Claude Code for diagnosis BEFORE trying more Cursor fixes

**Prevention checklist**:
- [ ] If Cursor's 2nd attempt fails, stop and diagnose with Claude Code
- [ ] Use Claude Code to verify approach BEFORE delegating to Cursor
- [ ] Claude Code = strategy, Cursor = tactics
- [ ] Don't repeat failed approaches across tools

### Lesson 6: Test Incrementally with Production Data
**Problem**: Fixed code locally, pushed, tested in production, nothing worked.

**Better approach**:
- Fix upload handler → Push → Test ONE photo upload → Verify orientation
- Then fix display → Push → Test display
- Incremental validation catches issues earlier

**Prevention checklist**:
- [ ] Push smallest testable unit
- [ ] Validate in production immediately after each push
- [ ] If first fix doesn't work, diagnose why before adding more fixes
- [ ] Production environment is source of truth, not local dev

### Lesson 7: Validate Specs Solve the Actual Problem (Dec 2025 SSE Streaming)
**Problem**: Created a "streaming" spec that only set a static progress message, leaving users staring at "Creating outfit 1 of 3..." for 20 seconds with no updates.

**What went wrong**:
- Optimized for "easy to implement" instead of "solves the problem"
- True streaming requires piping tokens through SSE as they generate
- Instead, spec only added 4 lines of `job.meta` updates at START and END of generation
- Rationalized it as "MVP" when it was actually useless
- Buried the real solution in "Future Enhancements (out of scope)"

**The useless spec said**:
```
"For MVP, we'll emit progress events at job milestones rather than during AI generation"
```
This means: set message once, wait 20 seconds, done. That's not streaming.

**Prevention checklist**:
- [ ] Before handing spec to Cursor, walk through UX second-by-second: "At t=0 user sees X, at t=5 they see Y, at t=20 they see Z"
- [ ] Ask: "Does this actually solve the problem during the slow part?"
- [ ] If labeling something "MVP", be explicit: "This MVP won't help during the 20s wait, only before/after"
- [ ] Don't bury the real solution in "Future Enhancements" without flagging it
- [ ] When user says "streaming to reduce latency", validate: are we actually streaming content, or just setting a loading message?

**First-principles validation for streaming features**:
- OpenAI's streaming API sends tokens as they generate (every ~50-100ms)
- True streaming = user sees text appearing character by character
- Fake streaming = set a message once, wait for full response, show result
- Before implementing, run a time study to understand what actually gets generated when

**Claude Code + Cursor workflow improvement**:
- Claude Code creates spec → Claude Code validates UX second-by-second → User approves → Cursor implements
- If Claude Code can't demo "user sees X at t=5", the spec isn't ready

### Lesson 8: Always Test Locally BEFORE Commit/Push
**Problem**: Committed and pushed code without testing locally first, resulting in broken production deploy.

**What happened** (Jan 2026 HEIC orientation fix):
- Wrote fix for HEIC image orientation
- Created todo list: "Modify code → Commit/Push → Test"
- Pushed untested code to production
- Code had a bug (double rotation)
- Had to push a second fix after local testing revealed the issue

**Why this matters**:
- Production deploys take time (~2 min)
- Users may see broken features
- Git history cluttered with "fix the fix" commits
- Debugging in production is harder than local

**Correct workflow**:
1. Write the code change
2. **Test locally** with real data (not mocked)
3. Verify the fix works as expected
4. THEN commit and push

**Prevention checklist**:
- [ ] Before ANY commit: "Have I tested this locally?"
- [ ] For image processing: test with actual image files
- [ ] For API changes: test with curl/Postman locally
- [ ] TodoWrite should ALWAYS have "Test locally" BEFORE "Commit/Push"
- [ ] If you can't test locally, explicitly acknowledge the risk

**TodoWrite template for code changes**:
```
1. Implement the fix
2. Test locally with real data   ← MUST come before commit
3. Commit and push
4. Verify in production
```

### Lesson 9: Full-Stack Integration Debugging (Jan 2026 - Image Orientation)

**Problem**: Simple bug (missing `preserveExif: true`) took 5 pushes over a month to fix.

**What happened**:
- Nov-Dec 2025: Fixed backend EXIF handling multiple times
- Jan 1, 2026: Added backend HEIC support
- Jan 2, 2026: Finally fixed frontend - issue was `browser-image-compression` stripping EXIF

**Why advanced models couldn't help**:
- We tested backend in isolation (test_exif_integration.py) ✅
- Backend test bypassed frontend, so it passed
- We kept asking model to fix backend when bug was in frontend
- **Models can't fix bad methodology** - if you test the wrong thing, model will fix the wrong thing

**Root cause of delay**:
1. **Tested components, not integration** - backend test bypassed frontend
2. **Didn't trace full flow** - Browser → Compression → Upload → Backend
3. **Assumed library defaults** - didn't check `browser-image-compression` docs
4. **Wrong scope** - fixed backend (last step) when bug was in step 2

**Prevention checklist**:
- [ ] For bugs spanning frontend/backend: trace ENTIRE flow first
- [ ] Test with production-like data flow (real browser uploads, not Python mocks)
- [ ] When 2+ fixes don't work: widen scope, check integration points
- [ ] For third-party libraries: check defaults, don't assume "right behavior"
- [ ] Component tests are necessary but not sufficient - need integration tests

**Debugging template for full-stack issues**:
```
1. Map the full data flow (every step from user to storage)
2. Test each step with production-like data
3. Check library defaults and configurations
4. Don't assume any step works - verify each one
5. If stuck after 2 attempts, trace end-to-end before more fixes
```

**Key insight**: The fix was 1 line (`preserveExif: true`) but took a month because we debugged the wrong component. Advanced models can't compensate for testing the wrong thing.

### Lesson 10: Verify Data Structure Before Bulk Operations (Jan 2026)

**Problem**: Deleted all 35 saved outfits thinking empty `items` arrays meant broken data.

**What happened**:
- Manager code looked for `outfits[].items`
- Actual S3 structure was `saved[].outfit_data.items`
- All outfits appeared "empty" due to wrong key path
- Bulk deleted everything, S3 versioning saved us

**Prevention checklist**:
- [ ] Before bulk delete: read ONE full record and print its structure
- [ ] Never assume empty = broken - verify the key path exists
- [ ] Show user exactly what will be deleted and get explicit confirmation
- [ ] Have S3 versioning enabled on all user data buckets