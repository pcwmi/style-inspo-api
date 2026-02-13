# Brain Dump - 2026-02-12

## Process Note: Always View Images When Reviewing Twilio Logs

**When reviewing SMS/WhatsApp logs that include user images, ALWAYS download and view the actual image** to understand the full context. Text-only analysis misses critical information about what the user is actually wearing/showing.

---

## 10:45 - Visualization & Agent Architecture Insights

### Try-On / Visualization

**1. Faster & cheaper model discovered**
- gen4_image_turbo works well for try-on, lower latency/cost than standard gen4

**2. Pre-composite vs nested calls - a mental model shift**
- Old software intuition: "3 image slots → 3 API calls or nested logic"
- New thinking: "What can the MODEL do?" → Pre-composite leverages model's ability to parse flat-lay collages
- Pre-composite = 1 call, same result, model does the work
- Further optimized: multi-collage across all 3 slots (525px/item vs 346px/item = 52% better fidelity)

**Key insight:** When working with generative models, think about what the MODEL can handle, not what traditional software patterns would suggest. The model's capability is the API.

### Agent Architecture Concern

**"Agentic spaghetti code" - are we building it?**

We're adding features to the SMS agent by editing prompts:
- MODE: GENERATE / REFINE / RESTORE
- "If user mentions specific item + rest OK → REFINE"
- Outfit history in context prefix
- Feedback patterns in context

This feels like whack-a-mole:
1. User reports problem
2. Add prompt clause to handle edge case
3. Repeat

**The concern:** Is this the agentic version of spaghetti code? Features scattered across prompt sections, no clear architecture, hard to reason about holistically.

**Questions to explore:**
- What's the "clean architecture" equivalent for agentic prompts?
- Should MODE classification be a separate, testable component?
- Is there a way to unit test prompt behavior like we test code?
- Or is this just the nature of LLM development - iterate on prompt until it works?

**Counter-argument:** Maybe this IS the right approach for now. We're learning what the agent needs to do. Premature abstraction in prompts could be worse than spaghetti. Ship, learn, refactor later.

**The eigenquestion:** When do prompt edits become "prompt debt" that needs refactoring vs. just normal iteration?

---

### Technical Details (for future reference)

**Multi-collage slot distribution:**
- 4 items → 2+2
- 5 items → 2+2+1
- 6 items → 2+2+2
- 7 items → 2+2+3
- 8+ items → 3+3+rest

**Outfit history implementation:**
- `conversation_state.py` stores last 3 outfits
- Agent context shows history for "go back" requests
- MODE: RESTORE handles restoration

**Still unsolved:**
- Context-specific feedback ("cowboy boots bad IN THIS OUTFIT" vs globally)

---

## 11:00 - Feedback Architecture: Accumulation vs Synthesis

### The Problem

Current feedback flow:
```
User feedback → raw storage → agent reads ALL → applies each one
```

No synthesis layer. Agent sees:
```
- Don't use cowboy boots (too western for Parisian look)
- Don't use ruffles with wide pants
- Don't use oversized top + wide pants
- ...accumulates forever...
```

**Problems with accumulation:**
1. Context window fills up as feedback grows
2. Specific feedback gets over-generalized ("cowboy boots bad in THIS outfit" → "never use cowboy boots")
3. Agent must synthesize on-the-fly every time (expensive, inconsistent)
4. No learning - just avoiding

### What Synthesis Would Look Like

Instead of raw feedback, agent would see:
```
Style Principles (extracted from 15 feedback instances):
- Prefers streamlined silhouettes (not oversized + wide)
- Avoids costume-y/western vibes in casual settings
- Likes pattern mixing BUT not more than 2 patterns
```

**Benefits:**
- Compact context (principles, not instances)
- Generalizes appropriately
- Explicit reasoning the agent can apply

### The Architectural Question

Should synthesis be:
1. **Pre-computed** - Background job that periodically extracts principles from raw feedback
2. **On-demand** - Before outfit generation, quick LLM call to synthesize recent feedback
3. **Layered** - Raw feedback + extracted principles, agent sees both

**Trade-off:** Pre-computed is cheaper but stale. On-demand is fresh but adds latency.

### Connection to "Agentic Spaghetti"

This is the same pattern:
- Prompt MODE rules = accumulated edge cases
- Feedback patterns = accumulated raw instances
- Context prefix = accumulated state

Each "fix" adds more to accumulate. No synthesis/compression layer anywhere.

**The eigenquestion:** At what scale does accumulated context become unmaintainable, and what's the minimum viable synthesis layer?

---

## 11:20 - The Agent CAN Synthesize (It Just Doesn't Persist)

### The Discovery

When user asked: **"Based on what you know about me what do I like and dislike"**

Agent did:
```
1. get_profile() → style words
2. get_feedback_patterns() → dislikes
3. get_saved_outfits() → likes
4. get_feedback() → raw feedback
5. get_items() → wardrobe patterns
```

Then produced: **"You're classic • playful • relaxed—but with a very specific edit: you like 'unexpected' when it still reads intentional and clean."**

Plus: "You tend to like: High-low mixing..."

### The Problem

This synthesis is:
- **On-demand** - only happens when explicitly asked
- **Ephemeral** - not stored anywhere
- **Expensive** - 5 tool calls + LLM reasoning every time

Next outfit request? Agent doesn't remember this synthesis. It either:
1. Re-gathers all data and re-synthesizes (expensive)
2. Just applies raw feedback rules (loses the "mental model")

### The Fix Idea: Persistent Style DNA

When agent produces synthesis like this, **store it**:

```python
# New primitive: update_style_dna
{
    "summary": "classic • playful • relaxed with intentional unexpected edits",
    "likes": ["high-low mixing", "polished + casual", "one statement piece"],
    "dislikes": ["costume-y vibes", "too-matched", "oversized + oversized"],
    "synthesized_at": "2026-02-12T18:40:53Z",
    "based_on": {"feedback_count": 5, "saved_count": 12}
}
```

Then in outfit generation, agent reads compact `style_dna` instead of gathering/synthesizing every time.

### Trade-off

- **Pro**: Consistent understanding, cheaper generation, explicit mental model
- **Con**: Staleness (needs refresh trigger), another data structure to maintain

### The Bigger Pattern

This connects to "agentic spaghetti" concern:
- We keep adding raw data (feedback, outfits, history)
- Agent must synthesize on-the-fly
- Synthesis is expensive and inconsistent
- Solution: **compress raw data into principles, persist the compression**

---

## 11:30 - Missing MODE: AUGMENT (Add to What You're Already Wearing)

### The Interaction

User sent photo of half-done outfit (denim shirt + jeans) + "How can I style this better"

**What agent did (4-star):**
- MODE: ANSWER (zero tool calls)
- Gave 3 styling directions: "scarf as belt", "cinch the waist", etc.
- Good thinking, but stopped at advice

**What 5-star looks like:**
- Recognize user is ALREADY WEARING something
- Call wardrobe tools to find specific pieces that match each direction
- Generate 3 outfit options that ADD to what they're wearing:
  - "Direction 1: Add [specific scarf] + [specific belt] from your closet"
  - "Direction 2: Add [specific jacket] to break up the denim"
  - "Direction 3: ..."

### The Follow-up Failures

**Failure 1: Didn't pick items on positive feedback**

User said: "I like the scarf and belt idea" → This is a **nudge to pick specific items**

Agent: Just acknowledged ("noted: you love the scarf + belt move") instead of picking items

**Failure 2: Changed the base when finally picking**

User had to explicitly say: "Pick the pieces for me"

Then agent CHANGED THE BASE:
- Original: User's denim shirt + jeans (what they were WEARING)
- Agent returned: White button-up + different jeans (completely different outfit)

### Root Cause: Missing AUGMENT Mode

Current MODEs:
- GENERATE = start from scratch
- REFINE = swap one item
- RESTORE = go back to previous

**Missing:**
- AUGMENT = keep what you're wearing, ADD items to complete the look

### The Pattern

When user sends a **photo of what they're currently wearing**, the context is:
- These items are FIXED (they're already dressed)
- Agent should ADD to this base, not replace
- Any wardrobe pull should be for ADDITIONAL items only

### Prompt Fix Idea

```
### MODE: AUGMENT (complete a partial outfit)
Triggers:
- User sends photo of what they're wearing
- "How can I style this", "What would go with this", "Finish this look"

Behavior:
1. Identify items user is ALREADY wearing (don't replace these)
2. Suggest 2-3 directions with specific wardrobe items to ADD
3. Each suggestion = what they're wearing + additions from closet

When user gives positive feedback on a direction:
- Immediately pick specific items, don't just acknowledge
```

---

## Later: Multiple Options = Multiple Visualizations

**Observation:** When agent gives 3 "lanes" (directions), it sends all 6 items in one jumbled collage. Confusing.

**Principle to add:** "When presenting multiple outfit options, show each as a separate visualization. Don't combine items from different options into one collage."

This is a prompt principle, not a tool change. If agent understands this, it naturally calls send_message separately for each lane.

**6-star result:** 3 separate try-on visualizations, one per direction. User can visually compare.

---

## 14:00 - Agent Architecture Insights (Synthesis Session)

### Mental Model: Let Models Do What They're Good At

We converged on a clean separation:
- **Models are good at:** Reasoning, pattern recognition, synthesis, taste, judgment, creativity
- **Models need help with:** Memory across sessions, consistency over time, structured state management

Code/product fills the gaps - not because it's "cheaper" but because models literally can't persist data across sessions.

**The Pattern:**
- If it requires reasoning → model does it
- If it requires persistence → code stores it
- Some things need both (synthesis = LLM reasons, code stores and triggers)

---

## Prompt Architecture

### From Modes-Based to Principles-Based

Old approach (brittle):
- MODE: GENERATE / REFINE / SAVE / ANSWER / ACKNOWLEDGE
- "If user says X, do Y" logic
- Whack-a-mole as edge cases emerge

New approach (Claude Code style):
1. Identity - who you are
2. Tone and Style - how you communicate
3. Core Differentiation - why you exist (vs ChatGPT, vs human stylist)
4. Principles - how to help (not rules, but judgment)
5. Tools - when and how to use them
6. Domain Knowledge - garment physics, etc.

**The key insight:** Don't classify intent in prompt rules. Give model rich context (full history, synthesized preferences) and let it reason about intent.

---

## Preference Synthesis

**Problem:** Agent currently re-gathers and reasons about preferences every turn (expensive, inconsistent)

**Solution:** Periodic LLM job:
- Code triggers (after N feedback items or periodically)
- LLM reasons (extracts patterns from raw feedback)
- Code stores result
- Per-turn agent receives compact preferences

This is "synthesis" - model reasoning captured and persisted by code.

---

## Context Window Strategy

Current: 10 messages, 500-char truncation → lossy, model can't reason well
Target: 50 messages, full text → model has history to reason from

With GPT-5.2's 272K token limit and prompt caching (90% discount on repeated prefix), we have massive headroom.

---

## Model Principles (for prompt)

Two key insights:
1. **Answer with things user already has** - every suggestion names specific wardrobe items
2. **Answer with pictures > words** - visualization > collage > text description

These should be core principles in the agent prompt, not MODE-specific rules.

---

## 21:15 - Slot-Based Outfit Validator: Eval-First Approach Works

### The Problem (Solved)

AI model generates physically impossible outfits (vest + cardigan + blazer, t-shirt on t-shirt). This is the #1 trust-busting moment. Previous attempts: prompt rules (model ignores them during generation), vision/images (model can SEE bulk but doesn't understand physical consequences). Both failed.

### The Solution: Deterministic Post-Filter

Built `backend/services/outfit_validator.py` — maps each item's `sub_category` to a body "slot" and rejects outfits with >1 item per slot.

**Slots:** base_top (tee, blouse), mid_layer (sweater, cardigan, vest), outer_layer (blazer, jacket, coat), bottom, shoes, dress, accessory

**Key design decision:** Name-based fallback in `get_slot()` is critical because sub_category metadata is unreliable — vests have no mapping in `restructure_metadata.py`, so checking item name for keywords like "vest", "cardigan" catches what metadata misses.

### Eval Results

- **General outfits (3 users × ~12 each):** 2% filter rate — not restrictive at all
- **Dana's vest stress test (complete-the-look × 4 occasions):** 58% filter rate — AI kept pairing vest + sweater (same sub_category) and vest + cardigan (both mid_layers)
- The 5 passing vest outfits were genuinely good layered looks (vest + button-up + blazer, vest + tee + jeans)

### The Meta-Learning: Eval Before Deploy

Instead of wiring to production immediately, built an eval script that generates outfits and shows side-by-side what would PASS vs get FILTERED. This validated the filter doesn't kill outfit quality before touching production. The concern about being "overly restrictive" was unfounded for general outfits but very real for the vest case — seeing the 58% rate and confirming the filtered outfits were actually bad gave confidence to deploy.

**Pattern:** For any filter/constraint that could reduce output quality, run a side-by-side eval first. The cost is ~5 min of API calls. The benefit is confidence in the decision.
