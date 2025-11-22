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
