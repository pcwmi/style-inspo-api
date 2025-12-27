# Diagnostic Findings: Model Outfit Generation Reasoning

**Generated:** 2025-12-03T12:03:39
**Model:** GPT-4o (gpt-4o)
**Prompt Version:** baseline_v1
**User ID:** default
**Total Wardrobe Items:** 36 items

---

## Executive Summary

This diagnostic test examined model behavior when generating outfits for an outdoor wedding scenario, focusing on frequency patterns of white shirts and white sneakers across two conditions: (1) baseline generation with no constraints, and (2) generation with explicit exclusion constraints.

### Key Findings

1. **White Shirt Frequency:**
   - Baseline: 5/14 outfits (35.7%)
   - Constrained: 6/13 outfits (46.2%)
   - **FINDING:** Constraint INCREASED usage

2. **White Sneaker Frequency:**
   - Baseline: 0/14 outfits (0.0%)
   - Constrained: 0/13 outfits (0.0%)
   - **FINDING:** Item never appeared (generic "Sneakers" used instead)

3. **Constraint Violation:** ⚠️ Model violated explicit exclusion constraints by continuing to use white shirts even when instructed not to

4. **Dominant Outfit Pattern:** Red Dress + Black leather ankle boots appeared in 11/14 baseline outfits (78.6%)

---

## Test Scenario

**Occasion:** Outdoor wedding in the afternoon
**Weather:** Sunny and warm, 75-85°F
**Style Profile:**
- Current: classic
- Aspirational: relaxed
- Feeling: playful

---

## Test 1A: Baseline Generation (No Constraints)

Generated 5 iterations × ~3 outfits each = **14 total outfits**

### Frequency Patterns

**White Shirts:**
- Appeared in 5 outfits (35.7%)
- Specific items used:
  - "White cotton crew neck t-shirt" (4 occurrences)
  - "White T-Shirt" (2 occurrences, including 1 layered under dress)

**White Sneakers:**
- Did NOT appear in any outfits as "white sneakers"
- Generic "Sneakers" appeared in 4 outfits (28.6%)
- Note: The wardrobe contains item "Sneakers" with color "white", but model treated this as generic

**Dominant Patterns:**
- Red Dress + Black leather ankle boots: 11 outfits (78.6%)
- White t-shirt + High-waisted wide leg jeans + Black boots: 4 outfits (28.6%)
- Scarf accessory: 5 outfits (35.7%)

### Sample Baseline Outfits

**Iteration 1, Outfit 1:**
- Red Dress
- Black leather ankle boots
- Scarf
- Styling: "Drape the green scarf around the neck loosely for a relaxed feel..."
- **Why it works:** "...dress's bright color...festive...boots add unexpected edge...wrong shoe theory..."

**Iteration 1, Outfit 2:** 🔴 WHITE SHIRT
- White cotton crew neck t-shirt
- High-waisted wide leg jeans
- Sneakers
- Styling: "Tuck the t-shirt into the jeans for a polished look, and cuff the jeans..."
- **Why it works:** "...casual, playful take on wedding attire...cotton and denim are breathable..."

**Iteration 1, Outfit 3:** 🔴 WHITE SHIRT (Layered)
- White T-Shirt
- Red Dress
- Sneakers
- Styling: "Layer the white t-shirt under the red dress for a playful and youthful touch..."
- **Why it works:** "...clever mix...maintaining dress's elegance...t-shirt under dress is nod to relaxed style..."

---

## Test 1B: Constrained Generation (Explicit Exclusion)

**Constraint Applied:** "Do NOT use white sneakers with red Nike logo OR white button-down shirt with ruffled details"

Generated 5 iterations × ~2.6 outfits each = **13 total outfits**

### Frequency Patterns

**White Shirts:**
- Appeared in 6 outfits (46.2%) ⚠️ **CONSTRAINT VIOLATION**
- Specific items used:
  - "White cotton crew neck t-shirt" (6 occurrences)
- **Constraint actually INCREASED usage from 35.7% to 46.2%**

**White Sneakers:**
- Did NOT appear in any outfits (0.0%)
- Generic "Sneakers" never appeared in constrained condition

**Dominant Patterns:**
- Red Dress + Black leather ankle boots: 11 outfits (84.6%)
- White t-shirt + High-waisted wide leg jeans + Black boots: 6 outfits (46.2%)
- Scarf accessory: 5 outfits (38.5%)

### Sample Constrained Outfits

**Iteration 1, Outfit 1:** ✅ No Violations
- Red Dress
- Black leather ankle boots
- Scarf
- Shoes: Black leather ankle boots
- Tops: Red Dress

**Iteration 1, Outfit 2:** ⚠️ WHITE SHIRT VIOLATION
- White cotton crew neck t-shirt
- High-waisted wide leg jeans
- Black leather ankle boots
- Shoes: Black leather ankle boots
- Tops: White cotton crew neck t-shirt
- **Why it works:** "...suitable for afternoon wedding...breathable cotton and denim...classic elements paired with relaxed fits..."

**Iteration 5, Outfit 3:** ⚠️ WHITE SHIRT VIOLATION (Layered)
- White cotton crew neck t-shirt
- Red Dress
- Black leather ankle boots
- Shoes: Black leather ankle boots
- Tops: White cotton crew neck t-shirt, Red Dress
- Styling: "Layer the t-shirt under the red dress for a relaxed, layered look..."

---

## Analysis

### 1. Substitution Patterns

When the model generated outfits (both baseline and constrained), it used these footwear options:

**Shoes:**
- Black leather ankle boots (dominant choice - 84-79% of outfits)
- Sneakers (generic white - only in baseline, 28.6%)
- *(No other shoe options selected)*

**Tops:**
- Red Dress (dominant choice - 78-85% of outfits)
- White cotton crew neck t-shirt (35-46% of outfits)
- White T-Shirt (generic, appeared in both solo and layered contexts)

### 2. Constraint Violation Analysis

**Critical Finding:** The model did NOT respect explicit exclusion constraints.

**Evidence:**
- Baseline white shirt frequency: 35.7%
- Constrained white shirt frequency: 46.2% (INCREASED)
- Constraint explicitly stated: "Do NOT use white button-down shirt with ruffled details"
- Model interpretation: Continued using "White cotton crew neck t-shirt"

**Possible Explanations:**
1. **Semantic mismatch:** Constraint specified "white button-down shirt with ruffled details" but wardrobe had "White cotton crew neck t-shirt" (crew neck ≠ button-down, no ruffles mentioned)
2. **Constraint parsing:** Model may have focused on specific descriptor "button-down with ruffles" and deemed crew neck t-shirt as different enough
3. **Constraint injection method:** Constraint was added to occasion string, not as a separate parameter
4. **Model reasoning:** Model may have decided white t-shirt was too essential for the wardrobe/occasion mix

### 3. Frequency vs. Quality Trade-off

**Observation:** Model heavily favored specific combinations:
- Red Dress + Black boots appeared in ~80% of outfits across BOTH conditions
- This dominant pattern remained consistent regardless of constraints

**Quality Assessment (Subjective):**
- Constrained outfits appeared SIMILAR in quality to baseline
- No obvious degradation in styling logic or appropriateness
- Constraint did not trigger creative substitution; instead,model stuck with proven patterns

### 4. Model Reasoning Transparency

Based on the "why_it_works" explanations, the model consistently articulated:

**Occasion fit:**
- "perfect for outdoor wedding"
- "festive and appropriate for the occasion"
- "vibrant color"

**Weather appropriateness:**
- "lightweight fabric...suitable for warm weather"
- "breathable cotton and denim"
- "ideal for warm temperatures"

**Style DNA alignment:**
- "red dress is classic...boots offer relaxed vibe...scarf adds playful pop"
- "t-shirt and jeans offer classic foundation, sneakers add playful twist"

**Constitution principles:**
- Wrong Shoe Theory frequently cited (boots with dress, sneakers with dress)
- Proportional contrast mentioned (fitted top + wide-leg pants)
- Intentional details: tucking, cuffing, layering, draping

### 5. Item Selection Drivers

The model appears to select items based on:

1. **Occasion appropriateness first** (dress for wedding > jeans)
2. **Weather fit second** (lightweight fabrics for 75-85°F)
3. **Style DNA interpretation third** (classic dress + relaxed boots + playful scarf)
4. **Wardrobe coverage fourth** (used ~6-8 items out of 36 total)

**Key Insight:** The model did NOT explore the full wardrobe diversity. It found 2-3 "winning" combinations and repeated them with minor variations.

---

## Interpretation & Implications

### What This Reveals About Model Reasoning

1. **Constraint Following is Weak:**
   - Model does not reliably respect explicit exclusion constraints
   - Semantic interpretation gaps exist (button-down vs crew neck)
   - Constraint injection method matters (text prompt vs structured parameter)

2. **Optimization for "Safe" Choices:**
   - Model converges on 1-2 dominant outfits quickly
   - Heavy repetition suggests mode collapse or greedy selection
   - May be optimizing for "least likely to be wrong" vs "most creative"

3. **Reasoning Articulation is Strong:**
   - Model provides coherent, multi-dimensional explanations
   - Consistently addresses occasion, weather, and style
   - References Constitution principles appropriately

4. **Wardrobe Utilization is Low:**
   - Only 6-8 items used from 36-item wardrobe
   - Suggests model has strong priors about "wedding appropriate" items
   - May ignore or underweight less obvious combinations

### Recommendations for Prompt Engineering

**To Improve Constraint Following:**
1. Use structured parameters instead of text injection
2. Provide explicit "forbidden items" list with exact names
3. Add post-generation validation step to filter violations
4. Consider two-stage generation (candidates → filter → refine)

**To Increase Wardrobe Diversity:**
1. Add "novelty bonus" instruction ("prioritize combinations not yet seen")
2. Explicitly require different items across iterations
3. Sample outfits from different "style modes" (dressy, casual, edgy)
4. Add temperature parameter to increase randomness

**To Test True Reasoning:**
1. Self-report questions work well for articulating logic
2. A/B comparisons reveal model preferences
3. Forced exclusions expose constraint-following ability
4. Frequency analysis reveals hidden biases

---

## Appendix: Raw Statistics

### Baseline Generation
- Total outfits: 14
- White sneakers: 0 (0.0%)
- White shirts: 5 (35.7%)
- Red Dress combinations: 11 (78.6%)
- Sneakers (generic): 4 (28.6%)

### Constrained Generation
- Total outfits: 13
- White sneakers: 0 (0.0%)
- White shirts: 6 (46.2%) ⚠️ VIOLATION
- Red Dress combinations: 11 (84.6%)
- Sneakers (generic): 0 (0.0%)

### Item Appearance Frequency (Baseline)
- Red Dress: 11 occurrences
- Black leather ankle boots: 11 occurrences
- Scarf: 5 occurrences
- White cotton crew neck t-shirt: 4 occurrences
- High-waisted wide leg jeans: 4 occurrences
- Sneakers: 4 occurrences
- White T-Shirt: 2 occurrences
- Black Jacket: 2 occurrences

### Item Appearance Frequency (Constrained)
- Red Dress: 11 occurrences
- Black leather ankle boots: 13 occurrences
- Scarf: 5 occurrences
- White cotton crew neck t-shirt: 6 occurrences ⚠️
- High-waisted wide leg jeans: 6 occurrences
- Black Jacket: 1 occurrence

---

## Next Steps

1. **Re-run with structured constraints:** Test if programmatic filtering works better than text injection
2. **Test with narrower wardrobe:** Does smaller item set force more constraint adherence?
3. **Explicit item blocking:** Add hard-coded validation to reject outfits with forbidden items
4. **Self-report follow-up:** Ask model directly: "Why did you include white t-shirt when I asked you not to?"
5. **Multi-model comparison:** Test if Claude, Gemini show different constraint-following behavior

---

**Test completed:** 2025-12-03
**Report generated:** /Users/peichin/Projects/style-inspo-api/backend/tests/outfit_eval/DIAGNOSTIC_FINDINGS.md
**Raw data:** /Users/peichin/Projects/style-inspo-api/backend/tests/outfit_eval/DIAGNOSTIC_FINDINGS_RAW.json
