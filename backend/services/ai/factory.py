"""AI Provider Factory for creating provider instances."""

import os
from typing import Optional

from .providers.base import AIProvider, AIProviderConfig
from .providers.openai import OpenAIProvider
from .providers.gemini import GeminiProvider
from .providers.claude import ClaudeProvider


class AIProviderFactory:
    """Factory for creating AI provider instances."""

    @staticmethod
    def create(
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        api_key: Optional[str] = None
    ) -> AIProvider:
        """
        Create an AI provider instance based on model name.

        Args:
            model: Model identifier (e.g., 'gpt-4o', 'gemini-2.0-flash-exp', 'claude-3-5-sonnet-20241022')
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            api_key: Optional API key (if not provided, will use environment variables)

        Returns:
            Configured AIProvider instance

        Raises:
            ValueError: If model is not recognized or API key is missing
        """
        # Detect provider from model name
        provider_type = AIProviderFactory._detect_provider(model)

        # Get API key from environment if not provided
        if api_key is None:
            api_key = AIProviderFactory._get_api_key(provider_type)

        # Create config
        config = AIProviderConfig(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key
        )

        # Instantiate provider
        if provider_type == "openai":
            return OpenAIProvider(config)
        elif provider_type == "google":
            return GeminiProvider(config)
        elif provider_type == "anthropic":
            return ClaudeProvider(config)
        else:
            raise ValueError(f"Unknown provider for model: {model}")

    @staticmethod
    def _detect_provider(model: str) -> str:
        """Detect provider from model name."""
        model_lower = model.lower()

        if any(x in model_lower for x in ["gpt-", "o1-", "o1"]):
            return "openai"
        elif "gemini" in model_lower:
            return "google"
        elif "claude" in model_lower:
            return "anthropic"
        else:
            raise ValueError(f"Could not detect provider from model name: {model}")

    @staticmethod
    def _get_api_key(provider: str) -> str:
        """Get API key from environment variables."""
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY"
        }

        env_var = env_vars.get(provider)
        if not env_var:
            raise ValueError(f"Unknown provider: {provider}")

        api_key = os.getenv(env_var)
        if not api_key:
            raise ValueError(f"API key not found in environment variable: {env_var}")

        return api_key

    @staticmethod
    def list_available_providers() -> dict:
        """
        List all available providers and their models.

        Returns:
            Dict of {provider_name: [available_models]}
        """
        return {
            "openai": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-4",
                "gpt-3.5-turbo",
                "o1",
                "o1-mini",
                "o1-preview"
            ],
            "google": [
                "gemini-2.0-flash-exp",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-pro",
                "gemini-pro-vision"
            ],
            "anthropic": [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-sonnet-20240620",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ]
        }
