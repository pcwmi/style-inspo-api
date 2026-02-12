# Brain Dump - 2026-02-11

## 21:25 - Visualization A/B Test: Pre-Composite vs Smart Selection

Visualization A/B test results: Pre-composite (flat-lay collage of ALL items) vs Smart Selection (first 2 + last 1 images).

**Key findings:**
1. Pre-composite is working SLIGHTLY BETTER than baseline for multi-item outfits (5-7 items)
2. Runway CAN parse flat-lay collages and translate them to worn outfits
3. Styling instructions ARE being sent to Runway but it's not following them reliably (e.g., "sweater draped over shoulders" gets ignored - this is a fundamental model limitation, not a code bug)

**Next steps:**
- Consider adopting pre-composite as default for outfits with 4+ items
- Explore more explicit prompt phrasing for styling instructions
- Accept that Runway is better at "outfit vibe/silhouette" than "exact styling technique"

**The success equation:** Visualization depends on (1) including all items (pre-composite solves this) and (2) following style instructions (still a challenge). If we can nail both + keep it fast, that's the best experience. Text "How to wear it" is the fallback.
