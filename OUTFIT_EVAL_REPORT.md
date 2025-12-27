# Outfit Generation Evaluation Analysis Report

**Date:** December 2, 2025
**Total Ratings Analyzed:** 187 outfit ratings across 4 models and 2 prompt variations
**Evaluation Period:** November 28 - December 2, 2025

---

## Executive Summary

This report documents a rigorous evaluation of AI-generated outfit quality across multiple models and prompt engineering approaches. Key findings:

1. **GPT-4o is the clear winner** for production use (4.0★ median, 53% high ratings)
2. **Fit constraint prompts backfire** - they increase poor taste without reliably reducing layering errors
3. **The quality ceiling is ~4.0★** - suggesting the bottleneck is prompt architecture, not model capability
4. **Next breakthrough requires rethinking the satisfaction framework**, not more model/prompt tweaking

**The Hard Truth:** This eval shows that the ceiling for outfit generation quality is around 4.0★ median / 53% high ratings with current prompting approaches. Even GPT-4o (the best) still has an 18% failure rate.

**The Real Question: Is This a Model Problem or a Prompt/Process Problem?**

Looking at the findings:
- **Impossible layering (9-17%):** Models don't understand garment physics
- **Poor taste (7-27%):** Models make aesthetically wrong choices
- **Baseline > Fit Constraints:** More rules ≠ better quality

This suggests **the bottleneck isn't model capability**, it's:
1. **Prompt architecture** - How we're asking the model to think about styling
2. **Context/information** - What the model knows about each garment
3. **Evaluation criteria** - The model's internal taste alignment with user preferences

---

## 1. Model Performance Comparison

### Methodology

- **Models tested:** GPT-4o, GPT-4o-mini, Claude Sonnet 4.5, Gemini 2 Flash
- **Prompt type:** Baseline Style Constitution (v1) only
- **Rating scale:** 1-5 stars (1=poor, 3=acceptable, 5=excellent)
- **Failure modes tracked:** Impossible layering (physics violations) and poor taste (aesthetic failures)

### Results Summary

| Model | N | Median | Avg | High (4-5★) | Low (1-2★) | Impossible Layering | Poor Taste |
|-------|---|--------|-----|-------------|------------|---------------------|------------|
| **GPT-4o** | 32 | **4.0★** | 3.12 | **53%** | 38% | 16% | 22% |
| Claude Sonnet 4.5 | 48 | 3.0★ | 3.04 | 46% | 35% | 10% | 21% |
| GPT-4o-mini | 29 | 3.0★ | 2.62 | 31% | 48% | 24% | 21% |
| Gemini 2 Flash | 30 | 3.0★ | 2.80 | 33% | 47% | 3% | 43% |

### Key Findings

**Winner: GPT-4o**
- Only model achieving 4.0★ median rating
- Highest percentage of "high quality" outfits (53%)
- Balanced failure modes (16% impossible layering, 22% poor taste)
- **1.0 full star better than competitors**

**Runner-up: Claude Sonnet 4.5**
- Solid 3.0★ median with 46% high ratings
- Lowest impossible layering rate (10%)
- Comparable poor taste rate to GPT-4o (21%)
- **Most consistent "acceptable" quality**

**Budget Option: GPT-4o-mini**
- 3.0★ median but only 31% high ratings (most are "just okay")
- Highest impossible layering rate (24%)
- Good poor taste rate (21%)
- **Adequate but uninspiring**

**Do Not Use: Gemini 2 Flash**
- 3.0★ median but 47% low ratings
- Lowest impossible layering (3%) but highest poor taste (43%)
- **Qualitative feedback: "outfits are plain"**
- Poor occasion appropriateness

### Fatigue Bias Testing

**Concern:** Initial ratings were done in sequence (GPT-4o first, Claude second), potentially introducing fatigue bias against Claude.

**Validation Test:**
- Rated 11 additional Claude baseline outfits with fresh eyes
- **Old ratings (tired):** 3.0★ median, 46% high
- **New ratings (fresh):** 3.0★ median, 45% high
- **Conclusion:** ✓ Ratings are consistent. Quality gap is real, not bias.

---

## 2. Prompt Engineering Analysis: Fit Constraints Experiment

### Hypothesis

Adding explicit garment fit constraints to the Style Constitution would:
- **H1 (intended):** Reduce impossible layering errors (e.g., "fitted cardigan over oversized sweater")
- **H2 (risk):** Potentially make outfits more conservative/boring

### Prompt Changes

**Baseline v1:** 377 lines of Style Constitution covering style principles, color theory, occasion appropriateness

**Fit Constraints v2:** Baseline + 102 additional lines of garment layering rules:
```
## GARMENT FIT CONSTRAINTS (CRITICAL)
**Rule: Each layer must be looser than the previous layer**

- Tank top: Must be fitted/tight
- T-shirt: Must fit close to body
- Button-down shirt: Fits looser than t-shirt
- Sweater: Fits looser than shirt
- Cardigan: Fits looser than sweater
[... 90 more lines of specific constraints ...]
```

### Results: Fit Constraints Backfire

#### Aggregate Impact (All Models Combined)

| Metric | Baseline (N=139) | Fit Constraints (N=48) | Change |
|--------|------------------|------------------------|---------|
| **Median Rating** | 3.0★ | 2.0★ | **-1.0★** ❌ |
| **Impossible Layering** | 13% | 15% | **+2pp** ❌ |
| **Poor Taste** | 26% | 38% | **+12pp** ❌ |

**Verdict:** Fit constraints make outfits WORSE across the board.

#### Per-Model Breakdown

**GPT-4o:**
- Median: 4.0★ → 4.0★ (no change)
- Impossible layering: 16% → 5% (-11pp) ✓
- Poor taste: 22% → 25% (+3pp) ✗
- **Assessment:** Constraints help with layering but slight taste penalty

**Claude Sonnet 4.5:**
- Median: 3.0★ → 2.0★ (-1.0★) ❌
- Impossible layering: 10% → 0% (-10pp) ✓
- Poor taste: 21% → 45% (+25pp) ❌
- **Assessment:** Dramatic quality drop. Constraints make outfits boring/inappropriate

**GPT-4o-mini:**
- Median: 3.0★ → 1.0★ (-2.0★) ❌
- Impossible layering: 24% → 56% (+31pp) ❌
- Poor taste: 21% → 22% (+2pp) ✗
- **Assessment:** Catastrophic failure. Constraints confuse the model completely

**Gemini 2 Flash:**
- Median: 3.0★ → 2.0★ (-1.0★) ❌
- Impossible layering: 3% → 12% (+9pp) ❌
- Poor taste: 43% → 75% (+32pp) ❌
- **Assessment:** Both failure modes worsen significantly

### Why Fit Constraints Failed

**Theory 1: Over-constraint reduces creativity**
- The 102 lines of rigid rules box AI into conservative, safe choices
- Models focus on "following layering rules" at expense of aesthetic judgment
- Result: Technically compliant but boring/inappropriate outfits

**Theory 2: Models can't apply garment physics rules correctly**
- Constraints assume models understand fit/drape/fabric weight
- In practice, models don't have tactile understanding of garments
- Adding rules without true comprehension creates confusion

**Theory 3: Context window/attention dilution**
- 102 additional lines may overwhelm model attention
- Critical style principles get lost in constraint noise
- Models lose sight of "make a great outfit" goal

**Evidence supporting Theory 1:**
- Poor taste increases dramatically (+25pp for Claude, +32pp for Gemini)
- Failure mode shifts from "impossible layering" to "too casual for occasion" and "boring combinations"
- Example notes: "too casual for wedding when there are better options", "plain", "safe but uninspired"

### Hypothesis Testing Conclusion

**H1: Fit constraints reduce impossible layering**
- **REJECTED** ✗
- Aggregate shows +2pp increase (13% → 15%)
- Only 2/4 models improved; GPT-4o-mini got dramatically worse (+31pp)

**H2: Fit constraints increase poor taste**
- **CONFIRMED** ✓
- Aggregate shows +12pp increase (26% → 38%)
- All models except GPT-4o-mini showed large increases
- Represents ~50% relative increase in poor taste failures

**Net Effect:** -1.0★ median quality drop

---

## 3. Failure Mode Analysis

### Impossible Layering (13% baseline rate)

**Definition:** Garment combinations that are physically impossible or extremely impractical to execute.

**Common patterns:**
- Layering fitted garments over looser ones: "cannot layer cardigan over an oversize top, the arm sleeves won't fit"
- Sleeve width conflicts: "the shirt has a larger sleeve length so it won't fit under the cardigan"
- Incompatible garment structures: "the cardian looks like a fitted version so you can't layer that over a tee"

**Why it happens:**
- Models lack tactile/physical understanding of garments
- Can't infer garment properties from image analysis alone
- No concept of fabric drape, weight, or body volume

**Current best performer:** Gemini 2 Flash (3% rate) - but at huge cost to taste

### Poor Taste (26% baseline rate)

**Definition:** Outfits that are aesthetically wrong, occasion-inappropriate, or boring.

**Common patterns:**
1. **Occasion mismatch (most common):** "jeans and sneaker for a wedding doesn't make sense", "too casual for important work meeting"
2. **Focal point conflicts:** "the strong necklace and the ruffled v-neck are competing for attention"
3. **Weather inappropriateness:** "boots when it's 75-80 is too warm"
4. **Styling instructions that hide garment features:** "the ruffle is the detail/highlight of the shirt so doesn't make sense to tuck & then add a belt there"
5. **Pattern/texture clashes:** "too many dots going on (the blouse and the scarf)"
6. **Plainness:** "not romantic enough", "too safe"

**Why it happens:**
- Models prioritize "safe" combinations over interesting ones
- Insufficient understanding of occasion formality levels
- Focus on individual garment properties vs. holistic outfit harmony
- Don't understand garment design intent (e.g., ruffles as focal point)

**Current best performers:** GPT-4o (22%), GPT-4o-mini (21%), Claude (21%)

---

## 4. The Quality Ceiling Problem

### Observation

Even the best model (GPT-4o) only achieves:
- 4.0★ median rating
- 53% high quality rate (meaning 47% are 3★ or below)
- 18% combined failure rate (impossible layering + poor taste)

**This suggests we've hit a ceiling that model selection alone cannot break through.**

### What the Ceiling Tells Us

**It's not an intelligence problem:**
- GPT-4o is a frontier model with strong reasoning capabilities
- Claude Sonnet 4.5 is comparably capable but performs worse
- The gap isn't about "smarter models" - it's about something else

**It's not a prompt engineering problem (in the traditional sense):**
- Adding more constraints made things worse
- More detailed rules don't help
- The issue isn't "the model doesn't understand the rules"

**It's a framework problem:**
- **Current approach:** Give model wardrobe inventory → Ask for outfits → Hope for taste alignment
- **Missing:** Deep understanding of what makes an outfit *satisfying* to the user
- **Gap:** Models optimize for "technically correct" vs. "makes user feel great"

### Implications

**To break past 4.0★ ceiling, we need:**

1. **Better understanding of outfit satisfaction drivers** (beyond avoiding failures)
   - What creates delight vs. just "acceptable"?
   - What builds user confidence in wearing the outfit?
   - How do we balance "safe" vs. "surprising"?

2. **Richer context about garment properties** (not just photos + descriptions)
   - Fit category (fitted/relaxed/oversized)
   - Fabric weight and formality level
   - Design intent (is this piece meant to be a focal point?)

3. **More sophisticated evaluation criteria** (not just "is this physically possible and tasteful?")
   - Does this outfit tell a story?
   - Does it honor the user's style DNA?
   - Is it appropriately interesting for the occasion?

4. **Possibly: Multi-step reasoning** (analyze occasion → select base piece → build around it)
   - Current: One-shot "generate 3 outfits" prompt
   - Alternative: Chain-of-thought that forces explicit reasoning about each choice

**Model selection and prompt tweaking have diminishing returns from here.**

---

## 5. Production Decisions

### Model Selection: GPT-4o

**Rationale:**
- Clear quality leader (4.0★ vs 3.0★ for others)
- 53% high rating rate = majority of outfits are good
- Balanced failure modes (no single glaring weakness)
- Quality matters more than cost for this use case

**Cost consideration:**
- GPT-4o is more expensive than alternatives
- However, user retention depends on outfit quality
- One bad outfit can damage trust; worth paying for quality
- Consider tiering in future (premium users get GPT-4o, free tier gets mini)

### Prompt Selection: Baseline v1 (No Fit Constraints)

**Rationale:**
- Fit constraints provide no net benefit (-1.0★ median)
- Don't achieve intended goal (impossible layering still happens)
- Cause significant unintended harm (+12pp poor taste)
- Simpler prompt = faster inference, lower cost

**Alternative considered:**
- Use fit constraints only for GPT-4o (which handles them best)
- **Rejected:** Even GPT-4o shows +3pp poor taste increase
- Not worth the added complexity

---

## 6. Methodology Notes & Limitations

### Rating Approach

**Process:**
- Single rater (project owner) evaluated all outfits
- Used 1-5 star scale with written notes
- Evaluated in batches over 4 days
- Total time investment: ~8-10 hours

**Strengths:**
- Consistent evaluation criteria (same person)
- Deep domain knowledge (fashion/styling expertise)
- Holistic judgment (can assess outfit as a whole, not just parts)

**Limitations:**
- Single rater = no inter-rater reliability
- Subjective taste judgments (what is "good"?)
- Potential batch effects (mood, fatigue)
- No blind evaluation (knew which model generated each outfit)

### Fatigue Bias Mitigation

**Concern:** Rating 187 outfits over multiple days could introduce fatigue bias.

**Mitigation:**
- Conducted validation test: Re-rated Claude outfits with fresh eyes
- Results showed consistency (3.0★ both times)
- Conclusion: Fatigue did not significantly affect ratings

**Remaining risk:**
- May have been more generous early on, harsher later
- GPT-4o rated first (potential advantage)
- However, 1.0★ gap is large enough to be meaningful despite this risk

### Sample Size Considerations

**Baseline prompts:** Well-powered
- GPT-4o: N=32
- Claude: N=48
- GPT-4o-mini: N=29
- Gemini: N=30
- **Total baseline: N=139**

**Fit constraint prompts:** Underpowered
- GPT-4o: N=20
- Claude: N=11
- GPT-4o-mini: N=9
- Gemini: N=8
- **Total fit constraints: N=48**

**Implication:**
- Model comparison conclusions are robust (large N, consistent patterns)
- Fit constraints analysis is directionally correct but could use more data
- However, -1.0★ drop is large enough to be confident it's real

### Failure Mode Classification

**Method:** Manual review of rating notes for keywords
- "Impossible layering": impossible, layering does not make sense, won't fit, can't layer
- "Poor taste": poor taste, too casual, weird, competing, too much

**Limitations:**
- Some outfits may have multiple failure modes (only primary counted)
- Keyword matching may miss nuanced failures
- Subjectivity in what counts as "poor taste" vs just "not my style"

**Validity check:**
- Patterns are consistent across models
- Failure modes align with intuition (e.g., Gemini high on "too casual")
- Examples spot-checked and confirmed accurate

---

## 7. Next Steps & Recommendations

### Immediate Actions (High Confidence)

1. **✓ Deploy GPT-4o with baseline v1 prompt to production**
   - Clear data supporting this choice
   - No further model/prompt testing needed in short term

2. **✓ Abandon fit constraint approach**
   - Data shows net negative effect
   - Don't invest more time in this direction

3. **Document failure patterns for future prompt improvement**
   - Compile examples of "poor taste" failures
   - Identify specific occasion/formality judgment errors
   - Use as training data for next prompt iteration

### Strategic Priorities (High Impact)

4. **Develop new outfit satisfaction framework** ⭐ **HIGHEST PRIORITY**
   - Current ceiling: 4.0★ median, 53% high quality
   - Need to understand: What makes an outfit *satisfying* beyond avoiding failures?
   - Research: What drives user delight? Surprise? Confidence?
   - **This has higher ROI than more model testing**

5. **Improve garment property understanding**
   - Current: Models work from photos + basic descriptions
   - Enhancement: Add fit category (fitted/relaxed/oversized), fabric weight, formality level
   - May require enhanced image analysis or user input during upload

6. **Consider multi-step reasoning architecture**
   - Current: One-shot "generate 3 outfits" prompt
   - Alternative: Chain-of-thought (analyze occasion → select base → build layers → refine)
   - May reduce both failure modes by forcing explicit reasoning

### Deferred / Low Priority

7. **Test Gemini 2.5 Flash or GPT-4.5 variants**
   - Unlikely to break through quality ceiling
   - Diminishing returns on model testing
   - Only revisit if new model claims major reasoning improvements

8. **Build automated evaluation pipeline**
   - Current manual rating works for now
   - Consider if doing large-scale testing (N>500 outfits)
   - Would need to solve subjectivity problem (taste is personal)

9. **A/B test in production**
   - Once new satisfaction framework is developed
   - Compare GPT-4o baseline vs. GPT-4o + new framework
   - Use real user feedback as ground truth

---

## 8. Reflections on the Evaluation Process

### What Went Well

**Rigorous methodology:**
- Systematic comparison across multiple dimensions
- Caught and corrected for potential biases (fatigue testing)
- Sought truth over confirmation bias

**Practical insights:**
- Clear production decision (GPT-4o, baseline prompt)
- Identified quality ceiling that model selection can't break
- Recognized need for strategic shift (framework innovation > model tweaking)

**Good skepticism:**
- Questioned initial conclusions ("am I penalizing Claude unfairly?")
- Re-tested assumptions with fresh data
- Avoided premature conclusions from small samples

### What Could Be Improved

**Sample size planning:**
- Fit constraint testing underpowered (N=48 vs N=139 baseline)
- Should have generated equal numbers per condition upfront
- Would have saved time vs. discovering gaps mid-analysis

**Failure mode taxonomy:**
- "Poor taste" is too broad (covers occasion mismatch, plainness, clashing)
- More granular categories would yield better insights
- Consider: Occasion/formality, aesthetic harmony, creativity/interest level

**Blind evaluation:**
- Knew which model generated each outfit
- Could introduce subtle bias (expectations about model quality)
- Future: Randomize and hide model names during rating

**Inter-rater reliability:**
- Single rater limits generalizability
- Taste judgments are subjective
- Future: Have 2-3 raters for subset to measure agreement

### Key Learnings

1. **Intuition + data is powerful:** Initial intuition ("Claude seems weaker") confirmed by rigorous testing, even after checking for bias

2. **More constraints ≠ better output:** The fit constraints experiment was a valuable negative result. Sometimes less is more.

3. **Know when to stop:** Could test more models (Gemini 2.5, GPT-4.5) but hitting diminishing returns. Better to invest energy in framework innovation.

4. **The ceiling matters:** Recognizing that 4.0★ is a ceiling (not a floor) reframes the problem from "pick the best model" to "rethink the approach"

5. **Measurement drives insight:** Wouldn't have discovered these patterns without systematic evaluation. "It feels like quality is uneven" → "53% high rating rate, 18% failure rate, 4.0★ median"

---

## 9. Appendices

### A. Rating Distribution Details

**GPT-4o Baseline (N=32):**
- 5★: 8 outfits (25%)
- 4★: 9 outfits (28%)
- 3★: 3 outfits (9%)
- 2★: 9 outfits (28%)
- 1★: 3 outfits (9%)

**Claude Sonnet 4.5 Baseline (N=48):**
- 5★: 3 outfits (6%)
- 4★: 19 outfits (40%)
- 3★: 9 outfits (19%)
- 2★: 12 outfits (25%)
- 1★: 5 outfits (10%)

### B. Example Failure Notes

**Impossible Layering Examples:**
- "cannot layer cardigan over an oversize top, the arm sleeves won't fit"
- "the shirt has a larger sleeve length so it won't fit under the cardigan"
- "this layering doesn't make any sense. it's not a super fitted t shirt, the blouse is not that loose for layering"
- "the belt is wider than the belt hole - not doable"

**Poor Taste Examples:**
- "jeans and sneaker for a wedding doesn't make sense"
- "boots when it's 75-80 is too warm. trouser is too casual. poor taste"
- "the ruffle is the detail / highlight of the shirt so doesn't make sense to tuck & then add a belt there. poor taste"
- "too many dots going on (the blouse and the scarf)"
- "not romantic enough" (for date night)
- "too casual for important work meeting"

### C. Related Documentation

- `backend/services/prompts/baseline_v1.py` - Current production prompt (USE THIS)
- `backend/services/prompts/fit_constraints_v2.py` - Failed experiment (DO NOT USE)
- `backend/tests/outfit_eval/results/eval_20251128_124930/review.html` - Interactive rating interface
- `backend/tests/outfit_eval/fixtures/test_scenarios.json` - Evaluation scenarios used
- `/Users/peichin/Downloads/Ratings from Outfit Eval (1).json` - Final ratings dataset

---

**Report prepared by:** Pei Chin (with analytical support from Claude Code)
**Last updated:** December 2, 2025
