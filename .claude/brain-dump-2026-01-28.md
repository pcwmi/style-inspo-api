# Brain Dump - January 28, 2026

## Topic: Agent-Native Architecture Learnings

### The Big Insight: "Primitives Are Just CRUD"

Initially felt underwhelmed when realizing primitives = CRUD operations. But that's the insight:

**Traditional software thinking:**
- Smart tools with bundled business logic
- `generate_weekly_outfit_plan()` that hardcodes "fetch calendar, loop days, generate per day"
- To change behavior → refactor code

**Agent-native thinking:**
- Dumb CRUD tools: `get_calendar()`, `get_items()`, `save_outfit()`
- Agent reasoning composes them with judgment
- To change behavior → edit the prompt

The magic isn't in the primitives. It's in **where intelligence lives**.

### The Eigenquestion for Primitive Design

> "To change behavior, do I edit the prompt or refactor code?"

If the answer is "refactor code" → primitive is too coarse, has bundled logic.

### No Framework Needed

For Style Inspo's "single skilled worker with tools" problem shape:

| Framework | Purpose | Why Skip |
|-----------|---------|----------|
| LangGraph | Multi-step workflows with branching | Overkill |
| CrewAI | Multiple agents collaborating | Don't need agent coordination |
| AutoGen | Agents conversing with each other | Same |
| Claude Agent SDK | Single agent with tools | Could use, but it's ~20 lines of code anyway |

The agent loop is trivial. Don't add dependencies for what you can write in 20 lines.

### Where Differentiation Lives

| Layer | Investment Level | Why |
|-------|-----------------|-----|
| Agent loop | Minimal (commoditized) | Everyone has the same while loop |
| Primitives | Medium | Design thoughtfully, but they're CRUD |
| System prompt | **High** | This is where taste lives |
| Domain knowledge | **Highest** | Styling rules, garment physics, feedback patterns |

### Key Design Decision: No `generate_outfit` Primitive

Outfit generation is **agent reasoning**, not a tool.

- Tools provide DATA: wardrobe items, calendar events, weather, feedback patterns
- Agent provides JUDGMENT: which items work together, why, styling notes

This keeps styling intelligence in the prompt (editable) not in code (requires refactor).

### Implementation Strategy: Strangler Fig

Build new `/primitives/*` endpoints alongside existing `/api/*`:
- Frontend keeps using `/api/*` (no breakage)
- Agent uses new `/primitives/*`
- Same underlying storage (S3, JSON)
- Eventually frontend can migrate (optional)

### Primitive Count: 32 Total

After adding worn tracking from recent commit:
- Wardrobe: 6 primitives
- Profile: 3 primitives
- Outfits: 8 primitives (including new worn tracking)
- Feedback: 3 primitives
- Consider-Buy: 8 primitives
- Context: 3 primitives (calendar, weather, URL extract)
- Viz/Jobs: 2 primitives
- Comms: 1 primitive (send_notification)

### Next Steps

1. Phase 1: Create read-only primitives (`/primitives/items/{user_id}`)
2. Phase 2: Add write primitives
3. Phase 3: Simple agent test ("What tops do I have?")
4. Phase 4: Styling agent with full system prompt
5. Phase 5: Multi-surface (SMS/email) - requires Twilio

### Quote to Remember

> "The framework doesn't help with what matters. It just wraps the loop."

The investment should go into domain knowledge and system prompt design, not framework selection.

---

## Visual Design Drives Engagement (Not Just Aesthetics)

### The Insight

Visual polish on the homepage isn't just "making it pretty" - it's a **re-engagement trigger**.

Alexi's feedback today:
> "Yay homepage! It's what inspired me to look at the model system today!"

The editorial aesthetic (edge-to-edge imagery, serif typography, larger thumbnails) caused a lapsed user to:
1. Return to the app
2. Explore features she hadn't tried
3. Get excited about model visualization

### The Pattern

```
Visual quality upgrade
    → Creates "this feels premium" signal
        → User invests attention
            → Explores deeper features
                → Potential for habit formation (if features deliver)
```

### Caveat: Visual Polish Can't Fix Broken Core

Same session, Alexi also tried Complete My Look:
> "lobbed a few easy requests at it and didn't have the results I was looking for"
> "layered two raglans on top of each other"

Visual features create expectations. If core features don't deliver, you get a "bait and switch" experience.

**The order matters:**
1. Fix core functionality FIRST
2. THEN polish visuals to drive engagement

Or risk: beautiful visuals → user excitement → feature failure → amplified disappointment

### Key Quote

> "Like when you see a perfectly styled mannequin in a store and just want to buy the whole outfit"

This is the emotional state we want to create. Model visualization achieves it. The question is: can the rest of the product live up to that promise?
