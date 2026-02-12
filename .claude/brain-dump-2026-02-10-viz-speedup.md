# Visualization Speed-Up Research (Feb 10, 2026)

## Problem
New outfit visualization takes 25-35s (Runway Gen-4 API). Users wait too long after tapping "See it on me." The collage/cold path already exists as instant fallback. Returning users already see cached S3 images. **The pain point is purely first-time generation latency for new outfits.**

## Key Insight: Quality-at-Speed, Not Just Speed
User already rejected Nano Banana (Gemini 2.5 Flash via Runway, ~17s) because the "vibe" wasn't as good as Runway Gen-4. Speed alone doesn't win — output must feel editorial/inspirational, like a fashion magazine, not a product catalog.

## Research Team Findings (3 agents debated)

### Approach 1: Faster Model Swap (PRIMARY STRATEGY)
- **Flux 2 Pro** (Black Forest Labs, Germany) via fal.ai (US): 6-10s, ~$0.06/MP, multi-reference image support. Higher aesthetic tier than Flex. Untested for garment photos.
- **Flux 2 Max**: 10-15s, ~$0.10/MP, "art-grade realism." Best aesthetic quality in Flux family.
- **Flux 2 Flex**: 3-6s, cheapest, but "developer tier" — may be too clinical for fashion inspiration.
- **Fashn.ai Product to Model** (UK): ~12s, $0.075, claims "editorial-grade," generates NEW scenes. Different from Fashn.ai Try-On (which is catalog-like). Needs person photo input — could generate reference model from text descriptor once, cache it.
- **Runway gen4_image_turbo**: ~12s, $0.02, claims same quality. Unvalidated for vibe.
- Provider abstraction already exists in codebase — adding new provider is straightforward.

### Approach 2: Pre-Generation at Save Time (DEPRIORITIZED)
- Only shaves 2-5 seconds (gap between save and "See it on me" tap)
- Not transformative for the actual pain point
- ~10 lines of code, worth adding opportunistically but not the solution

### Approach 3: Enhanced Collage (ALREADY EXISTS)
- Current cold path already shows garment collage. This IS the instant fallback.
- Progressive upgrade (collage → AI) already the implicit UX

## Chinese-Origin Models (AVOID)
- Kling Kolors / KlingAI — Kuaishou (Beijing)
- CatVTON — Sun Yat-Sen University (Guangzhou)
- OOTDiffusion — Xiao-i/Shanghai
- SDXL Lightning — ByteDance (Beijing)

## Clean Providers
- Flux (Black Forest Labs) — Germany
- fal.ai — USA
- Fashn.ai — UK
- Runway ML — USA
- Gemini/GPT (for judge) — USA

## Next Step: Vibe Test
Run visual comparison using existing 3x3 framework:
- Candidates: Flux 2 Pro, Fashn.ai Product to Model, Runway gen4_image_turbo
- Baseline: Current Runway gen4_image
- Same 5 outfits, same descriptor
- User evaluates: "Which feels inspiring?"
- Result determines which provider to swap to

## Key Debate Outcomes
1. Garment fidelity AND vibe both matter — purpose-built try-on may look clinical
2. Runway's editorial aesthetic is the bar (made by filmmakers/artists)
3. No fast model has PROVEN it matches Runway's vibe yet
4. Test before building — reuse existing 3x3 comparison framework
5. The "shotgun + LLM judge" pattern is over-engineering for now
6. Single biggest lever: find a model that's both fast AND inspiring
