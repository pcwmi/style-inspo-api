---
description: Run outfit generation evaluation with named presets
---

Run outfit generation evaluation using predefined presets or custom parameters.

**Common Usage (with presets):**

Run evaluations using named presets from `backend/tests/outfit_eval/fixtures/eval_presets.yaml`:

```bash
cd backend && source venv/bin/activate && cd tests/outfit_eval && STORAGE_TYPE=s3 python3 scripts/run_eval.py --preset baseline-vs-cot
```

**List Available Presets:**

See all available presets and their descriptions:

```bash
cd backend && source venv/bin/activate && cd tests/outfit_eval && python3 scripts/run_eval.py --list-presets
```

Or just run without arguments:

```bash
cd backend && source venv/bin/activate && cd tests/outfit_eval && python3 scripts/run_eval.py
```

**Common Presets:**

- **`quick-test`** - Single iteration, baseline only, fast feedback
- **`baseline-vs-cot`** - A/B test baseline vs chain-of-thought on GPT-4o
- **`prompt-comparison`** - All prompt variations on GPT-4o
- **`model-comparison`** - GPT-4o vs Claude vs Gemini (baseline)
- **`cot-across-models`** - Chain-of-thought across all models
- **`full-eval`** - Complete evaluation (expensive!)
- **`peichin-test`** - Baseline on all Peichin's scenarios
- **`gemini-test`** - Gemini models with multiple prompts
- **`claude-test`** - Claude models with multiple prompts
- **`work-party-deep-dive`** - Single scenario, multiple iterations

**Custom Usage (without presets):**

For custom evaluations, you can specify parameters directly:

```bash
cd backend && source venv/bin/activate && cd tests/outfit_eval && STORAGE_TYPE=s3 python3 scripts/run_eval.py \
  --models fixtures/model_configs.yaml \
  --scenarios fixtures/test_scenarios.json \
  --model-filter gpt4o \
  --iterations 1
```

**Workflow:**

1. Run eval: `/run-eval baseline-vs-cot`
2. Wait for completion (watch terminal output)
3. Generate HTML: `/eval-html`
4. Review results in browser

**Adding New Presets:**

Edit `backend/tests/outfit_eval/fixtures/eval_presets.yaml` to add custom eval configurations.
