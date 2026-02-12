# Brain Dump - 2026-02-10

## 14:30 - Stateful SMS & Two-Phase Visualization

### Stateful SMS Changes Everything
Before: Each SMS was a fresh conversation. User sends "save this" and agent has no idea what "this" means.
After: Redis-backed state (24hr TTL) preserves last outfit + recent messages. Now supports:
- "❤️" → saves the outfit they just saw
- "too casual" → captures feedback + generates new outfit
- "swap the shoes" → modifies only that piece
- "try again" → avoids repeating

This unlocks the 3 blocked use cases from the roadmap. The architecture: ConversationStateManager per phone number, StatefulSMSOutput captures what's sent, agent receives [CONTEXT] prefix.

### Two-Phase Delivery for Visualization
Problem: Visualization takes 60s, too slow for SMS response.
Solution: Send collage first (21s), spawn background thread for visualization, send follow-up MMS when ready.

This "immediate value + delightful surprise" pattern is reusable. User gets fast feedback, then bonus content arrives. No regression on speed.

### Silent Fail for Non-Critical Features
Visualization is enhancement, not core. If Runway fails, user already has collage. Log the error, don't bother user with "couldn't generate styled look". This keeps error handling proportional to feature criticality.

### Method Design for Different Flows
- `visualize_outfit(outfit_id)` - for saved outfits (has item metadata)
- `visualize_from_images(images)` - for SMS (just URLs, no outfit_id)

Same capability, different entry points. Don't force one flow to fit another's interface.
