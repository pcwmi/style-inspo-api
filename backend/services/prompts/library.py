"""Prompt template registry"""

from typing import Dict, Type
from .base import PromptTemplate
from .baseline_v1 import BaselinePromptV1
from .fit_constraints_v2 import FitConstraintsPromptV2
from .chain_of_thought_v1 import ChainOfThoughtPromptV1
from .chain_of_thought_streaming_v1 import ChainOfThoughtStreamingV1


class PromptLibrary:
    """Registry of all available prompt templates

    Usage:
        prompt = PromptLibrary.get_prompt("baseline_v1")
        context = PromptContext(user_profile={...}, available_items=[...], ...)
        full_prompt = prompt.build(context)
    """

    _PROMPTS: Dict[str, Type[PromptTemplate]] = {
        "baseline_v1": BaselinePromptV1,
        "fit_constraints_v2": FitConstraintsPromptV2,
        "chain_of_thought_v1": ChainOfThoughtPromptV1,
        "chain_of_thought_streaming_v1": ChainOfThoughtStreamingV1,
    }

    @classmethod
    def get_prompt(cls, version: str) -> PromptTemplate:
        """Get prompt template instance by version

        Args:
            version: Prompt version identifier (e.g., 'baseline_v1', 'fit_constraints_v2')

        Returns:
            PromptTemplate instance

        Raises:
            ValueError: If version is not found in registry
        """
        if version not in cls._PROMPTS:
            available = ", ".join(cls._PROMPTS.keys())
            raise ValueError(
                f"Unknown prompt version: '{version}'. "
                f"Available versions: {available}"
            )

        prompt_class = cls._PROMPTS[version]
        return prompt_class()

    @classmethod
    def list_versions(cls) -> list:
        """List all available prompt versions

        Returns:
            List of version strings
        """
        return list(cls._PROMPTS.keys())

    @classmethod
    def register_prompt(cls, version: str, prompt_class: Type[PromptTemplate]) -> None:
        """Register a new prompt template (for extensibility)

        Args:
            version: Version identifier
            prompt_class: PromptTemplate subclass
        """
        if version in cls._PROMPTS:
            raise ValueError(f"Prompt version '{version}' already registered")

        cls._PROMPTS[version] = prompt_class
