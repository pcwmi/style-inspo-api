"""
Unit tests for prompt version configuration and selection.

These tests validate:
1. Default prompt version is baseline_v1 (backward compatibility)
2. Environment variables can override default
3. Invalid prompt versions raise appropriate errors
4. All registered prompts can be instantiated

CRITICAL: All tests must pass before deploying prompt migration to production.
"""

import pytest
from core.config import get_settings
from services.prompts.library import PromptLibrary


class TestPromptVersionConfiguration:
    """Test environment-based prompt version configuration"""

    def test_default_prompt_version_is_baseline(self):
        """Verify default prompt version is baseline_v1 for backward compatibility"""
        settings = get_settings()
        assert settings.PROMPT_VERSION == "baseline_v1", \
            "Default prompt version must be baseline_v1 to maintain backward compatibility"

    def test_prompt_version_can_be_overridden(self, monkeypatch):
        """Test environment variable override works correctly"""
        monkeypatch.setenv("PROMPT_VERSION", "chain_of_thought_v1")

        # Force reload of settings
        from importlib import reload
        import core.config
        reload(core.config)

        settings = core.config.get_settings()
        assert settings.PROMPT_VERSION == "chain_of_thought_v1", \
            "Environment variable should override default prompt version"

    def test_invalid_prompt_version_raises_error(self):
        """Test that invalid prompt version raises ValueError"""
        with pytest.raises(ValueError, match="Unknown prompt version"):
            PromptLibrary.get_prompt("invalid_version")

    def test_all_registered_prompts_are_valid(self):
        """Test that all registered prompts can be instantiated and have correct interface"""
        for version in ["baseline_v1", "fit_constraints_v2", "chain_of_thought_v1"]:
            prompt = PromptLibrary.get_prompt(version)

            # Verify prompt has correct version property
            assert prompt.version == version, \
                f"Prompt version property should match requested version: {version}"

            # Verify prompt has required methods
            assert hasattr(prompt, 'build'), \
                f"Prompt {version} must have build() method"
            assert hasattr(prompt, 'system_message'), \
                f"Prompt {version} must have system_message property"

    def test_baseline_v1_is_registered(self):
        """Baseline v1 must always be available (production default)"""
        prompt = PromptLibrary.get_prompt("baseline_v1")
        assert prompt is not None
        assert prompt.version == "baseline_v1"

    def test_chain_of_thought_v1_is_registered(self):
        """Chain-of-thought v1 must be available (new production option)"""
        prompt = PromptLibrary.get_prompt("chain_of_thought_v1")
        assert prompt is not None
        assert prompt.version == "chain_of_thought_v1"
