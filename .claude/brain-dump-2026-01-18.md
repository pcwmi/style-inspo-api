# Brain Dump - January 18, 2026

## PostHog MCP Setup

Set up PostHog MCP for autonomous analytics queries. Command used:
```bash
claude mcp add --transport http posthog https://mcp.posthog.com/mcp -s user
```

Added device filter guidance to CLAUDE.md to exclude my devices from queries:
```sql
AND properties.$device_id NOT IN (
  '019b5d53-2130-76a8-943e-4a5552e0758b',
  '019bc998-094e-7309-a042-2e017cc5bd45',
  '019b6b77-3a3e-7343-942f-80c2bb67787a',
  '019b5d2f-f5cc-7329-bc3a-26f01842e4bd',
  'peichin'
)
```

**Why:** I often visit other user URLs (`?user=dimple`) to view their wardrobes, which inflates their event counts.

---

## User Retention Reality Check

### The Hard Truth

| User | Real Activity | Saved | Status |
|------|--------------|-------|--------|
| **Dimple** | 8 saves on Jan 11 (her device), returns to view same outfit | 8 | Retained but passive |
| **Alexi** | Saved pre-tracking (Dec 19), returned Jan 1-7, generated 6 more, saved 0 | Pre-tracking only | **Churned** |
| **Heather** | 0 real activity (all my device) | Unknown | Never used (with tracking) |
| **Mia** | 0 tracked (used pre-PostHog Dec 26) | Unknown | Never used (with tracking) |
| **Anonymous (019bbe70)** | Completed onboarding, never generated outfit | 0 | Bounced |

### Dimple's Pattern (Signal)
- Jan 8: First visit (browsing)
- **Jan 11: Big day** - 254 events, 5 outfits generated, 8 saves
- Jan 13, 15, 16, 19: Returns but just loads the SAME `/reveal` URL repeatedly

**She bookmarked a specific outfit and keeps coming back to look at it.** Not generating new outfits.

### Alexi's Pattern (Churn Signal)
- Dec 19: Saved outfits (before PostHog tracking)
- Jan 1-7: Came back, generated 6 MORE outfits, **saved none of them**
- Jan 7: Last seen, never returned

**Had saved outfits, came back to try again, didn't find value, left.**

### Onboarding Funnel (Real Users)
- 9 saw welcome → 3 completed words (33% conversion)
- 3 completed upload (100%)
- 2 generated outfit (67%)

**Biggest drop: Welcome → Words (67% drop)** - but this might be wrong audience (friends clicking links with no intent) rather than UX problem.

---

## Growth Expert Analysis

Consulted frameworks from Elena Verna, Casey Winters, Adam Fishman.

### Key Insight
**This is not product-market fit. This is "some interest, no habit."**
- 1 user retained but passive (Dimple)
- 1 user churned after a week (Alexi)
- 0 users regularly generating outfits

### What They Would Say

**Elena Verna:** "A growth team cannot fix a product that doesn't retain. You need retention before acquisition matters."

**Casey Winters:** "Activation is the input to retention. But first, do retained users love it? Product-market fit = retention that allows for sustained growth."

**Adam Fishman:** "Activated customers > signups. Your 67% welcome drop-off is a red herring if the 33% who continue don't retain."

### The Eigenquestion
**"Is Style Inspo good enough that users would miss it if it disappeared?"**

If yes → growth tactics make sense
If no → growth tactics are premature optimization

---

## Hypothesis: Saved Outfits = Core Value?

Dimple's behavior suggests "viewing saved outfits" might be more valuable than "generating new outfits."

**Evidence for:**
- Dimple returns repeatedly to view same saved outfit URL
- Only 1 visit to `/saved` page - maybe she bookmarked the reveal directly
- She's treating generated outfits as "lookbook content" to revisit

**Evidence against:**
- Alexi had saved outfits, still churned
- Generated 6 more outfits, saved none, left

**Question for user research:** "What's the value of saved outfits to you? Do you wear them? Do you just like looking at them?"

---

## Action Items

1. **Talk to Dimple** - Why do you keep coming back to that same outfit? Did you wear it? What would make you generate new ones?

2. **Talk to Alexi** - You saved outfits in December, came back in January, generated 6 more but saved none. What was missing?

3. **Don't optimize welcome page yet** - The problem isn't awareness, it's value/retention.

4. **Don't build promo video yet** - It's a "turbo boost" (one-time tactic), not a growth loop.

---

## Growth Expert Agent Created

Created `~/.claude/agents/growth-expert.md` channeling Elena Verna, Casey Winters, Adam Fishman frameworks.

Core principles:
1. Retention before acquisition
2. PMF first - growth can't fix a product people don't want
3. Loops over funnels
4. Challenge vanity metrics
5. User research over assumptions

---

## Technical Notes

### PostHog Tracking Timeline
- **Dec 26, 2025:** PostHog added (commit b03fa85)
- Events tracked: `words_completed`, `upload_completed`, `outfit_generated`, `outfit_saved`, `outfit_disliked`

### Data Gaps
- Mia's usage: pre-PostHog (no tracking)
- Alexi's Dec 19 saves: pre-PostHog
- Heather: all "activity" was actually me viewing their wardrobe

### Rageclick on Welcome Page
One anonymous user rage-clicked "Get Started" on Jan 14. They sat on welcome for 5 minutes before clicking - likely reading time, not technical issue. Code is fine (simple `<Link>` component).
