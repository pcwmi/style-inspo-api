# Test Instructions for Cursor: Prompt Migration

## Overview

You are implementing the production prompt abstraction migration as specified in `CURSOR_SPEC_PROMPT_MIGRATION.md`.

**Your implementation MUST pass all tests in this file before being merged.**

---

## Running the Tests

### Run All Prompt Migration Tests

```bash
cd backend
source venv/bin/activate
pytest tests/test_prompt_version.py tests/test_regression_prompt_migration.py -v
```

### Run Individual Test Suites

**Unit Tests (Prompt Version Configuration):**
```bash
pytest tests/test_prompt_version.py -v
```

**Regression Tests (Backward Compatibility):**
```bash
pytest tests/test_regression_prompt_migration.py -v
```

---

## Test Success Criteria

### Mandatory: 100% Pass Rate

All tests must pass with **zero failures** before deployment:

```
tests/test_prompt_version.py ..................... [ 60%] ✓
tests/test_regression_prompt_migration.py ........ [100%] ✓

======================== 8 passed in 2.34s ========================
```

### What Each Test Validates

#### test_prompt_version.py
- ✅ Default prompt version is `baseline_v1` (backward compatible)
- ✅ Environment variable `PROMPT_VERSION` can override default
- ✅ Invalid prompt versions raise appropriate errors
- ✅ All registered prompts (`baseline_v1`, `chain_of_thought_v1`, `fit_constraints_v2`) work

#### test_regression_prompt_migration.py
- ✅ `StyleGenerationEngine()` defaults to `baseline_v1` when no version specified
- ✅ Baseline prompt produces expected output structure
- ✅ Chain-of-thought prompt produces expected output structure (with reasoning steps)
- ✅ Different engine instances can use different prompt versions independently
- ✅ Anchor item handling works in both baseline and CoT prompts

---

## Implementation Checklist

Use this checklist to track your implementation progress:

### 1. Environment Configuration
- [ ] Add `PROMPT_VERSION` to `backend/core/config.py` with default `"baseline_v1"`
- [ ] Verify environment variable can be loaded from `.env`
- [ ] Test: `test_default_prompt_version_is_baseline()` passes
- [ ] Test: `test_prompt_version_can_be_overridden()` passes

### 2. API Endpoint Updates
- [ ] Update `backend/api/outfits.py` to accept optional `prompt_version` in request body
- [ ] Validate prompt version exists before queueing job
- [ ] Pass `prompt_version` to background job
- [ ] Return `prompt_version` in API response (202 status)
- [ ] Return error (400 status) for invalid prompt versions

### 3. Background Worker Updates
- [ ] Update `backend/workers/outfit_worker.py` to accept `prompt_version` parameter
- [ ] Default to environment variable if not provided
- [ ] Pass `prompt_version` to `StyleGenerationEngine` constructor
- [ ] Adjust `max_tokens` based on prompt version (3000 for CoT, 2000 for others)
- [ ] Include `prompt_version` in response metadata
- [ ] Test: `test_style_engine_defaults_to_baseline()` passes

### 4. Regression Testing
- [ ] Run all existing tests to ensure no breaking changes
- [ ] Test: `test_baseline_prompt_output_structure()` passes
- [ ] Test: `test_chain_of_thought_prompt_structure()` passes
- [ ] Test: `test_prompt_version_selection_is_isolated()` passes
- [ ] Test: `test_baseline_handles_anchor_items()` passes
- [ ] Test: `test_chain_of_thought_handles_anchor_items()` passes

### 5. Manual Validation
- [ ] Start local server and test API endpoint without `prompt_version` (should use baseline)
- [ ] Test API endpoint with `prompt_version: "chain_of_thought_v1"` (should use CoT)
- [ ] Test API endpoint with invalid `prompt_version: "invalid"` (should return 400)
- [ ] Verify response includes `metadata.prompt_version`

---

## Common Issues and Solutions

### Issue 1: Tests fail with "ImportError: cannot import name 'get_settings'"

**Solution:** Ensure `backend/core/config.py` exports `get_settings()` function:
```python
from functools import lru_cache

@lru_cache()
def get_settings():
    return Settings()
```

### Issue 2: Tests fail with "Unknown prompt version: chain_of_thought_v1"

**Solution:** Ensure `backend/services/prompts/library.py` has all prompts registered:
```python
class PromptLibrary:
    _PROMPTS = {
        "baseline_v1": BaselinePromptV1,
        "fit_constraints_v2": FitConstraintsPromptV2,
        "chain_of_thought_v1": ChainOfThoughtPromptV1  # Must be registered
    }
```

### Issue 3: Tests fail with "AttributeError: 'StyleGenerationEngine' object has no attribute 'prompt_version'"

**Solution:** Ensure `StyleGenerationEngine.__init__()` stores the prompt_version:
```python
def __init__(self, prompt_version: str = "baseline_v1", ...):
    self.prompt_version = prompt_version  # Store for later use
```

### Issue 4: Environment variable override test fails

**Solution:** Ensure you reload the settings module after monkeypatching:
```python
from importlib import reload
import core.config
reload(core.config)
settings = core.config.get_settings()
```

---

## Expected Test Output

When all tests pass, you should see:

```
======================== test session starts ========================
platform darwin -- Python 3.11.x, pytest-7.x.x, pluggy-1.x.x
rootdir: /Users/peichin/Projects/style-inspo-api/backend
collected 11 items

tests/test_prompt_version.py ......                           [ 54%]
tests/test_regression_prompt_migration.py .......             [100%]

======================== 11 passed in 3.21s ========================
```

---

## Deployment Readiness

Before marking this task complete:

1. **All Tests Pass:** ✅ 100% pass rate on test suite
2. **Manual Testing:** ✅ Tested locally with both prompt versions
3. **Code Review:** ✅ Implementation follows spec exactly
4. **Documentation:** ✅ Updated API documentation if needed
5. **Rollback Plan:** ✅ Understand how to revert via environment variable

---

## Questions?

If you encounter any issues or ambiguities:

1. Re-read `CURSOR_SPEC_PROMPT_MIGRATION.md` for detailed context
2. Check the existing prompt library code in `backend/services/prompts/`
3. Review the eval test code in `backend/tests/outfit_eval/` for patterns
4. Ask the human for clarification if specification is unclear

---

## Success!

Once all tests pass, you have successfully:

✅ Abstracted prompt selection into a configurable system
✅ Maintained 100% backward compatibility
✅ Enabled runtime prompt version switching
✅ Prepared for safe chain-of-thought rollout to production

**Next step:** Deploy to staging and monitor for 24 hours before production rollout.
