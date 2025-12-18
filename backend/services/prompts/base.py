"""Base classes for prompt templates"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class PromptContext:
    """All inputs needed to build a styling prompt"""
    user_profile: Dict
    available_items: List[Dict]
    styling_challenges: List[Dict]
    occasion: Optional[str] = None
    weather_condition: Optional[str] = None
    temperature_range: Optional[str] = None


class PromptTemplate(ABC):
    """Base class for all prompt templates"""

    @property
    @abstractmethod
    def version(self) -> str:
        """Prompt version identifier (e.g., 'baseline_v1', 'fit_constraints_v2')"""
        pass

    @property
    @abstractmethod
    def system_message(self) -> str:
        """System message for the AI"""
        pass

    @abstractmethod
    def build(self, context: PromptContext) -> str:
        """Build the full prompt from context"""
        pass
