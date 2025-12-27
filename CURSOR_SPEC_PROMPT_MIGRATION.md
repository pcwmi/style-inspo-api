# Cursor Implementation Spec: Production Prompt Abstraction & Chain-of-Thought Migration

**Date:** 2025-12-18
**Context:** Moving chain-of-thought prompt to production with safe abstraction layer
**Complexity:** Medium - Requires careful testing to avoid breaking production

---

## Executive Summary

**Goal:** Enable runtime prompt version selection in production while maintaining backward compatibility and safety.

**Why:** Currently, prompt versions are hardcoded (`baseline_v1`). To ship the new chain-of-thought prompt to production and A/B test it safely, we need:
1. Environment-based configuration for default prompt version
2. Per-request prompt version override capability (for testing)
3. Comprehensive tests to ensure no regressions

**Success Criteria:**
- ✅ Existing production flows work unchanged with `baseline_v1` (backward compatible)
- ✅ Can switch to `chain_of_thought_v1` via environment variable
- ✅ Can override prompt version per API request (for A/B testing)
- ✅ All tests pass (existing + new validation tests)
- ✅ No changes to API response format

---

## Current State Analysis

### 1. Hardcoded Prompt Version Locations

**Location 1: StyleGenerationEngine Default**
```python
# backend/services/style_engine.py:50
def __init__(
    self,
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    max_tokens: int = 2000,
    prompt_version: str = "baseline_v1"  # ❌ HARDCODED
):
```

**Location 2: Background Worker Instantiation**
```python
# backend/workers/outfit_worker.py:113
engine = StyleGenerationEngine()  # ❌ Uses default, no version passed
```

**Location 3: Consider Buying API**
```python
# backend/api/consider_buying.py (multiple locations)
engine = StyleGenerationEngine()  # ❌ Uses default
```

### 2. Existing Prompt Registry

The `PromptLibrary` abstraction already exists and works correctly:

```python
# backend/services/prompts/library.py
class PromptLibrary:
    _PROMPTS = {
        "baseline_v1": BaselinePromptV1,
        "fit_constraints_v2": FitConstraintsPromptV2,
        "chain_of_thought_v1": ChainOfThoughtPromptV1  # ✅ Already registered
    }

    @classmethod
    def get_prompt(cls, version: str) -> PromptTemplate:
        if version not in cls._PROMPTS:
            raise ValueError(f"Unknown prompt version: {version}")
        return cls._PROMPTS[version]()
```

### 3. API Entry Points

**Primary Endpoint:**
```python
# backend/api/outfits.py:26-50
@bp.route('/generate', methods=['POST'])
def generate_outfits():
    """Generate outfit combinations for a user"""
    data = request.json
    # Queues: generate_outfits_job(user_id, occasions, weather, temp, mode, anchor_items)
    # ❌ No prompt_version parameter
```

**Background Job:**
```python
# backend/workers/outfit_worker.py:26-263
def generate_outfits_job(user_id, occasions, weather_condition, temperature_range, mode, anchor_items, mock=False):
    # Line 113: engine = StyleGenerationEngine()
    # ❌ No prompt_version handling
```

---

## Desired End State

### 1. Environment Configuration

**New Environment Variable:**
```bash
# .env
PROMPT_VERSION=baseline_v1  # Default (backward compatible)
# PROMPT_VERSION=chain_of_thought_v1  # Can switch to new prompt
```

**Configuration Loading:**
```python
# backend/core/config.py
class Settings(BaseSettings):
    # Existing...
    OPENAI_API_KEY: str
    STORAGE_TYPE: str = "local"

    # ✅ NEW: Default prompt version for outfit generation
    PROMPT_VERSION: str = "baseline_v1"
```

### 2. Per-Request Override (Optional)

**API Request:**
```json
POST /api/outfits/generate
{
  "occasions": ["business meeting"],
  "weather_condition": "cool",
  "temperature_range": "55-65°F",
  "mode": "occasion",
  "prompt_version": "chain_of_thought_v1"  // ✅ NEW: Optional override
}
```

**Response Metadata:**
```json
{
  "outfits": [...],
  "metadata": {
    "prompt_version": "chain_of_thought_v1",  // ✅ NEW: Track which version was used
    "model": "gpt-4o",
    "latency_ms": 3456
  }
}
```

### 3. Updated Call Flow

```
API Request
  ↓
1. Extract prompt_version from request (or use env default)
  ↓
2. Pass prompt_version to RQ job
  ↓
3. Background worker creates: StyleGenerationEngine(prompt_version=version)
  ↓
4. Engine uses PromptLibrary.get_prompt(version)
  ↓
5. Return metadata with prompt_version used
```

---

## Implementation Tasks

### Task 1: Add Environment Configuration

**File:** `backend/core/config.py`

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Prompt configuration
    PROMPT_VERSION: str = Field(
        default="baseline_v1",
        description="Default prompt version for outfit generation"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

**Validation:**
- Default value is `"baseline_v1"` (backward compatible)
- Can be overridden via `.env` file or environment variable

---

### Task 2: Update API Endpoint

**File:** `backend/api/outfits.py`

**Changes:**
1. Accept optional `prompt_version` in request body
2. Validate prompt version exists in registry
3. Pass to background job

**Implementation:**
```python
@bp.route('/generate', methods=['POST'])
def generate_outfits():
    """Generate outfit combinations for a user"""
    data = request.json
    user_id = data.get('user_id')
    occasions = data.get('occasions', [])
    weather_condition = data.get('weather_condition')
    temperature_range = data.get('temperature_range')
    mode = data.get('mode', 'occasion')
    anchor_items = data.get('anchor_items', [])
    mock = data.get('mock', False)

    # ✅ NEW: Get prompt version (request override or env default)
    prompt_version = data.get('prompt_version', get_settings().PROMPT_VERSION)

    # ✅ NEW: Validate prompt version exists
    try:
        from services.prompts.library import PromptLibrary
        PromptLibrary.get_prompt(prompt_version)  # Validates version exists
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Queue job with prompt version
    job = queue.enqueue(
        'workers.outfit_worker.generate_outfits_job',
        user_id=user_id,
        occasions=occasions,
        weather_condition=weather_condition,
        temperature_range=temperature_range,
        mode=mode,
        anchor_items=anchor_items,
        mock=mock,
        prompt_version=prompt_version  # ✅ NEW: Pass to worker
    )

    return jsonify({
        'job_id': job.id,
        'status': 'queued',
        'prompt_version': prompt_version  # ✅ NEW: Return in response
    }), 202
```

---

### Task 3: Update Background Worker

**File:** `backend/workers/outfit_worker.py`

**Changes:**
1. Add `prompt_version` parameter to job function
2. Pass to StyleGenerationEngine constructor
3. Include in response metadata

**Implementation:**
```python
def generate_outfits_job(
    user_id: str,
    occasions: List[str],
    weather_condition: str,
    temperature_range: str,
    mode: str,
    anchor_items: List[str],
    mock: bool = False,
    prompt_version: str = None  # ✅ NEW: Optional parameter
):
    """Background job to generate outfit combinations"""

    # ✅ NEW: Use provided version or fall back to env default
    if prompt_version is None:
        from core.config import get_settings
        prompt_version = get_settings().PROMPT_VERSION

    # ... existing wardrobe loading logic ...

    # Create engine with specified prompt version
    engine = StyleGenerationEngine(
        model="gpt-4o",
        temperature=0.7,
        max_tokens=3000,  # Note: CoT needs more tokens for reasoning
        prompt_version=prompt_version  # ✅ NEW: Pass version
    )

    # ... existing outfit generation logic ...

    # ✅ NEW: Include metadata in response
    return {
        'outfits': outfits,
        'metadata': {
            'prompt_version': prompt_version,  # ✅ NEW
            'model': engine.model,
            'temperature': engine.temperature,
            'latency_ms': int((time.time() - start_time) * 1000)
        }
    }
```

---

### Task 4: Update Consider Buying API (Optional)

**File:** `backend/api/consider_buying.py`

**Changes:**
Similar to Task 2-3, add prompt_version support to consider_buying endpoints.

**Note:** This is lower priority - can be done in a follow-up if consider_buying is less critical.

---

### Task 5: Update max_tokens for Chain-of-Thought

**File:** `backend/workers/outfit_worker.py`

**Issue:** Chain-of-thought prompts produce longer output (reasoning + JSON). Current `max_tokens=2000` might truncate responses.

**Solution:**
```python
# Adjust max_tokens based on prompt version
max_tokens = 3000 if "chain_of_thought" in prompt_version else 2000

engine = StyleGenerationEngine(
    model="gpt-4o",
    temperature=0.7,
    max_tokens=max_tokens,
    prompt_version=prompt_version
)
```

---

## Test Requirements

### Test Suite 1: Unit Tests for Prompt Version Selection

**File:** `backend/tests/test_prompt_version.py` (NEW)

```python
import pytest
from core.config import get_settings
from services.prompts.library import PromptLibrary

class TestPromptVersionConfiguration:
    """Test environment-based prompt version configuration"""

    def test_default_prompt_version_is_baseline(self):
        """Verify default prompt version is baseline_v1 for backward compatibility"""
        settings = get_settings()
        assert settings.PROMPT_VERSION == "baseline_v1"

    def test_prompt_version_can_be_overridden(self, monkeypatch):
        """Test environment variable override"""
        monkeypatch.setenv("PROMPT_VERSION", "chain_of_thought_v1")
        from core.config import Settings
        settings = Settings()
        assert settings.PROMPT_VERSION == "chain_of_thought_v1"

    def test_invalid_prompt_version_raises_error(self):
        """Test that invalid prompt version raises ValueError"""
        with pytest.raises(ValueError, match="Unknown prompt version"):
            PromptLibrary.get_prompt("invalid_version")

    def test_all_registered_prompts_are_valid(self):
        """Test that all registered prompts can be instantiated"""
        for version in ["baseline_v1", "fit_constraints_v2", "chain_of_thought_v1"]:
            prompt = PromptLibrary.get_prompt(version)
            assert prompt.version == version
```

### Test Suite 2: API Endpoint Tests

**File:** `backend/tests/test_outfits_api.py` (EXTEND EXISTING)

```python
class TestOutfitGenerationAPI:
    """Test API endpoint with prompt version support"""

    def test_generate_outfits_default_prompt_version(self, client):
        """Test outfit generation uses default prompt version"""
        response = client.post('/api/outfits/generate', json={
            'user_id': 'test_user',
            'occasions': ['casual weekend'],
            'weather_condition': 'mild',
            'temperature_range': '60-70°F',
            'mode': 'occasion'
        })
        assert response.status_code == 202
        data = response.get_json()
        assert data['prompt_version'] == 'baseline_v1'

    def test_generate_outfits_custom_prompt_version(self, client):
        """Test outfit generation with custom prompt version"""
        response = client.post('/api/outfits/generate', json={
            'user_id': 'test_user',
            'occasions': ['casual weekend'],
            'weather_condition': 'mild',
            'temperature_range': '60-70°F',
            'mode': 'occasion',
            'prompt_version': 'chain_of_thought_v1'  # Override
        })
        assert response.status_code == 202
        data = response.get_json()
        assert data['prompt_version'] == 'chain_of_thought_v1'

    def test_generate_outfits_invalid_prompt_version(self, client):
        """Test that invalid prompt version returns 400"""
        response = client.post('/api/outfits/generate', json={
            'user_id': 'test_user',
            'occasions': ['casual weekend'],
            'mode': 'occasion',
            'prompt_version': 'invalid_version'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Unknown prompt version' in data['error']
```

### Test Suite 3: Integration Tests (Background Worker)

**File:** `backend/tests/test_outfit_worker.py` (EXTEND EXISTING)

```python
class TestOutfitWorkerPromptVersion:
    """Test background worker with different prompt versions"""

    @pytest.fixture
    def mock_wardrobe(self):
        """Minimal wardrobe for testing"""
        return {
            'items': [
                {'name': 'White tee', 'category': 'tops'},
                {'name': 'Blue jeans', 'category': 'bottoms'},
                {'name': 'Sneakers', 'category': 'footwear'}
            ]
        }

    def test_worker_uses_default_prompt_version(self, mock_wardrobe):
        """Test worker uses env default when no version specified"""
        result = generate_outfits_job(
            user_id='test_user',
            occasions=['casual'],
            weather_condition='mild',
            temperature_range='60-70°F',
            mode='occasion',
            anchor_items=[],
            mock=True
        )
        assert result['metadata']['prompt_version'] == 'baseline_v1'

    def test_worker_uses_specified_prompt_version(self, mock_wardrobe):
        """Test worker respects explicitly provided version"""
        result = generate_outfits_job(
            user_id='test_user',
            occasions=['casual'],
            weather_condition='mild',
            temperature_range='60-70°F',
            mode='occasion',
            anchor_items=[],
            mock=True,
            prompt_version='chain_of_thought_v1'
        )
        assert result['metadata']['prompt_version'] == 'chain_of_thought_v1'

    def test_chain_of_thought_produces_valid_outfits(self, mock_wardrobe):
        """Test CoT prompt produces correctly structured outfits"""
        result = generate_outfits_job(
            user_id='test_user',
            occasions=['casual'],
            weather_condition='mild',
            temperature_range='60-70°F',
            mode='occasion',
            anchor_items=[],
            mock=True,
            prompt_version='chain_of_thought_v1'
        )

        # Validate response structure
        assert 'outfits' in result
        assert len(result['outfits']) >= 1

        # Validate outfit structure matches baseline format
        for outfit in result['outfits']:
            assert 'items' in outfit
            assert 'styling_notes' in outfit
            assert 'why_it_works' in outfit
            assert isinstance(outfit['items'], list)
            assert len(outfit['items']) >= 3  # Minimum outfit completeness
```

### Test Suite 4: Prompt Output Validation

**File:** `backend/tests/test_prompt_output_validation.py` (NEW)

```python
import pytest
from services.style_engine import StyleGenerationEngine
from services.prompts.base import PromptContext

class TestPromptOutputValidation:
    """Test that all prompt versions produce valid, compatible output"""

    @pytest.fixture
    def sample_context(self):
        """Sample styling context"""
        return PromptContext(
            user_profile={
                "three_words": {
                    "current": "classic",
                    "aspirational": "relaxed",
                    "feeling": "playful"
                }
            },
            available_items=[
                {'name': 'White tee', 'category': 'tops'},
                {'name': 'Blue jeans', 'category': 'bottoms'},
                {'name': 'Sneakers', 'category': 'footwear'}
            ],
            styling_challenges=[],
            occasion="casual weekend",
            weather_condition="mild",
            temperature_range="60-70°F"
        )

    @pytest.mark.parametrize("prompt_version", [
        "baseline_v1",
        "chain_of_thought_v1",
        "fit_constraints_v2"
    ])
    def test_prompt_produces_valid_json(self, prompt_version, sample_context):
        """Test each prompt version produces parseable JSON"""
        engine = StyleGenerationEngine(prompt_version=prompt_version)

        # Create prompt
        prompt = engine.create_style_prompt(
            user_profile=sample_context.user_profile,
            available_items=sample_context.available_items,
            styling_challenges=sample_context.styling_challenges,
            occasion=sample_context.occasion,
            weather_condition=sample_context.weather_condition,
            temperature_range=sample_context.temperature_range
        )

        # Verify prompt is non-empty
        assert len(prompt) > 100
        assert sample_context.occasion in prompt

    @pytest.mark.parametrize("prompt_version", [
        "baseline_v1",
        "chain_of_thought_v1"
    ])
    def test_prompt_handles_anchor_items(self, prompt_version):
        """Test prompts correctly handle anchor items (complete-my-outfit)"""
        context = PromptContext(
            user_profile={"three_words": {"current": "classic", "aspirational": "relaxed", "feeling": "playful"}},
            available_items=[
                {'name': 'White tee', 'category': 'tops'},
                {'name': 'Blue jeans', 'category': 'bottoms'}
            ],
            styling_challenges=[
                {'name': 'Cream boots', 'category': 'footwear'}  # Anchor item
            ],
            occasion="casual weekend",
            weather_condition="mild",
            temperature_range="60-70°F"
        )

        engine = StyleGenerationEngine(prompt_version=prompt_version)
        prompt = engine.create_style_prompt(
            user_profile=context.user_profile,
            available_items=context.available_items,
            styling_challenges=context.styling_challenges,
            occasion=context.occasion,
            weather_condition=context.weather_condition,
            temperature_range=context.temperature_range
        )

        # Verify anchor item appears in prompt
        assert 'Cream boots' in prompt

        # Verify anchor requirement is present
        if prompt_version == "baseline_v1":
            assert 'ANCHOR PIECE - REQUIRED' in prompt or 'MUST include' in prompt
        elif prompt_version == "chain_of_thought_v1":
            assert 'user has selected' in prompt or 'MUST appear in ALL' in prompt
```

### Test Suite 5: Regression Tests (Backward Compatibility)

**File:** `backend/tests/test_regression_prompt_migration.py` (NEW)

```python
import pytest

class TestBackwardCompatibility:
    """Ensure changes don't break existing production behavior"""

    def test_default_behavior_unchanged(self, client):
        """Test that default behavior (no prompt_version) still works"""
        # This is critical - existing API clients should see no change
        response = client.post('/api/outfits/generate', json={
            'user_id': 'test_user',
            'occasions': ['casual'],
            'mode': 'occasion'
        })
        assert response.status_code == 202

    def test_existing_api_contracts_maintained(self, client):
        """Test existing response format is maintained"""
        response = client.post('/api/outfits/generate', json={
            'user_id': 'test_user',
            'occasions': ['casual'],
            'mode': 'occasion'
        })
        data = response.get_json()

        # Required fields in response
        assert 'job_id' in data
        assert 'status' in data

        # New field is additive only
        assert 'prompt_version' in data

    def test_baseline_prompt_output_unchanged(self):
        """Test baseline_v1 prompt still produces expected output structure"""
        from services.style_engine import StyleGenerationEngine

        engine = StyleGenerationEngine(prompt_version="baseline_v1")

        # Generate sample outfit
        result = engine.generate_outfit_combinations(
            user_profile={"three_words": {"current": "classic", "aspirational": "relaxed", "feeling": "playful"}},
            available_items=[...],  # Sample wardrobe
            occasion="casual",
            weather_condition="mild",
            temperature_range="60-70°F"
        )

        # Validate output structure matches production format
        assert len(result) >= 1
        for outfit in result:
            assert 'items' in outfit
            assert 'styling_notes' in outfit
            assert 'why_it_works' in outfit
```

---

## Validation Checklist

Before merging to production, verify:

### Pre-Merge Checklist

- [ ] All new tests pass (100% pass rate)
- [ ] All existing tests still pass (no regressions)
- [ ] Manual test: API request without `prompt_version` uses `baseline_v1`
- [ ] Manual test: API request with `prompt_version: "chain_of_thought_v1"` works
- [ ] Manual test: Invalid prompt version returns 400 error
- [ ] Code review completed
- [ ] Documentation updated (API docs, environment variables)

### Post-Deploy Checklist (Staging)

- [ ] Deploy to staging environment
- [ ] Test baseline prompt in staging (existing flow)
- [ ] Test chain-of-thought prompt in staging (new flow)
- [ ] Verify response metadata includes `prompt_version`
- [ ] Monitor logs for errors
- [ ] Test A/B scenario: some requests with baseline, some with CoT

### Production Rollout Plan

**Phase 1: Deploy with Default Baseline (Safe)**
```bash
# .env (production)
PROMPT_VERSION=baseline_v1  # No change from current behavior
```
- Deploy code changes
- Monitor for 24 hours
- Verify no errors or regressions

**Phase 2: Test Chain-of-Thought with Select Users**
- Use per-request override to test CoT with internal users
- Collect feedback on outfit quality
- Monitor API latency (CoT takes ~30s vs ~15s for baseline)

**Phase 3: Gradual Rollout**
- Option A: Switch environment variable to `chain_of_thought_v1` (100% traffic)
- Option B: Implement probabilistic routing (50% baseline, 50% CoT)
- Monitor user feedback and performance metrics

---

## Rollback Plan

If issues are detected after deployment:

**Quick Rollback (Environment Variable)**
```bash
# Revert .env to baseline
PROMPT_VERSION=baseline_v1
```
- Restart workers to pick up new config
- No code changes needed

**Full Rollback (Git)**
```bash
git revert <commit-hash>
git push origin main
```
- Redeploy previous version
- All changes reverted

---

## Implementation Timeline

**Estimated Time:** 2-3 hours
- 30 min: Add environment config + API changes
- 30 min: Update background worker
- 60 min: Write tests (5 test suites)
- 30 min: Manual testing + validation

**Suggested Order:**
1. Add environment configuration (Task 1)
2. Write tests (Test Suites 1-5) - **Do this before implementation**
3. Update API endpoint (Task 2)
4. Update background worker (Task 3)
5. Adjust max_tokens (Task 5)
6. Run all tests
7. Manual testing
8. Deploy to staging

---

## Additional Notes

### Chain-of-Thought Response Format (CRITICAL)

**Output Format Difference:**

**Baseline v1:**
```json
[
  {
    "items": ["White tee", "Blue jeans", "Sneakers"],
    "styling_notes": "...",
    "why_it_works": "..."
  }
]
```

**Chain-of-Thought v1:**
```
[Reasoning text with STEP 1, STEP 2, etc...]

===JSON OUTPUT===

[
  {
    "items": ["White tee", "Blue jeans", "Sneakers"],
    "styling_notes": "...",
    "why_it_works": "..."
  }
]
```

**✅ GOOD NEWS: Parsing Already Handles Both Formats**

The existing code in `style_engine.py` (lines 471-480) already detects and parses both formats:
- Detects `===JSON OUTPUT===` marker
- Extracts JSON after marker for CoT responses
- Extracts JSON directly for baseline responses

**NO CODE CHANGES NEEDED** for response parsing - it already works!

### Chain-of-Thought Performance Considerations

**Latency:**
- Baseline: ~15-25s per generation
- Chain-of-thought: ~25-40s per generation (includes reasoning)
- **Mitigation:** Already using background jobs, user experience unchanged

**Token Usage:**
- Baseline: ~2000 tokens output
- Chain-of-thought: ~3000-4000 tokens output (reasoning + JSON)
- **Mitigation:** Increased `max_tokens` to 3000 for CoT

**Cost:**
- CoT uses ~50% more tokens
- **Mitigation:** Track cost metrics, consider rate limiting if needed

### Future Enhancements (Out of Scope)

- Per-user prompt version preferences (stored in user profile)
- A/B test framework with automatic traffic splitting
- Prompt performance metrics dashboard
- Automated prompt quality evaluation

---

## Success Metrics

After migration, track:
- **Reliability:** Zero increase in error rate
- **Performance:** No degradation in baseline prompt latency
- **Quality:** User feedback on CoT outfits vs baseline
- **Adoption:** % of requests using CoT prompt

---

## Questions for Cursor

If anything is unclear during implementation:
1. Should we add logging for which prompt version was used?
2. Should we add rate limiting per prompt version?
3. Should we add prompt version to database for audit trail?

---

## References

- Current Production Code: `backend/services/style_engine.py`
- Prompt Library: `backend/services/prompts/library.py`
- Background Worker: `backend/workers/outfit_worker.py`
- API Endpoint: `backend/api/outfits.py`
- Eval Results: See `/run-eval --preset cot-complete-my-outfit` results
