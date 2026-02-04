# Brain Dump - 2026-02-03

## 21:45 - GPT Model Comparison for AI Outfit Generation: Vision, Quality, and Latency

### The Questions

We ran rigorous A/B tests to answer two questions:
1. **Does sending wardrobe images to the model improve outfit quality?**
2. **How do we trade off quality vs latency across model generations?**

---

### Question 1: Is Vision Worth It?

**Hypothesis:** If the AI can "see" the actual garments (textures, bulk, silhouettes), it should avoid physically nonsensical combinations like tucking a ruffled shirt or layering a chunky vest over a bulky sweater.

**Test Design:**
- GPT-4o: Text metadata only vs Text + Images
- GPT-5.1: Text metadata only vs Text + Images
- GPT-5.2: Text metadata only vs Text + Images
- 4 users × 3 scenarios × 3 outfits = 36 outfits per variant
- Rated good/ok/bad by human evaluator

**Results:**

| Model | Text-Only | + Vision | Verdict |
|-------|-----------|----------|---------|
| GPT-4o | Bad physics | Still bad physics | Vision doesn't help |
| GPT-5.1 | Some physics errors | Fewer physics errors, but taste problems | Mixed |
| GPT-5.2 | 7 bad, 2 ok, 26 good | 7 bad, 9 ok, 20 good | Vision makes outfits mediocre |

**The Surprising Finding:** Vision doesn't reduce failures (same "bad" count). Instead, it shifts "good" outfits to "ok" outfits.

**Why?**

1. **GPT-4o could see but couldn't reason.** It recognized chunky knit texture but still suggested layering it under a fitted blazer. The model pattern-matches on text ("vest = layering piece") without understanding physical consequences.

2. **GPT-5.1 traded physics for taste.** Vision helped avoid impossible layering, but introduced bland/safe choices. One user's edgy street aesthetic got replaced with "safe" combinations.

3. **GPT-5.2 vision produced mediocrity.** Same failure rate, but fewer standout outfits. The model seems to "play it safe" when it can see the items.

**Latency cost of vision:**
- GPT-4o: +130% latency (17s → 39s)
- GPT-5.1: +19% latency (31s → 37s)
- GPT-5.2: +7% latency (31.9s → 34.1s)

**Conclusion:** Vision is not worth it.
- Doesn't reduce failures
- Produces more mediocre outfits
- Adds latency
- Adds cost (~$0.007 per generation for image tokens)

The model lacks "embodied knowledge" of how garments interact with bodies. It can SEE the chunky knit but doesn't KNOW that chunky knit creates bulk that disrupts fitted layers.

---

### Question 2: Quality vs Latency Tradeoff

**Test Design:**
- GPT-4o vs GPT-5.2 (text metadata only, same prompt)
- 4 users × 3 scenarios × 3 outfits = 36 per model
- Measured: latency, good/ok/bad ratings, items per outfit

**Latency Results:**

| Model | Avg Latency | Range |
|-------|-------------|-------|
| GPT-4o | 20.0s | 15.7-26.8s |
| GPT-5.2 | 33.7s | 27.3-42.2s |

GPT-4o is **1.7x faster**.

**Quality Results:**

| Model | Good | OK | Bad | Quality Score |
|-------|------|-----|-----|---------------|
| GPT-4o | 22 | 7 | 6 | 73% |
| GPT-5.2 | 28 | 1 | 7 | 79% |

GPT-5.2 is **+6% better quality**.

**But quality score misses something important: outfit completeness.**

| Model | Avg Items/Outfit | Distribution |
|-------|------------------|--------------|
| GPT-4o | 4.0 | 97% have exactly 4 items |
| GPT-5.2 | 4.7 | 47% have 5-6 items |

GPT-5.2 produces **18% more items per outfit** - more accessories, more layers, more complete looks.

A "good" GPT-4o outfit with 4 basic items (top, bottom, shoes, jacket) vs a "good" GPT-5.2 outfit with 6 items (adding scarf, jewelry, bag) - both rated "good" but 5.2 is objectively more styled.

**The Real Tradeoff:**

| | GPT-4o | GPT-5.2 |
|---|--------|---------|
| Latency | 20.0s | 33.7s (+68%) |
| Quality score | 73% | 79% (+6%) |
| Outfit completeness | 4.0 items | 4.7 items (+18%) |
| "Good" quality | ~6-7/10 | ~8/10 |

---

### Question 2b: GPT-5.1 vs GPT-5.2

Since production was on GPT-5.1, we also compared:

| Model | Latency | Quality |
|-------|---------|---------|
| GPT-5.1 | 35.2s | 72% |
| GPT-5.2 | 31.9s | 77% |

**GPT-5.2 is a pure upgrade over 5.1:**
- 9% faster (3.3s less)
- 5% better quality
- Same cost

OpenAI's claim of "40% faster inference with same weights" shows up as ~9% improvement in our end-to-end measurements.

---

### Final Decisions

1. **Vision: NO.** Don't send images. It doesn't reduce physics errors, makes outfits mediocre, adds latency and cost.

2. **Model choice: GPT-5.2.**
   - If on 5.1: Upgrade to 5.2. Pure win, no tradeoff.
   - If considering 4o for speed: Accept 68% more latency for meaningfully better outfits.

3. **Latency budget:** The extra 13.7s for GPT-5.2 (vs 4o) buys you more complete, more styled outfits. For a styling app where quality matters, this is worth it.

---

### Meta-Learning: How to Evaluate AI Quality

**Rating scales miss dimensions.** Good/ok/bad doesn't capture:
- Outfit completeness (number of items)
- Quality ceiling within "good" (6/10 vs 8/10)
- Styledness vs basic functionality

**Look at the outputs, not just the scores.** The item count analysis revealed what ratings obscured: GPT-5.2 produces more thoughtful, complete outfits.

**Vision ≠ understanding.** Models can see images without understanding physical consequences. "Seeing" a chunky knit doesn't mean knowing it creates bulk. This is a fundamental limitation, not a prompting problem.

**Test the tradeoff space systematically.** We tested:
- Data enrichment (text vs vision)
- Model capability (4o vs 5.1 vs 5.2)
- Held prompt constant (chain_of_thought_v1)

This isolates variables and produces actionable conclusions.
