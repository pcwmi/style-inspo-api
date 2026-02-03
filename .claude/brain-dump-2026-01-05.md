
---

## Runway ML Virtual Try-On Exploration - Key Learnings (Jan 5, 2026)

### Context
Testing Runway Gen-4 Image API for outfit visualization in Style Inspo. Goal: validate if Runway can create inspiring outfit visualizations that give users "aha moment" and help them imagine wearing their wardrobe.

### Validated Hypotheses ✅

**1. Relatable Model > Personal Photo**
- **Test**: Model vs personal photo comparison
- **Result**: Personal photo feels "like a remote relative" (uncanny valley effect)
- **Insight**: Users don't need their exact face - demographic relatability (height, race, body type) creates stronger emotional connection than exact likeness
- **Implication**: Personalization = relatable model descriptor, NOT personal photo upload

**2. Relatable Model > Standard Shopping Model**
- **Test**: Asian 5'4" relatable descriptor vs white 5'10" standard model
- **Result**: Relatable model creates "I could pull this off" feeling; standard model feels "fancy but out of touch"
- **Insight**: Representation matters for inspiration - users relate better to models who share their physical characteristics
- **Implication**: Default to relatable model descriptors based on user demographics

**Winning descriptor**:
```
Model: ~163 cm, ~150 lb, Asian woman, dark wavy chest-length hair, softly defined hourglass figure; natural proportions (neither skinny nor chubby).
```

### Failed Hypotheses ❌

**3. Strong Prompt Anchoring Does NOT Improve Garment Fidelity**
- **Test**: Control prompts vs explicit detail preservation instructions
- **Prompt added**: "Preserve exact garment details from reference images: keep lengths (midi/mini/maxi), cuts, necklines, proportions, and colors exactly as shown."
- **Result**: 
  - Sage skirt outfit: Strong anchoring FAILED spectacularly - skirt too short, boots too tall (worse than control)
  - Pink cardigan outfit: On par with control (no improvement)
- **Insight**: Runway Gen-4 is architecturally designed for character/location consistency, NOT object preservation. Prompt engineering cannot overcome model limitations.
- **Evidence**: Runway docs state "Currently, References primarily supports character and location preservation, but updates are planned for the future to support objects"

### Core Limitation Identified

**Garment Fidelity Problem**: Runway Gen-4 treats garments as part of character's overall aesthetic, not as discrete objects to preserve
- Skirt lengths frequently wrong (midi becomes mini, wrong cuts)
- Trouser widths altered
- Colors/patterns approximated but not exact
- This is a FUNDAMENTAL MODEL LIMITATION, not a prompt engineering issue

### Strategic Implications

**For Inspiration Use Case (Style Inspo core value prop)**

✅ **Runway is GREAT for**:
- Creating aspirational outfit visualizations with relatable models
- Helping users imagine "could I pull this off?"
- Generating editorial-style imagery that feels personal
- Exploration and inspiration ("what would this look like on someone like me?")

❌ **Runway is NOT suitable for**:
- Exact virtual try-on (garments won't match user's actual items)
- E-commerce product visualization (fidelity issues)
- "See this exact outfit on you" promises

### Product Architecture Decision

**Two-tool strategy**:
1. **Runway** (relatable model): For inspiration, exploration, "plan my day" mood setting
   - Cost: ~$0.005-0.01 per image, 25-30s generation
   - Use when: User wants to see outfit in context, feel inspired, imagine possibilities
   
2. **Fashn.ai or similar** (future): For exact virtual try-on
   - Cost: $0.075 per image
   - Use when: User wants exact garment representation on their body

**Don't try to make Runway do what it's not built for** - accept the limitation and use it for its strengths

### What's Next

**Validated next step**: Test Runway video generation with relatable model in user-specified contexts
- Example: "Coffee meeting" setting for "plan my day" feature
- Hypothesis: Seeing outfit in motion (how skirt flows, coat drapes) adds another dimension beyond static images
- Acceptance: Garment fidelity will still be approximate, but motion/context may add value despite this

**Open questions**:
- Does video's motion/draping compensate for fidelity issues?
- Is contextual setting ("coffee shop", "office") valuable for outfit planning?
- What's the right balance between generation cost/time and user value?

### Technical Details
- All tests used relatable model descriptor
- 3 reference images max (Runway limitation)
- 1000 character prompt limit
- Generation time: 24-32 seconds per image
- Model: gen4_image with References feature

