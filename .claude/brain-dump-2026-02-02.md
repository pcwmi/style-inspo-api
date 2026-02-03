# Brain Dump - 2026-02-02

## 13:58 - Daily Analysis Insights & Vision-at-Runtime

**Observations from Dana's daily digest:**
- Most unsaved outfits are physically nonsensical layering (the recurring problem)
- Bright spot: blazer + sweater + skirt layering worked well - shows AI *can* get it right

**Key insight: Text vs Vision analysis quality**
- When Claude analyzed outfits from text metadata only → shallow analysis
- When GPT-4o looked at actual garment images → much richer, more accurate analysis
- The model can SEE the ruffles, the bulk, the texture clashes when given images

**Implication:**
This validates resuming work on **visual images at runtime** for outfit generation.

If the AI can't "see" what it's combining, it's pattern-matching on text ("tuck shirt into skirt") without understanding THIS shirt has ruffles that would bunch.

**The hypothesis:**
Adding vision to the generation loop (not just post-hoc analysis) could dramatically reduce physically nonsensical suggestions.

**Open questions:**
- Latency impact of vision calls during generation?
- Send all item images at once, or just the "risky" combinations?
- Can we use vision to validate BEFORE returning to user?

---

## 14:15 - Historical Context: Why Text-First Architecture?

**Timeline of model releases vs Style Inspo development:**

| Date | Event |
|------|-------|
| March 2023 | GPT-4 released (text only) - $30/1M input, $60/1M output |
| **Sept 2023** | **Style Inspo prototype started** - GPT-4V didn't exist yet |
| Nov 2023 | GPT-4V (vision-preview) released - $10/1M input, $30/1M output |
| **May 2024** | **GPT-4o released** - $2.50/1M input, $10/1M output (vision included) |
| July 2024 | GPT-4o mini - $0.15/1M input, $0.60/1M output |
| **Sept 2025** | Style Inspo rebuilt with FastAPI/Next.js - inherited text-first architecture |
| Feb 2026 | Today - realizing vision would help |

**Why we chose text-first (reconstructed reasoning):**

1. **Original prototype predated vision** - When Style Inspo started in Sept 2023, GPT-4V literally didn't exist. Text metadata was the only option.

2. **Inherited architecture** - By Sept 2025 rebuild, we had rich text metadata (colors, style_tags, descriptions) and never questioned if vision would be better.

3. **Cost perception outdated** - GPT-4V in Nov 2023 was expensive ($10/1M input). By May 2024, GPT-4o made vision 75% cheaper, but we didn't revisit the decision.

4. **"Good enough" assumption** - Text metadata seemed sufficient. We never A/B tested vision vs text for outfit quality.

**The missed opportunity:**
- GPT-4o (May 2024) made vision cheap and fast
- We rebuilt the entire app in Sept 2025 but kept text-only generation
- 8 months of "physically nonsensical" outfits that vision might have caught

**Current GPT-4o vision costs (Feb 2026):**
- Low-detail image: 85 tokens (~$0.0002 per image)
- High-detail image: up to 1,100 tokens (~$0.003 per image)
- 50 wardrobe items at low-detail = ~4,250 tokens = ~$0.01 per generation

**Conclusion:** Text-first wasn't a deliberate choice—it was path dependence from Sept 2023. Time to test vision.

Sources:
- [OpenAI Pricing](https://openai.com/api/pricing/)
- [GPT-4o Wikipedia](https://en.wikipedia.org/wiki/GPT-4o)
- [GPT-4 Vision Pricing Calculator](https://www.helicone.ai/llm-cost/provider/openai/model/gpt-4-vision-preview)

---

## 16:45 - Vision A/B Test Results: Images Don't Help

**Experiment:** Does sending wardrobe images to GPT-4o reduce physically nonsensical outfit suggestions?

**Setup:**
- Control: Chain-of-thought prompt (production) with text metadata only
- Treatment: Same CoT prompt + wardrobe images (22 items, low-detail = 85 tokens each)
- Tested on Dana's wardrobe (known to have problematic generations)

**Results:**
| Metric | CoT Text-Only | CoT + Vision |
|--------|--------------|--------------|
| Cost | ~$0.018/gen | ~$0.023/gen (+27%) |
| Latency | ~17s | ~39s (+130%) |
| Quality | Bad physics | **Still bad physics** |

**Failure modes observed (even with vision):**

1. **Chunky vest over cardigan** - "Cardigan buttoned, vest layered on top"
   - Model can SEE the chunky knit texture
   - Still suggests layering it over a fitted cardigan
   - Confabulates: "The cropped cardigan layers smoothly under the vest"

2. **Short sleeves under long sleeves** - "Blouse tucked into skirt, sweater over blouse"
   - Blouse is short-sleeve, sweater is long-sleeve V-neck
   - Short sleeves bunched under long = uncomfortable
   - V-neck shows nothing (collar won't peek through properly)

**Key insight:** Vision doesn't help because the model lacks **embodied knowledge** of how garments interact with bodies.

It can SEE:
- ✅ The chunky knit texture
- ✅ The short sleeves
- ✅ The V-neck shape

It doesn't KNOW:
- ❌ Chunky knit creates bulk that disrupts fitted layers
- ❌ Short sleeves under long sleeves = shoulder bunching
- ❌ V-necks need visible layers (crew neck, turtleneck), not collars

**The model pattern-matches:**
- "vest = layering piece" → suggests layering (regardless of fabric weight)
- "sweater over blouse = classic combo" → suggests it (regardless of sleeve lengths)
- Generates confident but false justifications

**Conclusion:** This appears to be a **fundamental limitation**, not a prompting problem.

**Options going forward:**
1. **Hard-code constraints in metadata** - `"layering_constraint": "too bulky to layer"` (giving up on reasoning)
2. **Accept limitation** - Focus product on value props that don't require physical reasoning
3. **Human-in-loop** - Flag "risky" combinations for human review before showing user

**Cost of vision experiment:**
- ~$0.15 total for 6 scenarios × 2 variants
- Latency: 2x slower with images
- Conclusion: Not worth pursuing further

---

## 17:25 - Frontier Model A/B Test: GPT-5.1 Text vs Vision

**Follow-up question:** Does vision help with a more capable model?

**Setup:**
- GPT-5.1 (Text-Only): chain_of_thought_v1 prompt
- GPT-5.1 (Vision): vision_cot_v1 prompt (same CoT + images)
- 22 items from Dana's wardrobe

**Results:**

| Variant | Problematic Layering? | Example |
|---------|----------------------|---------|
| **GPT-5.1 Text-Only** | YES | Outfit 3: "Navy oversized sweater + Beige sleeveless knit vest" (vest over bulky sweater) |
| **GPT-5.1 Vision** | NO | All 3 outfits had physically reasonable layering |

**GPT-5.1 Vision outfits (all OK):**
1. Denim skirt + fuzzy sweater + blazer + flats ✅
2. Oversized sweater + burgundy tee (peeking out) + jeans + boots ✅
3. Cropped denim shirt + cropped cardigan (open over shirt) + jeans + flats ✅

**Key finding:** Vision DOES help with GPT-5.1. The earlier negative result was with GPT-4o.

**Hypothesis:** GPT-5.1 has better visual reasoning that translates to physical understanding when given images. GPT-4o could see but couldn't reason about physical consequences.

**o3 Results:** Not compatible - returns empty responses (both text and vision).

**Cost/latency:**
| Variant | Latency | Cost |
|---------|---------|------|
| GPT-5.1 Text | 31.2s | ~$0.02 |
| GPT-5.1 Vision | 33.2s | ~$0.02 |

Vision adds only ~2 seconds with GPT-5.1. Much better than GPT-4o's 2x latency hit.

**Implication:** For production, consider GPT-5.1 + Vision as the premium tier. The physics reasoning improvement may justify the cost.

**Open question:** Is this result consistent across multiple runs, or did we get lucky?

---

## 17:45 - Multi-User Vision A/B Test: Wardrobe-Dependent Results

**Follow-up experiment:** Test GPT-5.1 Text vs Vision across 4 different wardrobes to see if vision consistently helps.

**Setup:**
- GPT-5.1 (Text-Only): chain_of_thought_v1 prompt
- GPT-5.1 (Vision): vision_cot_v1 prompt (same CoT + images)
- 4 users: Dana, Alexi, Pei-chin, Kate
- 2 scenarios each: casual brunch, work meeting (8 test cases per variant)

**Results Summary:**

| User | Text-Only | Vision | Verdict |
|------|-----------|--------|---------|
| Dana | ❌ Physics (vest over sweater) | ✅ Clean | Vision helps |
| Alexi | ❌ Physics (top on top) | ⚠️ Taste issues | Vision converts physics→taste |
| Pei-chin | ✅ Clean | ⚠️ Style clutter | Vision may hurt |
| Kate | ✅ Clean | ✅ Clean | No difference |

**Detailed observations:**

1. **Dana** - Vision clearly helps
   - Text-only: "Navy oversized sweater + Beige sleeveless knit vest" (vest over bulky sweater)
   - Vision: All outfits physically reasonable

2. **Alexi** - Vision trades physics for taste problems
   - Text-only: "Black ribbed short-sleeve button-up top + Grey open-knit short-sleeve cardigan" (layering issue)
   - Vision: "White short-sleeve button-up shirt + Rust Corduroy Button-Up Jacket" (works physically, but doesn't fit her edgy street aesthetic)

3. **Pei-chin** - Vision introduces clutter
   - Text-only: Clean, no issues
   - Vision: "Bow tie blouse + crochet cardigan + layered necklace" (too many competing elements)

4. **Kate** - Both variants work fine
   - No physics issues either way
   - Wardrobe may be more "forgiving" (fewer tricky textures/silhouettes)

**Cost/latency comparison:**
| Variant | Avg Latency | Cost |
|---------|-------------|------|
| GPT-5.1 Text | ~31s | ~$0.02 |
| GPT-5.1 Vision | ~37s (+19%) | ~$0.02 |

**Key insight:** Vision converts physics problems into taste problems.

This is an improvement in one sense (physics violations are objectively wrong, taste is subjective), but suggests:
- Vision helps the model avoid impossible layering
- Vision does NOT help with style editing (knowing when to simplify)
- Some wardrobes (detailed/accessory-heavy) may be worse with vision

**Why wardrobe-dependent?**
- **Dana**: Many chunky knits, vests - vision helps see bulk
- **Alexi**: Street/edgy style - vision sees items but doesn't understand aesthetic
- **Pei-chin**: Many accessories and details - vision sees MORE and suggests MORE
- **Kate**: Classic pieces - fewer edge cases to begin with

**Conclusion: Vision is NOT a clear win.**

Not shipping as default. The trade-off is wardrobe-dependent:
- Wardrobes with tricky textures → vision helps
- Wardrobes with lots of details → vision may hurt
- Simple/classic wardrobes → no difference

**Possible future approach:** Use vision selectively for "risky" items (knits, layers) rather than entire wardrobe.

**Test artifacts:**
- Results: `backend/tests/outfit_eval/results/multi_user_ab_test_20260202_174127.html`
- Script: `backend/tests/outfit_eval/scripts/frontier_model_test.py`

---

## 18:30 - Three Dimensions of AI Quality Tuning (Interdependent)

**The framework:**

| Level | What it is | Your control | Example |
|-------|------------|--------------|---------|
| **1. Model capability** | Raw reasoning ability | ❌ Wait for releases | GPT-5.1 >> 4o for garment physics |
| **2. Data/enrichment** | What you feed the model | ✅ Architecture choice | Text vs images, metadata richness |
| **3. Prompt** | How you instruct | ✅ Continuous tuning | Chain-of-thought, physics rules |

**Critical insight: The dimensions are INTERDEPENDENT, not orthogonal.**

Evidence from today's testing:
- **GPT-4o + images:** No improvement over text metadata
- **GPT-5.1 + images:** Helps reduce physics violations

Same Level 2 intervention (adding images), different results based on Level 1.

**Why this happens:**
Level 1 sets the **ceiling**. Levels 2 & 3 determine how close you get to it.
- If the model CAN'T reason about garment physics, better data doesn't help
- If the model CAN reason about it, better data gives it more to work with

**Implication for testing strategy:**
When one dimension changes significantly → re-test the others.

```
New model released (L1 changes)
    → Re-test data strategies (L2)
    → Re-test prompt approaches (L3)
    → Previous findings may be invalidated
```

It's not "test once, done forever." It's continuous recalibration as the landscape shifts. Your Level 2/3 investments aren't wasted - they compound with Level 1 improvements, but their impact varies depending on where the ceiling is.

**Practical workflow:**
1. When new model drops → quick smoke test on core use case
2. If quality jumps → re-run key A/B tests (data, prompts)
3. Findings are timestamped to model version, not permanent truths

---

## 18:45 - The Magic Extractor Framing

**You're not building AI. You're extracting maximum magic from it.**

```
┌─────────────────────────────────────┐
│           MODEL CEILING             │  ← Outside your control
├─────────────────────────────────────┤
│                                     │
│    ↑ Your job: climb as high as    │
│      possible with data + prompts   │
│                                     │
│    ┌───────────────────┐           │
│    │  Current magic    │           │
│    │  extraction       │           │
│    └───────────────────┘           │
│                                     │
└─────────────────────────────────────┘
```

**What this framing clarifies:**

1. **When to stop optimizing:** If you're at 90% of the ceiling → diminishing returns on data/prompts. Wait for ceiling to rise (new model), then climb again.

2. **Why domain experts beat ML researchers at AI products:** The best AI product builders aren't necessarily ML researchers - they're **magic extractors** who deeply understand the domain and translate that into data + prompts the model can use.

3. **What your work actually is:** Styling constitution, feedback patterns, physics rules in prompts - that's domain knowledge being converted into "extraction efficiency."

**The job:** Maximum magic extraction from whatever model exists today.
