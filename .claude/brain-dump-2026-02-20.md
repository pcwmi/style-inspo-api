# Brain Dump - 2026-02-20

## 00:15 - Agent Feedback Signal Strength Hierarchy

Signal strength hierarchy for agent feedback:

1. **Explicit dislikes with freeform reasons** (strongest — ground truth like "don't stack sweaters")
2. **Explicit saves with reasons** (strong — "love basics + elevated accessories")
3. **Save rate from daily digest** (useful hard data — "25% save rate = selective user")
4. **GPT pattern guess from not-saved outfits** (directional — pre-computed, compact)

Agent should weight these accordingly. Silent feedback is the weakest signal — keep it compact (summary + save rate) so it doesn't dilute the explicit signals.
