# Brain Dump - 2026-02-04

## 14:30 - User Research Synthesis: Kate, Dana, Rana

### Three Users, Three Lenses

| User | Profile | Key Insight |
|------|---------|-------------|
| **Kate** | Gets decision paralysis getting dressed | Wants to **de-risk** before opening closet. "Spend 10-15 mins on phone, get 1-2 candidates with high confidence, then try on to confirm." |
| **Dana** | Power user, trained ChatGPT on her taste | Stickiness = **taste learning**. "My ChatGPT knows me. It'll say 'this is very you' or 'not the most Dana version of this.'" |
| **Rana** | 50s, self-image gap | "I don't want to see my own picture." Mental self-image is younger than reality. Aspiration > literal accuracy. |

---

### The Five Problems

**1. Visualization latency blocks the "see before save" flow**
- Kate wanted to see outfit on model BEFORE deciding to save
- Current: generate → save → then visualize (too late)
- Latency (~60-90s) makes "visualize first" feel heavy

**2. No taste learning loop**
- Dana's ChatGPT is sticky because it learned her taste over time
- "this is very you" / "not the most Dana version" = personalized feedback
- Current feedback is checkbox-based, not expressive

**3. Words are hard for style identity**
- Kate: "I was so mystified by the 'describe your style' words"
- Both prefer visual selection over verbal description
- Insight: Let users pick images, then give them the words

**4. Trust-building before utility**
- Kate: "I think I need a fashion therapist and getting me to share would help build trust"
- Not a literal feature request—more about emotional onboarding
- The app should feel like it "gets" you before it styles you

**5. Garment physics errors break trust**
- Dana: "but it put like 3 sweaters together"
- Long-standing problem. AI can explain why it's wrong but won't avoid it.
- Current best approach: filter/validate outputs before showing user

---

### Rana's Deeper Insight

The self-image gap:
- In her head, she's still in her 30s
- When she sees photos of herself (50s), she doesn't like it
- "I don't want to see my own picture"

**Product implication:** The "relatable model" approach isn't just preference—it's protection. For users with self-image gaps, showing a similar-but-aspirational model is *kinder* than literal accuracy.

**Question Pei-Chin is wrestling with:**
> "Is what I'm building to inspire or to actually wear it and feel good? The goal is the latter, but when someone doesn't love how they look, maybe this app can help them find the right outfit, but it's just a lot more complicated problem."

---

## Brainstorm: Solutions

### Problem 1: Visualization latency
**Current state:** 60-90s per visualization, too slow for "see before save"

**Ideas:**
- Make visualization **default/automatic** after outfit generation (background job)
- Show outfit card first, visualization appears when ready (progressive enhancement)
- Lower-fidelity fast preview? (e.g., flat lay collage in 2s, model visualization in 60s)
- Accept latency but set expectations ("Your styled look is being created...")

### Problem 2: Taste learning
**Current state:** Checkbox feedback, not expressive

**Ideas:**
- Free-text feedback field: "What did you think?"
- Agent asks clarifying questions: "Was this too dressy? Not dressy enough?"
- Pattern extraction from feedback → surfaces in future generations
- "This is very you" / "This is a stretch" confidence signals
- Fuse into agent-native: feedback becomes tool input for next generation

### Problem 3: Visual style picker
**Current state:** Three words onboarding

**Ideas:**
- Show style mood boards, user picks 3 they resonate with
- AI extracts the words from their choices
- "You picked preppy, French casual, and minimalist vibes"
- Could also use Pinterest board analysis if API available

### Problem 4: Trust-building / fashion therapist
**Current state:** Functional onboarding

**Ideas:**
- Chat-based onboarding that asks about struggles
- "What's your biggest frustration getting dressed?"
- "Are there pieces you love but never wear?"
- Build rapport before asking for wardrobe uploads
- This is emotional, not just functional

### Problem 5: Garment physics errors
**Current state:** AI generates nonsensical combos sometimes

**Ideas:**
- Post-generation validation layer (check for impossible combos)
- Filter out outfits that violate rules before showing user
- "Soft fail" - show fewer outfits if some are filtered
- Long-term: wait for better world models

---

## 15:00 - Brainstorm: Refined Approaches

### 1. Visualization as default — progressive UX, not blocking

The latency problem (~60-90s) isn't solvable yet, but the **experience** of latency is.

**Approach:**
- Show outfit card immediately (items + styling notes)
- Visualization generates in background automatically
- User can tap "see on model" → loading state → reveals when ready
- Don't block UI on visualization—it's ready when user wants it

**Key insight:** Kate wanted to see before *committing to save*, not before seeing the outfit at all.

### 2. Feedback as agent primitive

Checkbox feedback is lame. The agent-native reframe: **feedback is a primitive** the agent reads before generating.

```
get_feedback_patterns() → "Dana likes French tucking, hates chunky layers, prefers 'effortless' over 'polished'"
```

**Flow:**
- Free-text feedback field ("any thoughts?") after save/dislike
- Extract patterns from free text
- Agent consumes patterns in system prompt
- "This is very you" emerges from agent having enough context

**Tactical first step:** Even just adding a free-text field gives training data.

### 3. Visual onboarding — swap words for mood boards

**Current:** Three words (causes friction)
**Better:** Pick 3 mood boards that resonate

Then the app tells YOU: "Looks like you gravitate toward relaxed French girl with a preppy edge."

Same data, less cognitive load. User feels understood without having to articulate.

### 4. Fashion therapist — it's about sequence, not feature

Kate's insight isn't "add a chat feature." It's: **build trust before asking for wardrobe.**

| Current Flow | Therapist Flow |
|--------------|----------------|
| Upload clothes → get outfits | Tell me what frustrates you → I hear you → now let's look at your closet |

**Agent-native version:** First message could be "What's one piece you love but never wear?" — start with empathy, not utility.

### 5. Post-generation filtering — pragmatic trust protection

Can't fix the world model. CAN protect trust.

**Approach:**
- Validate outputs against rule set (no 3 sweaters, no cardigan over chunky knit)
- Filter silently—show 2 good outfits instead of 3 mediocre ones
- Log filtered outfits for debugging/learning

This buys time while waiting for model improvements.

---

## Priority Signal

| Problem | Urgency | Effort | Impact |
|---------|---------|--------|--------|
| Visual onboarding | High | Low | Reduces drop-off |
| Feedback as primitive | High | Medium | Unlocks taste learning |
| Visualization progressive UX | Medium | Medium | Kate's core ask |
| Post-gen filtering | Medium | Medium | Trust protection |
| Fashion therapist sequence | Lower | Low | Nice-to-have |

---

## 16:00 - Dana's ChatGPT Prompt: The "Fashion Therapist" Pattern

Dana shared her actual ChatGPT "founder prompt" for styling. This isn't a feature request—it's insight from someone who's been thinking about this problem deeply.

### Her System Prompt Structure

```
ROLE: Personal stylist for [name], [body type], [coloring], [vibe]

PRINCIPLES:
- Style is about feeling confident and authentic
- Honor both body and personality
- Every outfit serves a function AND feeling
- Taste + diagnosis, not recommendations

INTERACTION STYLE:
- Talk like a stylist friend (casual, direct)
- One thing at a time (don't overwhelm)
- Always explain WHY
```

### Her Session Flow

| Phase | What Happens |
|-------|--------------|
| 1. Gut Check | "How do you feel about this outfit?" (before any analysis) |
| 2. Diagnosis | Identify what's not working and WHY |
| 3. Fixes | Specific changes (tuck, swap, accessorize) |
| 4. Confidence | "Now it feels like YOU" |

### The Eigenquestion

**"Taste + diagnosis, not recommendations"**

This reframes everything:
- Current apps: "Here's an outfit" (recommendation)
- Dana's ChatGPT: "Here's why this doesn't feel right, and what to change" (diagnosis)

The value isn't generating outfits. It's **teaching taste** through feedback loops.

### Connection to Kate's "Fashion Therapist"

| Kate Said | Dana Built |
|-----------|------------|
| "I need a fashion therapist" | Diagnostic flow before recommendations |
| "Getting me to share would help build trust" | "Gut check" phase asks for feelings first |
| "I didn't know my style until ChatGPT gave me words" | System prompt defines her style for her |

They're asking for the same thing: **an entity that understands them before it styles them.**

### Agent-Native Implications

Dana's prompt structure maps to primitives:

```
get_style_profile() → "body type, coloring, vibe"
get_gut_check(outfit) → "How do you feel about this?"
diagnose_outfit(outfit, feeling) → "What's not working"
suggest_fixes(diagnosis) → "Tuck the shirt, swap the shoes"
confirm_confidence(outfit_v2) → "Now it feels like you"
```

The flow is conversational and stateful. Not "generate 3 outfits" but "let's work through this one outfit together."

### Why This Matters

Dana trained ChatGPT over months. The stickiness comes from accumulated context:
- "This is very you"
- "Not the most Dana version of this"

The app can't compete on taste until it has this loop. But it CAN compete on convenience (integrated wardrobe, visualization) once taste is established.

**Insight:** Maybe the first use case isn't "generate outfits" but "diagnose outfits I'm already wearing."

---

## 16:30 - User Segmentation: Power Users vs. Busy Moms

### Two Distinct Archetypes

| | Dana (Power User) | Mia/Heather (Busy Mom) |
|---|---|---|
| **Mode** | Iterating, refining | Quick decision, move on |
| **Time** | Has time to engage | 5 minutes or less |
| **Goal** | "Make this outfit better" | "Just tell me what to wear" |
| **Session** | Back-and-forth dialogue | One-shot answer |

### The Tension

Building for Dana (diagnostic, iterative) feels different from building for Mia (fast, decisive). But they're not incompatible.

### The Insight: Taste Learning is Infrastructure

**For busy moms:** The app *already knows* your taste → "Here's your outfit, go." No iteration needed because the app is confident.

**For power users:** The app knows your taste → Can give diagnostic feedback: "This doesn't feel like you because X."

Taste learning isn't a feature for power users. It's the *foundation* that makes quick answers trustworthy for busy moms.

### Why Dana Iterates

Dana iterates *now* because ChatGPT is still learning her. Once it knows her, she might say "just pick something" too.

The iteration phase is *training*, not the end state.

### Sequence Matters

1. **Build taste** (Dana's diagnostic mode) — conversational, back-and-forth
2. **Unlock speed** (Mia's "just tell me" mode) — one-shot, confident

You can't skip to step 2 without step 1.

Kate sits in the middle: she wants to "de-risk" (efficiency) but needs trust first. The fashion therapist phase *earns* the right to give quick answers later.

### Product Implication

The onboarding/early experience should optimize for taste learning (Dana mode). Once taste is established, the daily use case shifts to speed (Mia mode).

**Wrong:** Build for speed first, hope taste emerges
**Right:** Build for taste first, speed becomes possible
