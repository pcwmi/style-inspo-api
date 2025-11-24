"""Anthropic Claude provider implementation."""

import time
from typing import Optional
from anthropic import Anthropic

from .base import AIProvider, AIResponse, AIProviderConfig


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, config: AIProviderConfig):
        """Initialize Claude client."""
        super().__init__(config)
        self.client = Anthropic(api_key=config.api_key)

    def _validate_config(self) -> None:
        """Validate Claude configuration."""
        if not self.config.api_key:
            raise ValueError("Anthropic API key is required")

        # Validate model name
        valid_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]
        if self.config.model not in valid_models:
            raise ValueError(f"Invalid Claude model: {self.config.model}. Valid models: {valid_models}")

    def generate_text(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AIResponse:
        """Generate text using Claude."""
        start_time = time.time()

        kwargs = {
            "model": self.config.model,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_message:
            kwargs["system"] = system_message

        response = self.client.messages.create(**kwargs)

        latency = time.time() - start_time

        return AIResponse(
            content=response.content[0].text,
            model=self.config.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            latency_seconds=latency,
            raw_response=response
        )

    def analyze_image(
        self,
        image_url: str,
        prompt: str,
        temperature: Optional[float] = None
    ) -> AIResponse:
        """Analyze image using Claude Vision."""
        start_time = time.time()

        # Download and encode image to base64
        import requests
        import base64

        response_img = requests.get(image_url)
        image_data = base64.b64encode(response_img.content).decode('utf-8')

        # Detect image type from headers
        content_type = response_img.headers.get('content-type', 'image/jpeg')
        media_type = content_type.split('/')[-1]  # jpeg, png, etc.

        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=temperature or self.config.temperature,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": f"image/{media_type}",
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        latency = time.time() - start_time

        return AIResponse(
            content=response.content[0].text,
            model=self.config.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            latency_seconds=latency,
            raw_response=response
        )

    @property
    def supports_vision(self) -> bool:
        """Claude 3+ models support vision."""
        return "claude-3" in self.config.model

    @property
    def provider_name(self) -> str:
        """Provider name."""
        return "anthropic"

    def calculate_cost(self, usage: dict) -> float:
        """
        Calculate cost for Claude models.
        Pricing as of Nov 2024 (per 1M tokens):
        - Claude 3.5 Sonnet: $3.00 input, $15.00 output
        - Claude 3 Opus: $15.00 input, $75.00 output
        - Claude 3 Sonnet: $3.00 input, $15.00 output
        - Claude 3 Haiku: $0.25 input, $1.25 output
        """
        pricing = {
            "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
            "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00},
            "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
            "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        }

        model_pricing = pricing.get(self.config.model, {"input": 0, "output": 0})

        input_cost = (usage.get("prompt_tokens", 0) / 1_000_000) * model_pricing["input"]
        output_cost = (usage.get("completion_tokens", 0) / 1_000_000) * model_pricing["output"]

        return input_cost + output_cost
