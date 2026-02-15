# Brain Dump - 2026-02-14

## 16:00 - Session Recap: Flux 2 Pro, Viz Persistence Bug, Process Improvements

### Shipped: Flux 2 Pro as Default Visualization Provider
Switched production visualization from Runway to Flux 2 Pro across SMS + web. Better garment fidelity (items actually appear), half the cost ($0.03 vs $0.08/img), ~20-26s latency via fal.ai edit endpoint. Changed defaults in visualization_manager.py, factory.py, visualization_worker.py. Added FAL_KEY to Railway. Hit a missing dependency bug on deploy — fal-client was pip-installed locally during eval session but never added to requirements.txt. Fixed and deployed.

### Bug Fix: Visualization Not Persisting to Saved Outfits
Found that viz images were generated during outfit generation (stored in Redis, 1hr TTL) but never written to the S3 outfit record on save. When users visited "Ready to Wear," frontend saw `visualization_pending: true` + no URL → re-triggered 5 viz requests every page load. Root cause: two independent systems (Redis by viz_key vs S3 by outfit_id) that never talked to each other. The method `update_outfit_visualization()` already existed but was never called.

Fix (3 changes in backend/api/outfits.py):
1. On save: check Redis for completed viz URL, persist to S3 immediately
2. Background thread: after viz completes, also persist to any matching saved outfit (handles race condition)
3. Stale outfits (>5 min old, no URL): return pending=false to stop re-triggering for existing outfits

### Process Improvements
1. **Pre-commit hook created** (.git/hooks/pre-commit) — runs `from main import app` on every commit touching backend Python files. Would have caught the missing fal-client mechanically.
2. **CLAUDE.md rewritten** — 10 narrative post-mortem lessons replaced with 6 named GATE blocks + workflow rules. Key insight: lessons written as "here's what went wrong" are read once and forgotten. Gates written as "do X before Y" are actionable during execution.
3. **Auto memory updated** (MEMORY.md) — pre-deploy checklist now in system prompt every session. Includes: import smoke test, check requirements.txt for new deps, verify env vars in Railway.

### Alexi Re-engagement
Ran eval: 9/10 outfits passed with GPT-5.2 + validator. Fixed one mislabeled item (cardigan → button-up shirt). Sent Alexi a message asking about her actual trigger moment for needing styling help. Also identified Dimple as strongest re-engagement candidate — she literally asked for text-based access and we built SMS.

---

## 18:10 - Agent Browse Behavior + Search Tool Idea

**Observation:** When I sent the Frame sale page and asked "what should I buy", the agent called `browse_url`, got 40 products, then gave *strategic* advice ("you're missing high-function foundations") instead of picking specific products. When I narrowed to "pick 1, date night, size M", it immediately pulled a specific product with a direct link. **Good stylist pattern: diagnose before prescribing.** The data was in context the whole time — it chose when to be strategic vs specific.

**Feature idea: Add a product search tool.** Currently the agent has `browse_url` (user provides a URL → extract products) but no `search_products` (agent searches retailers on its own). For the no-closet friend use case, the agent gives great advice ("get a black suede Chelsea boot from G.H. Bass") but can't link to actual products. A search tool would close this gap.

---

## 18:48 - Shipped: Agent-Powered Web Outfits (One Brain, Two Surfaces)

Agent-powered web outfits shipped and made default. The quality difference is noticeable — agent reads feedback patterns and saved outfits, so it actually learns from user reactions. Key win: one brain, two surfaces (web + SMS) now share the same agent framework. The "Why this outfit" reasoning panel shows users the agent's thought process. This validates the agent-native architecture thesis: intelligence lives in the prompt, primitives are just CRUD, and the same agent loop serves any surface. First time web outfits feel feedback-aware.
