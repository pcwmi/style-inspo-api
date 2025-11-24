"""Base class for AI providers."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class AIResponse:
    """Standardized AI response."""
    content: str
    model: str
    usage: Dict[str, int]  # tokens used
    latency_seconds: float
    raw_response: Any = None


@dataclass
class AIProviderConfig:
    """Configuration for AI provider."""
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    api_key: Optional[str] = None


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: AIProviderConfig):
        """Initialize provider with configuration."""
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider configuration (API key, model availability, etc.)."""
        pass

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AIResponse:
        """
        Generate text from prompt.

        Args:
            prompt: User prompt
            system_message: System/instruction message (if supported)
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            AIResponse with generated text and metadata
        """
        pass

    @abstractmethod
    def analyze_image(
        self,
        image_url: str,
        prompt: str,
        temperature: Optional[float] = None
    ) -> AIResponse:
        """
        Analyze image with prompt (vision capability).

        Args:
            image_url: URL to image
            prompt: Analysis prompt
            temperature: Override default temperature

        Returns:
            AIResponse with analysis and metadata
        """
        pass

    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """Whether this provider supports vision/image analysis."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'openai', 'google', 'anthropic')."""
        pass

    def calculate_cost(self, usage: Dict[str, int]) -> float:
        """
        Calculate cost in USD for token usage.
        Override this method to provide accurate pricing.

        Args:
            usage: Dict with 'prompt_tokens' and 'completion_tokens'

        Returns:
            Cost in USD
        """
        # Default: return 0 (override in subclasses with actual pricing)
        return 0.0
