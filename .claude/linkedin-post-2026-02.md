# LinkedIn Post - Feb 2026

## "Where to Invest Your Effort When Building AI Products"

**Status:** PUBLISHED
**Date:** February 4, 2026

---

---

I've been building an AI styling app for 5 months. Here's what I learned about where to invest effort—and where not to.

**The model is the ceiling. Your job is extraction.**

We ran A/B tests: does sending wardrobe images help the AI create better outfits?

Results (GPT-5.2):

| | Text-Only | + Vision |
|---|---|---|
| Bad outfits | 7 | 7 |
| Mediocre | 2 | 9 |
| Great | 26 | 20 |

Vision didn't fix physics errors. It just converted great outfits into mediocre ones. Same floor, lower ceiling.

The model "plays it safe" when it can see the items. We wanted fewer failures. We got fewer standouts.

**The question to ask:** Am I hitting the ceiling, or is there more to extract?

---

### Where TO invest:

**1. Data preparation (the "silent middle")**

User feedback: "The app keeps suggesting the same items—specific skirt, certain earrings."

Root cause: We passed wardrobe items in the same order every time. LLMs have position bias—middle items get ignored.

Fix: Seeded daily shuffle. 5 lines of code. Result: even item usage across the wardrobe.

Small data prep changes, big impact.

**2. Prompts over code**

We had ~75 lines of orchestration:
```
if occasion == "work": filter formal items
if weather == "cold": add layering
```

Now it's 3 lines:
```
agent = StylingAgent(user_id)
agent.run(message)
```

Good tools are dumb CRUD operations. Intelligence lives in prompts, not code.

The eigenquestion: "To change behavior, do I edit the prompt or refactor code?" If refactor → your tool is too smart.

**3. Emotional resonance > literal accuracy**

We A/B tested outfit visualization:
- Personal photo: "uncanny valley", "like a remote relative"
- Demographically-similar model: "I could pull this off"

[📷 Image: side-by-side comparison]

Personalization isn't literal accuracy. It's aspiration.

---

### Where NOT to invest:

**The "waiting for model" bucket**

Some problems need model breakthroughs, not engineering:

1. **Latency:** 34 seconds per outfit is too slow. Even GPT-5.2 adds +7% for vision.

2. **World model gap:** The AI can EXPLAIN why ruffles create bulk when tucked. But it won't APPLY that when styling an outfit. Pattern matching overpowers reasoning.

3. **Try-on complexity:** Runway's model handles 2-3 items cleanly. At 5+ items, it merges garments into impossible shapes.

[📷 Image: 5-item outfit where top+skirt merged into dress]

4. **Visualization latency:** 60-90 seconds per image. Too slow for first-load.

Engineering won't solve these. We're waiting for model breakthroughs.

---

### The meta-lesson: Look deeper than your metrics

| Model | Quality Score | Items/Outfit |
|---|---|---|
| GPT-4o | 73% good | 4.0 items |
| GPT-5.2 | 79% good | 4.7 items |

Quality scores hid something: GPT-5.2 produces more complete outfits—accessories, layers, bags. A "good" 4-item outfit vs a "good" 6-item outfit both rate "good," but one is objectively more styled.

Your evaluation framework matters as much as your engineering.

---

**Summary:**

| Invest here | Don't invest here |
|---|---|
| Data prep (shuffling) | Vision (doesn't fix physics) |
| Prompts > code | Fighting latency with engineering |
| Emotional resonance | Literal personalization |
| Evaluation frameworks | Waiting problems |

The model is the ceiling. Your job is maximum extraction from whatever exists today.

---

## Final Published Version:

In the past few weeks I feel viscerally that the model is the ceiling, and my job is to extract as much as I can with the right product support. It also clarifies where to invest my energy vs. waiting for the model to improve.

=== Where to invest ===
1. Address 'lost in the middle' by randomizing data order
2. A 'hotter version of myself' >> reality
3. Model quality vs. latency tradeoffs (GPT-4o vs GPT-5.2)

=== Where NOT to invest (waiting for models) ===
1. Physical interaction between garments (world model gap)
2. Try-on complexity (5+ pieces breaks)

Plus: Agent demo (WhatsApp video)
