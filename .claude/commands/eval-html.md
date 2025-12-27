---
description: Generate interactive HTML review from outfit eval results
---

Generate an interactive HTML review page from outfit evaluation results with star ratings and comment capture.

Run the universal HTML generator that:
- Auto-detects latest eval directory (or uses specified directory if provided as parameter)
- Auto-detects A/B test (multiple models) vs single model evals
- Generates side-by-side comparison for A/B tests
- Displays 200x200px images with hover zoom
- Includes star ratings and comment capture (localStorage persistence)
- Shows model performance stats (latency, cost)

```bash
cd backend && STORAGE_TYPE=s3 ./venv/bin/python3 tests/outfit_eval/scripts/generate_eval_html.py
```
