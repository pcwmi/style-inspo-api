# Brain Dump - 2026-01-19

## 14:30 - User Research: Dimple Call & Alexi Prep

### Dimple Call (Jan 19)
- "A bit disappointed" if Style Inspo disappeared (not "very disappointed" = not PMF)
- She's a target customer: uses Stitch Fix/Armoire, always cares about appearance, RTO context
- Friction: mornings too rushed, website feels like "big deal" vs quick check
- Suggestions: evening notifications 8:30pm, text/chat interface, Pinterest integration
- Reframe: this is a playground, not a business. Joy comes from understanding how style fits into people's lives

### Research Approach Shift
- Not doing "user research for optimization" - doing "ethnography for curiosity"
- Better questions: "tell me about getting dressed in your life" not "do you like my product"
- The 50% friend catch-up time is intentional and valuable

### Alexi Data (for upcoming call)
- Dec 19: Uploaded ~40 items, saved 2 outfits (initial success)
- Jan 5-6: Came back, uploaded 70+ MORE items (big investment)
- Jan 1-7: Generated 6 outfits, saved NONE of them
- Jan 7: Churned

Key question for Alexi: "You uploaded 70+ photos in January - what were you hoping for? And when you generated new outfits, what was different from December?"

### Questions for Alexi
1. Tell me about getting dressed in your life, what does that mean to you
2. Tell me the last time you didn't like your outfit or felt like you were in a rut
3. Tell me the last time you used StyleInspo, what prompted you to do that (follow the breadcrumb)
4. You came back in January and uploaded a ton more - what were you hoping would happen?

### Frame Clarification
- This is NOT a business - it's a playground
- Joy: learning AI, creative outlet, domain I enjoy
- Value of user research: understanding how style connects to people's lives, not optimizing for PMF
- If more than 1 person enjoys it, that's icing on the cake

---

## 16:00 - Agent as First-Class Citizen Architecture

Inspired by Dan Shipper's writing on agent-native software. Exploring how Style Inspo could be rebuilt with "agent as first-class citizen."

### The Core Concept

**Traditional software:** UI → Logic → Data
**Agent-native software:** Agent IS the core, surfaces are just access points

The app's value isn't the website. It's the **capability**: "Help me look good with what I have."

The website is just one way to access that capability. An agent can access it via text, email, calendar triggers, etc.

### Three Pillars (from Dan Shipper)

1. **Parity** - Agent can do everything a human user can do
2. **Granularity** - Tools are small, atomic primitives (not bundled features)
3. **Composability** - Small tools combine in ways you didn't anticipate

### Current Style Inspo Fails the Parity Test

| User Can Do | Agent Can Do |
|-------------|--------------|
| Upload a photo | ❌ No |
| View wardrobe | ❌ No |
| Generate outfits | ❌ No (no API) |
| Get styling feedback | ❌ No |

To make agent first-class: expose primitives that any agent can call.

### The Key Insight: Atomic Primitives vs Features

**Feature-level tool (too coarse):**
```
generate_weekly_outfit_plan(user_id, week_start)
```
This encodes business logic. Agent can only use it one way.

**Atomic primitives (composable):**
```
get_wardrobe_items(user_id, filters?)
get_calendar_events(user_id, date_range)
generate_outfit(items[], occasion, style_profile)
save_outfit_choice(user_id, outfit, date)
```

Now "plan my week" **emerges** from composition:
`get_calendar → for each day: generate_outfit → save_choice`

You didn't build the feature. The agent composed it.

### Style Inspo Primitives (First Pass)

**Wardrobe**
- `get_items(user_id, filters?)` → items[]
- `get_item(item_id)` → item
- `add_item(user_id, image)` → item (analyzes + stores)

**Style Profile**
- `get_profile(user_id)` → profile
- `update_profile(user_id, changes)` → profile

**Generation**
- `generate_outfit(items[], occasion, style_profile)` → ONE outfit
- (Not "generate 3 outfits" - that's a composition)

**Feedback/History**
- `save_outfit(user_id, outfit, rating)` → saved
- `get_outfit_history(user_id, filters?)` → outfits[]
- `get_rejection_patterns(user_id)` → patterns[]

**Photo Analysis**
- `analyze_clothing_photo(image)` → item_metadata
- `analyze_outfit_photo(image)` → styling_feedback

**Context (new)**
- `get_calendar_events(user_id, date_range)` → events[]
- `get_weather(location, date)` → weather

### Emergent Use Cases

| User says | Agent composes primitives |
|-----------|---------------------------|
| "Plan my week" | get_calendar → for each: generate_outfit → save |
| "What's wrong with this outfit?" | analyze_outfit_photo + get_profile → feedback |
| "I never wear this blazer" | get_outfit_history(blazer) → identify patterns → generate with it |
| "What should I buy?" | get_items + get_rejection_patterns → identify gaps |

### What IS an Agent (Mechanically)?

Not a separate service. It's:
1. **The same LLM** (GPT-4, Claude)
2. **That can ask to use tools** (function calling)
3. **In a loop** (keeps going until done)

```python
while not done:
    response = llm.chat(messages, tools=TOOLS)
    if response.tool_calls:
        for call in response.tool_calls:
            result = execute_tool(call.name, call.args)
            messages.append({"role": "tool", "content": result})
    else:
        done = True
```

The agent loop is commoditized. The differentiation is in **tool design**.

### Framework Landscape (Late 2025)

| Framework | Mental Model |
|-----------|--------------|
| LangGraph | Flowchart: explicit nodes and edges |
| CrewAI | Org chart: roles collaborate |
| AutoGen | Chat room: agents converse |
| Claude Agent SDK | Single skilled worker with tools |

For Style Inspo: don't need a framework. Problem shape is "single worker with tools."

### Where Future Is Heading

- Agent loop → commoditized (OpenAI, Anthropic provide it)
- MCP → becoming the protocol layer for tool exposure
- Differentiation → tool design and domain knowledge
- Apps become "tool providers" that any agent can consume

### Open Design Questions

1. **Granularity**: Is `generate_outfit` atomic enough? Or break into `select_anchor` + `find_complementary` + `check_fit` + `compose`?

2. **Where does intelligence live**: Should `get_rejection_patterns` be smart (LLM analyzes) or dumb (raw data)?

3. **What's missing**: What user requests can't current primitives handle?

### Homework

Going offline to think independently about:
1. What are all the things a user might ask a styling assistant?
2. What's the smallest set of primitives that could handle all of them?
3. Where does current app have "features" that are really compositions of hidden primitives?

---

## 18:30 - User Research Synthesis: Dimple + Alexi

### The Eigenquestion
> "Is the app solving a clothing problem, or a memory/organization problem?"

### Side-by-Side Comparison

| | Dimple | Alexi |
|--|--------|-------|
| **Core friction** | Access/timing (tool works, can't use it) | Output quality (tool fundamentally broken) |
| **Actual value** | "Buy smart" validation | "Reminder of items I forgot I own" |
| **Outfits worn** | Unknown | 1 out of 2 saved |
| **Trust level** | Trusts outputs | Doesn't trust (physical impossibilities) |
| **Wardrobe size** | ~40 items | 100+ items |

### Alexi's Existential Feedback

The AI doesn't understand **garment physics**:
- Ruffled shirt tucked into jeans (bulky)
- Oversized sweatshirt + tight cropped jacket (proportions wrong)
- Hoodies without undershirt
- "No skirts" constraint ignored

**Neither user actually uses it for complete outfit generation.**
- Dimple can't (timing)
- Alexi won't (broken output)

### The Philosophical Shift

**From:** "AI generates your outfit"
**To:** "AI reminds you what's possible in your closet"

Alexi already uses it this way - as a **single-item inspiration** tool, picking one piece then building the rest herself.

### Jobs-to-be-Done (Actual vs Expected)

| User | Expected Job | Actual Job |
|------|--------------|------------|
| Dimple | Plan work outfits | Validate purchases ("buy smart") |
| Alexi | Generate complete outfits | Remember forgotten items + single-item inspiration |

### For Playground Joy

The interesting questions aren't "how do I fix retention" but:
- How do people actually relate to their clothes?
- Why do they forget what they own?
- What makes a garment physically work with another?

The **garment physics problem** (layering, tucking, proportions) is intellectually interesting. That might be a fun direction to explore.

### Possible Next Experiment

Build the "complete my look" flow:
- User starts with: "I want to wear this sweater + important meeting"
- App suggests 2-3 items to complete it
- Respects garment physics
- Test with Alexi
