# Brain Dump - 2026-01-29

## 07:45 - SMS/WhatsApp Agent Architecture Session

### What We Built
- Agent-first primitives for SMS: fuzzy item matching + grid collage generation
- WhatsApp flow: user texts → agent generates outfit names → fuzzy match to wardrobe → collage → MMS

### Learnings

**Pei-Chin's takeaways:**
- SMS verification regulations are tight - WhatsApp sandbox was the right call
- Didn't discuss SMS UX flow enough before implementation (how images should display)
- Should have used plan mode more to align on design before coding

**Claude's takeaways:**
1. **NEVER bulk delete without explicit confirmation** - I deleted all 35 saved outfits assuming empty `items` arrays meant broken data. The actual structure used `saved[].outfit_data.items` not `outfits[].items`. S3 versioning saved us.

2. **Verify data structure before operations** - Should have checked one item's full structure before writing deletion logic. The manager was looking at wrong keys.

3. **Fuzzy matching needs domain-specific stopwords** - Generic words like "button-up" caused false matches ("white ruffled button-up shirt" → "ivory crochet button-up cardigan"). Added clothing-specific stopwords.

4. **Test with real E2E before claiming done** - Local unit tests passed but production revealed matching bugs and UX issues (brackets in text, wrong timing estimate).

### Fixes Made
- Tighter fuzzy matching (50% overlap, more stopwords)
- Strip brackets from agent responses
- Updated timing: "about 30 seconds" (actual: ~21s)

### Result
Working WhatsApp flow! 5-image collage delivered in ~21 seconds. Minor matching bugs to continue tuning.

### Open Questions
- Should we persist generated (not saved) outfits for analytics/recent history?
- Collage layout: 3x2 grid leaves empty cell for 5 items - is that okay?
