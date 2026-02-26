# Brain Dump - 2026-02-21

## 02:50 - Visualization Body Proportions: Brand Reference Trick

Fal.ai (Flux 2 Pro) exaggerates body size when descriptors include terms like "size 10 curvy", "125 lbs", or "curvy". The model's training data associates these with much larger body types than intended.

**Fix:** Append ". Proportions similar to a J.Crew or Madewell catalog model." to the raw descriptor. This anchors body proportions to mainstream catalog models without rewriting the descriptor (preserving ethnicity, skin tone, hair).

**Tested across 4 users:**
- Heather (white, "size 10 curvy") — dramatic improvement, realistic size 10
- Anneka (Indian, "125 lbs, curvy") — dramatic improvement, realistic petite build
- Pei-Chin (East Asian, no body size terms) — subtle difference, both fine
- Dana (white, "olive skin, medium build") — skin tone preserved correctly with append approach

**Key insight:** The problem is specifically body-size language. Descriptors without size terms don't need correction. Full descriptor rewrites are dangerous — dropping "white" from Dana's descriptor shifted her skin tone darker. Append-only is safe.

**What NOT to do:** Don't rewrite descriptors with an LLM or regex. Just append the brand reference to whatever the user entered. One-line change in `flux2pro.py:148`.
