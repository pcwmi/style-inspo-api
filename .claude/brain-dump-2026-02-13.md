# Brain Dump - Feb 13, 2026: Platform Strategy & The Onboarding Problem

## Context
After landing page video polish (SMS demo videos with viewport-aware autoplay), stepped back to think about where to invest: SMS, web, messaging on web, native app. Reviewed all recent brain dumps and current agent/SMS architecture to ground the thinking.

## The Core Tension

SMS nails the *moment* (30 seconds getting dressed) but constrains the *magic* (visual richness). The agent has matured significantly — principle-based prompts, slot validation, multi-turn state, knows when to stop — it genuinely feels like texting a person now. But the visual payoff (Runway visualization, closet grid, saved looks) gets compressed into MMS thumbnails.

## Eigenquestion: What's the Unit of Value?

Is the value in the **conversation** (back-and-forth refinement) or the **artifact** (the visualization, the styled look)?

- If conversation → SMS wins. The 30-second moment is real, messaging is the natural container for dialogue.
- If artifact → web/app wins. You need real estate for the visual payoff. Dimple doesn't generate outfits, she *browses and bookmarks* them. That's an artifact interaction, not a conversation.

User research maps to this split:
| User | Interaction Mode | Platform Fit |
|------|-----------------|--------------|
| Mia | "60% to 40%", quick execution | SMS |
| Kate | 10-15 min planning, de-risking | Web/App |
| Dana | Taste learning ("this is very you") | Medium-agnostic |
| Rana | Relatable model, self-image gap | Visual richness (Web) |
| Dimple | Browse and bookmark saved looks | Web |

## Frame: SMS is the Front Door, Web is the Living Room

You text to get styled. The result lives somewhere you can browse, revisit, share. The conversation is ephemeral. The look is persistent.

This means: keep investing in SMS as the interaction layer (it's working), but build the artifact layer on web — saved looks, visual history, "your style over time."

## Where This Breaks: Onboarding

The "SMS front door" frame has a sequencing problem. Current flow: web signup → upload 10+ photos → set style words → *then* text. That's a web-first funnel with SMS as the payoff. The front door is actually the web.

Onboarding is inherently visual + high-friction:
- Need to see wardrobe grid to know what's uploaded
- Uploading 10 photos via MMS is miserable
- Style words need a UI (or mood board visual selection per Kate/Rana research)

**The value lives in SMS, but the setup lives on web.** Users invest in the less-magical medium before accessing the magical one. Risk: drop-off between "uploaded closet" and "actually texted."

## Three Paths Forward

### Option 1: Accept the split
Web onboarding → SMS ongoing. This is current state. Risk is conversion gap between upload and first text.

### Option 2: Collapse onboarding into SMS
"Text me 3 photos of what you're considering today." Agent works with *just those*. No full wardrobe needed. Supported by "accidental feature" insight — text placeholders for unowned items delighted Dimple, so maybe 3-5 items is enough, not 10. Wardrobe builds organically over conversations. Loses: visual grid, browsing, "oh I forgot I had that."

### Option 3: Bring messaging into web (most interesting)
Onboarding *is* the conversation, but in a chat UI on web. "Send me a photo of what you're wearing today." Same agent, richer visual canvas. User sees wardrobe building in real-time. When hooked, they get the phone number for the morning moment.

This collapses the tension — front door and living room are the same place. The chat *is* the app. Closer to what Dana already trained ChatGPT to do, just with wardrobe layer underneath.

**Open question:** Does moving conversation to web lose the "30 seconds getting dressed" moment? Or can both coexist — web chat for setup/planning, SMS for the morning moment?

## What's Working in Agent (Status Check)

Recent wins worth preserving regardless of platform decision:
- System prompt matured from formula-based to principle-based ("Unexpected Perfect" + know when to stop)
- Slot-based outfit validator catches physics violations (2% general filter rate, 58% for vests)
- Multi-turn conversation state (Redis, 24h TTL, 50 messages, outfit history for "go back")
- "Don't act on acknowledgments" fix changed the feel completely
- Two-phase delivery: collage first (21s), visualization follow-up
- 32 CRUD primitives, no framework overhead, ~50 line agent loop

## Unresolved

1. Is the conversation or the artifact the thing people come back for?
2. Can web chat UI deliver the same "effortless" feel as texting?
3. Is there a 4th option where SMS *is* the onboarding? ("Text STYLE to get started" → guided photo upload via MMS → immediate first outfit)
4. Visual is key — but visual *what*? The Runway visualization? The collage? The closet grid? The mood board?
5. How much wardrobe do you actually need for value? (3 items? 5? 10?)
