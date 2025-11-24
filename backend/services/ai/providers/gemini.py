"""Google Gemini provider implementation."""

import time
from typing import Optional
import google.generativeai as genai

from .base import AIProvider, AIResponse, AIProviderConfig


class GeminiProvider(AIProvider):
    """Google Gemini provider."""

    def __init__(self, config: AIProviderConfig):
        """Initialize Gemini client."""
        super().__init__(config)
        genai.configure(api_key=config.api_key)
        self.model = genai.GenerativeModel(config.model)

    def _validate_config(self) -> None:
        """Validate Gemini configuration."""
        if not self.config.api_key:
            raise ValueError("Google API key is required")

        # Validate model name
        valid_models = [
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-pro",
            "gemini-pro-vision"
        ]
        if self.config.model not in valid_models:
            raise ValueError(f"Invalid Gemini model: {self.config.model}. Valid models: {valid_models}")

    def generate_text(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AIResponse:
        """Generate text using Gemini."""
        start_time = time.time()

        # Combine system message with prompt if provided
        full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt

        generation_config = genai.types.GenerationConfig(
            temperature=temperature or self.config.temperature,
            max_output_tokens=max_tokens or self.config.max_tokens
        )

        response = self.model.generate_content(
            full_prompt,
            generation_config=generation_config
        )

        latency = time.time() - start_time

        # Extract token usage (if available)
        usage = {
            "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
            "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
            "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0)
        }

        return AIResponse(
            content=response.text,
            model=self.config.model,
            usage=usage,
            latency_seconds=latency,
            raw_response=response
        )

    def analyze_image(
        self,
        image_url: str,
        prompt: str,
        temperature: Optional[float] = None
    ) -> AIResponse:
        """Analyze image using Gemini Vision."""
        start_time = time.time()

        # Download image for Gemini (it requires PIL Image or bytes)
        import requests
        from PIL import Image
        from io import BytesIO

        response_img = requests.get(image_url)
        img = Image.open(BytesIO(response_img.content))

        generation_config = genai.types.GenerationConfig(
            temperature=temperature or self.config.temperature,
            max_output_tokens=self.config.max_tokens
        )

        response = self.model.generate_content(
            [prompt, img],
            generation_config=generation_config
        )

        latency = time.time() - start_time

        usage = {
            "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
            "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
            "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0)
        }

        return AIResponse(
            content=response.text,
            model=self.config.model,
            usage=usage,
            latency_seconds=latency,
            raw_response=response
        )

    @property
    def supports_vision(self) -> bool:
        """Gemini 1.5+ and gemini-pro-vision support vision."""
        return "vision" in self.config.model or "1.5" in self.config.model or "2.0" in self.config.model

    @property
    def provider_name(self) -> str:
        """Provider name."""
        return "google"

    def calculate_cost(self, usage: dict) -> float:
        """
        Calculate cost for Gemini models.
        Pricing as of Nov 2024 (per 1M tokens):
        - Gemini 2.0 Flash: $0.075 input, $0.30 output
        - Gemini 1.5 Pro: $1.25 input, $5.00 output
        - Gemini 1.5 Flash: $0.075 input, $0.30 output
        """
        pricing = {
            "gemini-2.0-flash-exp": {"input": 0.075, "output": 0.30},
            "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
            "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
            "gemini-pro": {"input": 0.50, "output": 1.50},
        }

        model_pricing = pricing.get(self.config.model, {"input": 0, "output": 0})

        input_cost = (usage.get("prompt_tokens", 0) / 1_000_000) * model_pricing["input"]
        output_cost = (usage.get("completion_tokens", 0) / 1_000_000) * model_pricing["output"]

        return input_cost + output_cost
