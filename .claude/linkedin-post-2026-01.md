# LinkedIn Post - January 2026 Monthly Update

**Status:** PUBLISHED
**Date:** January 19, 2026

---

Building an AI-powered style assistant has been my playground lately. This month I hit walls that taught me more than the wins....

=== Longer Autonomous Horizons ===
Opus 4.5 is so good that the rate-limiting factor is how I use it, not the model itself. The pattern that unlocked longer horizon of Claude autonomy: MCP integrations (Playwright, Vercel, Railway) + clear verification criteria + session-specific permissions + permission to iterate. I use the Ralph Loop concept: Promise → Verify → Iterate. Instead of "try to fix this bug," I give Claude a promise: "go through the user flow of XYZ E2E without errors" It can fail, iterate, and only return when verification passes.

The a-ha moment was when I asked Claude how I could use it better. It says... "If you specify verification criteria and let me know it's ok to iterate, I won't feel like I'm failing you." Maybe anthropomorphizing, but the insight is real. Permission to fail unlocks autonomy.

The other shift: traditional UI feels less essential when the agent has context. Instead of opening PostHog dashboards, I ask Claude: "Who used the product yesterday, what did they do, and what was surprising?" My ability to get insights feels a lot more fluid and the subsequent 'stable' dashboard also feels more on demand.

=== Hitting the Walls ===
The AI kept suggesting "tuck the ruffled shirt into the leather skirt." Anyone who's worn ruffles knows.. it creates bulk at the waistband and not a flattering look.

The surprising part: AI CAN reason about this. When I asked "which is more flattering?", it correctly explained ruffles create bulk when tucked. It knows. But during outfit generation, it doesn't apply that reasoning. I ran an A/B test adding "ask yourself if anything would bunch up." 100% still said tuck.
What's obvious to humans isn't obvious to AI. We have embodied intuition about fabric; AI has pattern-matching. It can think about physical effects when pushed, but doesn't naturally attend to them. The causal effect in the physical world isn't 'top of the mind' for AI, and I'm excited to see if the world model changes that....

=== Agent-First Architecture ===
Even I, the creator, only use the app a few times a week, and a few users told me the morning is always a rush for them.. a user said, "What if it sent outfit suggestions in the evening for tomorrow?" Later I read Dan Shipper's agent-native architecture and something clicked.

The reframe: traditional software is UI → Logic → Data. Agent-native flips it: the agent IS the core, surfaces are access points. The app's value isn't the website, but the capability. We can remove the rigidity of the UI layer and the capability can meet users where they are (SMS, email, web, calendar trigger etc). I'm excited about designing the atomic primitives and seeing what emergent 'features' it'll enable.

=== Ask ===
Building with agent-first patterns? Let's compare notes on primitive design and extending autonomy horizons.

---

## Cut content (saved for future posts)

- Virtual try-on learning: "relatable model" > personal photo ("hotter version of me" vs "distant relative")
- Accidental feature: AI suggesting items users don't own, users loved it
- Chain-of-thought prompting: "4-star prompts describe outputs, 5-star prompts guide reasoning"
- User research reframe: ethnography vs optimization
