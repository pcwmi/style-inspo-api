# A/B Test: Baseline vs Chain-of-Thought Prompting

**Date Created**: December 7, 2025
**Hypothesis**: Chain-of-thought prompting pushes models toward creative tail (5-star outputs) vs 4-star plateau

---

## Background

### The 4-Star Problem

From eval results and brain-dump insights:
- Models naturally create "most likely" outputs (statistical center of training data)
- 4-star results = safe, predictable combinations
- 5-star results = creative tail, unexpected perfect choices
- RLHF makes this worse (penalty for bad > reward for exceptional)

### The Solution

**4-star prompts describe outputs** ("create outfits that honor your style")
**5-star prompts guide reasoning process** (step-by-step compositional thinking)

---

## Test Setup

### Prompt Variants

**Baseline** (`baseline_v1`):
- Declarative principles: "All outfits MUST honor style DNA..."
- Tells model WHAT to do
- Current production prompt

**Chain-of-Thought** (`chain_of_thought_v1`):
- Explicit reasoning steps: "STEP 1: FUNCTION... STEP 2: ANCHOR..."
- Tells model HOW to think
- New prompt variant (Dec 2025)

### Key Differences

| Aspect | Baseline | Chain-of-Thought |
|--------|----------|------------------|
| **Approach** | Declarative rules | Step-by-step reasoning |
| **Unexpected Element** | Optional/implicit | Explicitly required |
| **Style DNA** | Must be present | Must name which piece carries which word |
| **Anchor Selection** | Implied | Explicit "hero piece" selection |
| **Positioning** | Expert stylist | Fashion editor for "Best Dressed" |

### Model Configurations

**Primary Test**: GPT-4o
- `gpt4o_baseline` vs `gpt4o_chain_of_thought`
- Same model, same temp (0.7), only prompt differs
- Max tokens: 2000 vs 3000 (reasoning needs more space)

**Secondary Test**: Claude Sonnet 4.5
- `claude_sonnet_45_baseline` vs `claude_sonnet_45_chain_of_thought`
- Validate if effect is model-agnostic

---

## How to Run the Test

### Quick Test (Outdoor Wedding Scenario)

```bash
cd /Users/peichin/Projects/style-inspo-api/backend
source venv/bin/activate

# Run baseline
STORAGE_TYPE=s3 python3 tests/outfit_eval/scripts/run_eval.py \
  --user-id peichin \
  --scenario outdoor_wedding \
  --models gpt4o_baseline \
  --iterations 3

# Run chain-of-thought
STORAGE_TYPE=s3 python3 tests/outfit_eval/scripts/run_eval.py \
  --user-id peichin \
  --scenario outdoor_wedding \
  --models gpt4o_chain_of_thought \
  --iterations 3
```

### Full A/B Comparison

```bash
# Run both prompts on same scenario
STORAGE_TYPE=s3 python3 tests/outfit_eval/scripts/run_eval.py \
  --user-id peichin \
  --scenario outdoor_wedding \
  --models gpt4o_baseline gpt4o_chain_of_thought \
  --iterations 5
```

### Generate HTML Review

After running eval, generate visual review:

```bash
STORAGE_TYPE=s3 python3 tests/outfit_eval/scripts/generate_diagnostic_html.py
```

---

## What to Look For

### Success Indicators

**More Creative Diversity**:
- ❓ Are different anchor pieces selected across iterations?
- ❓ Do outfits avoid white sneakers/basic tees default?
- ❓ Are unexpected elements actually unexpected?

**Better Style DNA Integration**:
- ❓ Can you identify which piece carries which style word?
- ❓ Does the composition create intentional tension?
- ❓ Do all three words feel present (not just checked off)?

**Reasoning Quality**:
- ❓ Does the reasoning make sense?
- ❓ Are "unexpected elements" truly unexpected (not just labeled)?
- ❓ Do you believe the "why it works" explanations?

###  Failure Modes

**Chain-of-thought could fail if**:
- Model treats reasoning as performative (goes through motions)
- Reasoning steps don't actually shift probability distribution
- Increased tokens = more verbose but not more creative
- "Unexpected element" becomes formulaic ("wrong shoe theory" every time)

**Success = Creative tail, not just different 4-stars**

---

## Evaluation Criteria

### Quantitative (Track These)

1. **Anchor Diversity**: How many unique anchor pieces across N iterations?
2. **Item Repetition**: % of items appearing in 2+ outfits
3. **White Sneaker/Shirt Usage**: Are we still defaulting to safe choices?
4. **Reasoning Token Count**: Is reasoning substantive or filler?

### Qualitative (Your Gut Check)

1. **Would you actually wear this?**
2. **Does this feel like YOU (style DNA present)?**
3. **Is the unexpected element truly unexpected?**
4. **Would someone say "I wouldn't have thought of that"?**
5. **Is this a 5-star outfit or just a different 4-star?**

---

## Next Steps After Results

### If Chain-of-Thought Wins

1. Run larger eval (10+ iterations, multiple scenarios)
2. Test with other models (Claude, Gemini)
3. Consider making it production prompt
4. Document which reasoning steps matter most
5. Iterate on prompt structure

### If Baseline Wins (or Tie)

1. Analyze why chain-of-thought didn't help
2. Check if reasoning is performative
3. Try different reasoning structure
4. Consider if 5-star outputs require different approach
5. Document learnings

### If Results Are Mixed

1. Identify which dimensions improved
2. Extract the effective reasoning steps
3. Hybrid approach: declarative + selective reasoning
4. Test refined version

---

## Files Modified

- ✅ `/backend/services/prompts/chain_of_thought_v1.py` - New prompt template
- ✅ `/backend/services/prompts/library.py` - Registered in prompt library
- ✅ `/backend/tests/outfit_eval/fixtures/model_configs.yaml` - Added test configurations

---

## Related Documents

- `.claude/brain-dump-2025-12-04.md` - Core insights on 4-star vs 5-star
- `backend/tests/outfit_eval/DIAGNOSTIC_REVIEW.html` - Visual review of diagnostic results
- `backend/tests/outfit_eval/HTML_GENERATION_REFERENCE.md` - How to generate HTML reviews

---

**Ready to run?** Start with the Quick Test to see if this approach has legs. If you see promising signals, scale up to full eval.
