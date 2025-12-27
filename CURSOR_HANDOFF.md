# Cursor Implementation Task: Production Prompt Abstraction

## Quick Start

**Goal:** Enable runtime prompt version selection in production to safely ship chain-of-thought prompt.

**Files to Read:**
1. `CURSOR_SPEC_PROMPT_MIGRATION.md` - Full implementation specification
2. `CURSOR_TEST_INSTRUCTIONS.md` - Test requirements and validation

**Success Criteria:** All tests in `backend/tests/test_prompt_version.py` and `backend/tests/test_regression_prompt_migration.py` must pass.

---

## What You Need to Implement

### 1. Add Environment Configuration (5 min)

**File:** `backend/core/config.py`

Add this field to the `Settings` class:
```python
PROMPT_VERSION: str = Field(
    default="baseline_v1",
    description="Default prompt version for outfit generation"
)
```

### 2. Update API Endpoint (15 min)

**File:** `backend/api/outfits.py`

Add these changes to the `/generate` endpoint:
- Accept optional `prompt_version` in request body
- Validate it exists (use `PromptLibrary.get_prompt()`)
- Pass to background job
- Return in response

### 3. Update Background Worker (15 min)

**File:** `backend/workers/outfit_worker.py`

Update `generate_outfits_job()`:
- Add `prompt_version: str = None` parameter
- Default to `get_settings().PROMPT_VERSION` if None
- Pass to `StyleGenerationEngine(prompt_version=...)`
- Adjust `max_tokens` (3000 for CoT, 2000 for others)
- Include in response metadata

### 4. Run Tests (5 min)

```bash
cd backend
pytest tests/test_prompt_version.py tests/test_regression_prompt_migration.py -v
```

**Must see:** ✅ 11/11 tests passing

---

## Key Implementation Rules

### ✅ DO:
- Use exact variable names from spec (`PROMPT_VERSION`, not `PROMPT_VER`)
- Default to `"baseline_v1"` everywhere (backward compatible)
- Validate prompt version before using it
- Include `prompt_version` in API response metadata
- Pass tests 100%

### ❌ DON'T:
- Change any existing API response formats (additive only)
- Break backward compatibility (no version = baseline)
- Skip validation (invalid versions must return 400 error)
- Modify prompt template code (library already works)

---

## Testing Your Implementation

### Quick Test Cycle

```bash
# 1. Run tests
pytest tests/test_prompt_version.py tests/test_regression_prompt_migration.py -v

# 2. Manual test (start server)
cd backend
python -m uvicorn api.main:app --reload

# 3. Test default behavior (should use baseline_v1)
curl -X POST http://localhost:8000/api/outfits/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "occasions": ["casual"],
    "mode": "occasion"
  }'

# 4. Test CoT override
curl -X POST http://localhost:8000/api/outfits/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "occasions": ["casual"],
    "mode": "occasion",
    "prompt_version": "chain_of_thought_v1"
  }'

# 5. Test invalid version (should return 400)
curl -X POST http://localhost:8000/api/outfits/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "occasions": ["casual"],
    "prompt_version": "invalid"
  }'
```

---

## File Locations Reference

```
backend/
├── core/
│   └── config.py              # Add PROMPT_VERSION here
├── api/
│   └── outfits.py             # Update /generate endpoint
├── workers/
│   └── outfit_worker.py       # Update generate_outfits_job()
├── services/
│   ├── style_engine.py        # Already supports prompt_version ✅
│   └── prompts/
│       ├── library.py         # Already has all prompts registered ✅
│       ├── baseline_v1.py     # Production default ✅
│       └── chain_of_thought_v1.py  # New production option ✅
└── tests/
    ├── test_prompt_version.py          # NEW - Your tests to pass
    └── test_regression_prompt_migration.py  # NEW - Your tests to pass
```

---

## Expected Outcome

### Before Your Changes
```python
# Can only use baseline_v1
engine = StyleGenerationEngine()  # Hardcoded to baseline
```

### After Your Changes
```python
# Can configure via environment
# .env: PROMPT_VERSION=chain_of_thought_v1
engine = StyleGenerationEngine()  # Uses env default

# Can override per request
engine = StyleGenerationEngine(prompt_version="chain_of_thought_v1")
```

---

## Validation Checklist

Before submitting your implementation:

- [ ] All 11 tests pass (100% pass rate required)
- [ ] `PROMPT_VERSION` environment variable works
- [ ] API accepts `prompt_version` in request
- [ ] Invalid prompt version returns 400 error
- [ ] Response includes `prompt_version` in metadata
- [ ] Default behavior unchanged (baseline_v1)
- [ ] No breaking changes to existing API contracts

---

## Time Estimate

**Total:** ~40 minutes
- 5 min: Read spec and understand context
- 5 min: Add environment config
- 15 min: Update API endpoint
- 15 min: Update background worker
- 5 min: Run tests and validate

---

## Help & Troubleshooting

**If tests fail:**
1. Read error message carefully
2. Check `CURSOR_TEST_INSTRUCTIONS.md` "Common Issues" section
3. Verify you followed the spec exactly (variable names, types, defaults)

**If unsure about something:**
1. Re-read `CURSOR_SPEC_PROMPT_MIGRATION.md` Section X
2. Look at existing code patterns in `backend/services/prompts/`
3. Ask the human for clarification

---

## Success Metrics

You're done when:
✅ All tests pass
✅ Can switch prompts via environment variable
✅ Can override prompt per API request
✅ Backward compatibility maintained (existing code works unchanged)

**Deploy strategy:** See `CURSOR_SPEC_PROMPT_MIGRATION.md` Section "Production Rollout Plan"
