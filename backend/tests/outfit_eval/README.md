# Outfit Generation Evaluation Harness

Systematic A/B testing framework for comparing AI models on outfit generation quality, latency, and cost.

## Overview

This evaluation harness allows you to:
- Test multiple AI models (OpenAI, Gemini, Claude) with the same prompts
- Generate outfits across different scenarios (occasions, complete-my-look, etc.)
- Review and rate outfits visually in an HTML interface
- Analyze results to pick the best model

## Setup

### 1. Install Dependencies

```bash
cd /Users/peichin/Projects/style-inspo-api/backend

# Activate virtual environment (if not already)
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure API Keys

Add API keys to your `.env` file:

```bash
# Required (already configured)
OPENAI_API_KEY=sk-...

# For Gemini testing
GOOGLE_API_KEY=AIza...

# For Claude testing
ANTHROPIC_API_KEY=sk-ant-...
```

Get API keys:
- Google: https://aistudio.google.com/app/apikey
- Anthropic: https://console.anthropic.com/

## Usage

### Step 1: Run Evaluation

Generate 200 outfits across 4 models:

```bash
cd tests/outfit_eval

python scripts/run_eval.py \
    --scenarios fixtures/test_scenarios.json \
    --models fixtures/model_configs.yaml \
    --iterations 10
```

**Parameters:**
- `--scenarios`: Test scenarios (5 scenarios: wedding, work meeting, casual, date night, complete-my-look)
- `--models`: Models to test (4 models: gpt-4o, gemini-2.0-flash, claude-3.5-sonnet, gpt-4o-mini)
- `--iterations`: Outfits per scenario/model combination (default: 10)

**Output:**
- Creates `results/eval_TIMESTAMP/raw_results.json`
- Takes ~30-60 minutes depending on API speed

### Step 2: Generate Review Page

Create interactive HTML for rating outfits:

```bash
python scripts/generate_review.py --results results/eval_20251123_143022/
```

**Output:**
- Creates `results/eval_TIMESTAMP/review.html`
- Open in browser to review outfits

### Step 3: Rate Outfits

1. Open `review.html` in your browser
2. For each outfit:
   - Click stars to rate (1-5)
   - Add notes about why it's good/bad
3. Click "💾 Export Ratings" button
4. Save as `ratings.json` in the results directory

### Step 4: Analyze Results

Generate summary statistics:

```bash
python scripts/analyze_results.py --ratings results/eval_20251123_143022/ratings.json
```

**Output:**
```
Model Performance Comparison
================================================================================

Model ID                       Avg Rating   Count    Distribution
------------------------------ ------------ -------- --------------------
gemini_2_flash                 4.30/5.0     50       1★:0 2★:2 3★:8 4★:20 5★:20
gpt4o_baseline                 4.10/5.0     50       1★:1 2★:3 3★:10 4★:22 5★:14
claude_35_sonnet               4.20/5.0     50       1★:0 2★:2 3★:12 4★:18 5★:18
gpt4o_mini                     3.70/5.0     50       1★:2 2★:8 3★:15 4★:20 5★:5

🏆 Best Performing Model: gemini_2_flash
```

## File Structure

```
outfit_eval/
├── README.md                   # This file
├── fixtures/
│   ├── test_scenarios.json     # 5 test scenarios
│   └── model_configs.yaml      # 4 model configurations
├── scripts/
│   ├── run_eval.py            # Main evaluation runner
│   ├── generate_review.py     # HTML review generator
│   └── analyze_results.py     # Results analyzer
├── results/
│   └── eval_TIMESTAMP/
│       ├── raw_results.json   # All evaluation results
│       ├── review.html        # Interactive review page
│       └── ratings.json       # Your ratings (exported)
└── templates/                  # (Reserved for future templates)
```

## Test Scenarios

Current scenarios (defined in `fixtures/test_scenarios.json`):

1. **Occasion: Outdoor Wedding** (Peichin) - Elegant occasion-based generation
2. **Occasion: Important Work Meeting** (Heather) - Professional outfit generation
3. **Complete My Look: Brown Boots** (Peichin) - Anchor piece styling
4. **Casual Weekend Outing** (Heather) - Everyday casual outfit
5. **Date Night Dinner** (Peichin) - Dressy occasion outfit

To add more scenarios, edit `test_scenarios.json` following the existing format.

## Models Tested

Current models (defined in `fixtures/model_configs.yaml`):

- **gpt-4o** - OpenAI (baseline, current production)
- **gemini-2.0-flash-exp** - Google (fast, cheap)
- **claude-3-5-sonnet-20241022** - Anthropic (reasoning quality)
- **gpt-4o-mini** - OpenAI (cost control)

To add more models, edit `model_configs.yaml`.

## Metrics Tracked

For each outfit generated:
- ⭐ **Quality Rating** (1-5 stars, manual)
- ⏱️ **Latency** (seconds, automatic)
- 💰 **Cost** (USD, automatic)
- ✅ **Structural Validation** (no two shoes/pants, automatic)
- 📝 **Notes** (free text feedback, manual)

## Tips

### Running Smaller Evals

For quick testing:
```bash
python scripts/run_eval.py --iterations 3  # Only 3 iterations (60 total outfits)
```

### Testing Single Model

Edit `model_configs.yaml` and comment out models you don't want to test.

### Adding New Test Cases

1. Edit `fixtures/test_scenarios.json`
2. Add new scenario following existing format
3. Run eval with updated scenarios

### Recurring Evaluations

Run this eval regularly (e.g., monthly) to:
- Test new models as they're released
- Track quality trends over time
- Validate prompt improvements
- Compare cost/performance tradeoffs

## Troubleshooting

**Error: "No wardrobe found for user"**
- User must have uploaded items in production
- Check user_id is correct in test_scenarios.json

**Error: "API key not found"**
- Add missing API key to `.env` file
- Restart terminal to reload environment

**HTML page doesn't show images**
- Images are loaded from production S3 URLs
- Check network connection
- Verify image_path URLs in raw_results.json

## Future Enhancements

Potential additions:
- [ ] Cost tracking and budget alerts
- [ ] Automated quality scoring (Claude-as-judge)
- [ ] Trend analysis over multiple eval runs
- [ ] Integration with production monitoring
- [ ] Prompt variation testing

---

**Created**: Nov 2025
**Last Updated**: Nov 2025
