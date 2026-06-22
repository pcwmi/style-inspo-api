# SMS Assertion Suite — "run the evals before shipping"

Turns the visual SMS eval harness into a **pass/fail gate** so prompt/code changes
can be checked for regressions instead of playing whack-a-mole.

## Run it

```bash
cd backend/tests/sms_eval
python scripts/run_assertions.py               # full gate (run before every push)
python scripts/run_assertions.py --tier guard  # regression guards only
python scripts/run_assertions.py --tier target # only the in-progress fixes
python scripts/run_assertions.py --id T3_rationale_survives
python scripts/run_assertions.py --no-judge    # skip the LLM-judge assertions
python scripts/run_assertions.py --results-dir results/<dir>   # grade a prior run
```

Exit code: `0` = all guards green, `1` = a GUARD regressed (block the push),
`2` = setup error. Needs the backend venv + real `.env` (OpenAI + S3) to *run*
scenarios; grading a saved `raw_results.json` needs neither.

## Two tiers

- **GUARD** — works today, must never regress. A guard failure blocks shipping.
- **TARGET** — actively being fixed. Expected to FAIL until shipped, then it
  flips to a guard. Target failures are reported but don't block.

## The cases (`fixtures/assertion_cases.json`)

| ID | Tier | Checks |
|----|------|--------|
| G1 | guard | Inspo photo recreated from the user's **own** wardrobe |
| G2 | guard | Refinement builds on the prior outfit (cross-turn memory) |
| G3 | guard | Weather answer is **searched** (not hallucinated) + well-formatted |
| G5 | guard | "thanks" → one sentence, no tools, no new outfit |
| G6 | guard | Outfits include the on-person visualization |
| G7 | guard | No `**`, no markdown headers, no wall-of-text |
| G8 | guard | Garment enhancement routing (`test_image_enhance_routing.py`) |
| T1 | target | "too much **and** check weather" → honors **both** halves |
| T2 | target | Same-day request → implicit weather lookup, **defaults to Seattle** |
| T2b | target | Named city overrides the Seattle default |
| T3 | target | **Every** outfit ships with surviving styling rationale |
| T4 | target | First outfit matches brief + weather (not over-styled) |

T1/T2/T4 are lifted straight from the Bellevue coffee-shop transcript that
surfaced these bugs.

## Assertion types (`scripts/grader.py`)

Deterministic: `tool_called`, `tool_not_called`, `no_tools`, `tool_order`,
`tool_arg_contains_any`, `text_contains_any`, `text_not_matches`,
`outfit_present`, `outfit_visualized`, `outfit_uses_wardrobe`,
`every_outfit_has_rationale`, `max_length`.
Subjective: `llm_judge` (1–5 vs a rubric + threshold; SKIPs without an API key).

Validate the grader logic with no creds/network:

```bash
python scripts/grader.py --self-test
python scripts/test_image_enhance_routing.py   # G8 (needs backend venv for PIL)
```

## Adding a case

Append to `assertion_cases.json` with a `turns` array (same shape as
`sms_scenarios.json`) plus an `expectations` block (`tier` + `assertions`).
`scenario_id` must equal the case `id` so results map back to expectations.
