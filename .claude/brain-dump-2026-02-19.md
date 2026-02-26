# Brain Dump - 2026-02-19

## 13:30 - SMS vs Web Divergence Audit

SMS and web are complementary access points but have significant feature gaps where SMS is missing write capabilities that web has.

### The Pattern
SMS agent has READ access to most data but missing WRITE tools that web has. This creates a broken feedback loop — users can view outfits/items via SMS but can't close the loop (mark worn, decide on purchases, etc.).

### Divergence Table

| Feature | SMS | Web | Priority |
|---------|-----|-----|----------|
| Viz persistence | ❌ Orphaned (FIXED today) | ✅ Saved | FIXED |
| Mark outfit worn | ❌ No tool | ✅ Full API | HIGH |
| Worn photo upload | ❌ No | ✅ Yes | HIGH |
| Consider-buying: decide (bought/passed) | ❌ No tool | ✅ Yes | HIGH |
| Consider-buying: delete | ❌ No tool | ✅ Yes | MEDIUM |
| Consider-buying: update | ❌ No tool | ✅ Yes | MEDIUM |
| Feedback/dislike | ✅ Same | ✅ Same | ALIGNED |
| Outfit save structure | ✅ Same manager | ✅ Same manager | ALIGNED |
| Context (weather/temp) | Agent infers | Explicit params | LOW |
| Image enrichment on retrieval | ❌ No | ✅ Yes | LOW |

### Root Cause
SMS agent tools were built for the "styling conversation" use case (get items, suggest outfits, save). The lifecycle management tools (mark worn, decide on purchases, manage considering list) were never added because they weren't part of the initial SMS flow. But users naturally want to do these things via text.

### Key Architectural Insight
SMS and web should be complementary access points to the SAME capabilities. The eigenquestion: "Can a user complete their entire style workflow from SMS alone?" Right now: no. They have to go to the dashboard for worn tracking and purchase decisions.

### What to Build Next
1. `mark_worn` tool — calls `SavedOutfitsManager.mark_outfit_worn()`. Simple add.
2. `decide_considering_item` tool — calls `ConsiderBuyingManager.decide_item()`. Enables the buy-smarter feedback loop from SMS.
3. `delete_considering_item` tool — calls `ConsiderBuyingManager.delete_item()`. List hygiene.

### Code Paths
- Web worn tracking: `api/outfits.py:647` (mark-worn), `:699` (worn-photo)
- Web consider CRUD: `api/consider_buying.py:86-250+`
- SMS agent tools: `agent/tools.py` (definitions), `agent/agent.py` (handlers)
- Manager methods already exist — just need tool definitions + handlers in agent

---

## 03:05 - LLM Cost Architecture: Where Data Lives Matters More Than How Much

### The Pattern

When building agentic LLM apps, there's a non-obvious cost architecture decision: WHERE you place context data (system prompt vs tool results) matters as much as HOW MUCH data you send.

- **System prompt** = static prefix → OpenAI automatically caches identical prefixes ≥1024 tokens at 90% discount ($0.175/1M vs $1.75/1M)
- **Tool results** = dynamic content in message history → always full price, never cached

### What We Did

Style Inspo's agent was making 2+ LLM calls per message:
1. Call 1: Agent calls get_profile + get_items + get_feedback_patterns (context gathering)
2. Call 2: Agent uses the results to reason and respond

We moved the same data (user profile, wardrobe items, feedback patterns) from tool results into the system prompt via a `preload_user_context()` function. The agent now gets the data "for free" as part of the cached system prompt prefix.

### The Compounding Effect

This isn't just "1 fewer API call." Three things compound:

1. **Fewer total tokens processed** — The eliminated call would have re-sent the entire system prompt + tools (~5.7k tokens) PLUS the wardrobe JSON tool results (~8-10k tokens). Those tokens simply don't exist anymore.

2. **Data moved from uncacheable → cacheable** — Before, wardrobe data arrived as tool results (dynamic, full price every call). After, the same data is in the system prompt (static prefix, 90% cached).

3. **Higher cache ratio on remaining calls** — Shopping turns went from ~45% cached to 98% cached because the wardrobe data is now part of the identical prefix.

### Measured Results

| Scenario | Before | After | Change |
|----------|--------|-------|--------|
| Shopping (text-only) | 2 LLM calls, 18.5s, ~$0.033 | 1 call, 7.9s, ~$0.006 | -57% latency, -82% cost |
| Occasion (outfit) | 4 LLM calls, 19.6s, ~$0.048 | 3 calls, 16.4s, ~$0.026 | -16% latency, -46% cost |

### Why Tool Results Are Uncacheable

OpenAI's prompt caching is **strict prefix matching from the start of the messages array**. It's NOT "cache any repeated content anywhere" — it's "if the first N tokens are identical to a previous request, those N tokens are cached."

The cache matches from position 1 forward. As soon as something differs, caching stops. Tool results are always at the END of the growing message list — they're new content appended after the cached prefix.

After preloading into system prompt: wardrobe data is part of the fixed prefix — identical across ALL requests for this user. Every call gets 98% cache hit.

### Implementation Details

- `preload_user_context(user_id)` in `api/sms.py` — fetches profile, wardrobe (compact: name/category/colors/style only), and filtered feedback patterns
- Injected into system prompt with explicit instruction: "Do NOT call get_profile, get_items, or get_feedback_patterns — this data is already here."
- Added `cached_tokens` logging to `agent.py` to verify caching is working
- Token usage (input/output/cached) now tracked per agent run and persisted to S3 via agent_logger
