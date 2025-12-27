"""OpenAI provider implementation."""

import time
from typing import Dict, Optional, Iterator
from openai import OpenAI

from .base import AIProvider, AIResponse, AIProviderConfig


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider."""

    def __init__(self, config: AIProviderConfig):
        """Initialize OpenAI client."""
        super().__init__(config)
        self.client = OpenAI(api_key=config.api_key)

    def _validate_config(self) -> None:
        """Validate OpenAI configuration."""
        if not self.config.api_key:
            raise ValueError("OpenAI API key is required")

        # Validate model name
        valid_models = [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4",
            "gpt-3.5-turbo", "o1", "o1-mini", "o1-preview"
        ]
        if self.config.model not in valid_models:
            raise ValueError(f"Invalid OpenAI model: {self.config.model}. Valid models: {valid_models}")

    def generate_text(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AIResponse:
        """Generate text using OpenAI GPT."""
        start_time = time.time()

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens
        )

        latency = time.time() - start_time

        return AIResponse(
            content=response.choices[0].message.content,
            model=self.config.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            latency_seconds=latency,
            raw_response=response
        )

    def generate_text_stream(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Iterator[str]:
        """
        Stream text generation from OpenAI.

        Yields:
            str: Text chunks as they're generated
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        stream = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            stream=True  # Enable streaming
        )

        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    def analyze_image(
        self,
        image_url: str,
        prompt: str,
        temperature: Optional[float] = None
    ) -> AIResponse:
        """Analyze image using GPT-4 Vision."""
        start_time = time.time()

        # Use vision-capable model
        vision_model = "gpt-4o" if "gpt-4" in self.config.model else self.config.model

        response = self.client.chat.completions.create(
            model=vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            temperature=temperature or self.config.temperature,
            max_tokens=self.config.max_tokens
        )

        latency = time.time() - start_time

        return AIResponse(
            content=response.choices[0].message.content,
            model=vision_model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            latency_seconds=latency,
            raw_response=response
        )

    @property
    def supports_vision(self) -> bool:
        """GPT-4o and GPT-4-turbo support vision."""
        return "gpt-4" in self.config.model

    @property
    def provider_name(self) -> str:
        """Provider name."""
        return "openai"

    def calculate_cost(self, usage: dict) -> float:
        """
        Calculate cost for OpenAI models.
        Pricing as of Nov 2024 (per 1M tokens):
        - GPT-4o: $2.50 input, $10.00 output
        - GPT-4o-mini: $0.15 input, $0.60 output
        - GPT-4-turbo: $10.00 input, $30.00 output
        """
        pricing = {
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-4": {"input": 30.00, "output": 60.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        }

        model_pricing = pricing.get(self.config.model, {"input": 0, "output": 0})

        input_cost = (usage.get("prompt_tokens", 0) / 1_000_000) * model_pricing["input"]
        output_cost = (usage.get("completion_tokens", 0) / 1_000_000) * model_pricing["output"]

        return input_cost + output_cost
