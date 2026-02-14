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

## Pre-Action Gates

**These are blocking checks. Run the relevant gate BEFORE taking the action.**

### GATE: Before Every Commit/Push

```
1. Run: cd backend && python -c "from main import app"
2. If you added ANY new import → check it's in requirements.txt
3. If you added ANY new env var → verify it exists in Railway
4. If you touched image/file code → test with both local files AND S3 URLs
```

A pre-commit hook enforces step 1 automatically. Steps 2-4 are manual.

### GATE: Before Deploying a Provider/Module from a Prior Session

Prior sessions may have `pip install`ed packages that never made it to `requirements.txt`. Before deploying code built in a different session:
- Check every import in the new files against `requirements.txt`
- Run the import smoke test above

### GATE: Before Fixing a Bug

1. **Trace the full data flow first** — map every step from user input to final output
2. **Grep for the actual code path** — don't assume which file handles the flow; verify with search
3. **If it spans frontend + backend** — test the integration, not just one component
4. **Check third-party library defaults** — don't assume libraries do "the right thing"
5. **If 2 fixes haven't worked** — stop fixing and widen scope; you're probably in the wrong component

### GATE: Before Changing Rendering/UI Code

1. **Screenshot the current state** before touching anything
2. **Compare HTML/CSS output** of old vs new rendering path
3. **Check for custom CSS classes** that will be lost in a component swap

### GATE: Before Writing a Spec

Walk through UX second-by-second: "At t=0 user sees X, at t=5 they see Y, at t=20 they see Z." If the spec doesn't help during the slow/painful part, it doesn't solve the problem.

### GATE: Before Bulk Delete/Modify

1. **Read ONE full record** and print its actual structure
2. **Show the user** exactly what will be deleted/modified and the count
3. **Get explicit confirmation** before proceeding
4. Never assume empty/null = broken — verify the key path first

### Workflow Rules

- **Fix at the source, not the symptoms.** Map where data is created vs displayed. Fix at creation (1 place), not display (N places).
- **Push smallest testable unit.** Validate in production immediately after each push.
- **Cursor = tactics, Claude Code = strategy.** If Cursor's 2nd attempt fails, switch to Claude Code for diagnosis before trying more Cursor fixes.
- **Production environment is the source of truth**, not local dev. Test with real data flows (browser uploads, not Python mocks).