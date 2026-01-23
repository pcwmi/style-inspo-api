"""Base classes for prompt templates"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import date
import hashlib
import random


def generate_shuffle_seed(user_id: str, occasion: Optional[str] = None) -> int:
    """Generate deterministic seed for reproducible item shuffling.

    Uses user_id + occasion + today's date so:
    - Same user, same occasion, same day = same shuffle (reproducible for debugging)
    - Different days = different shuffle (reduces position bias over time)
    """
    today = date.today().isoformat()
    seed_string = f"{user_id}:{occasion or 'none'}:{today}"
    return int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)


def shuffle_items_seeded(items: List[Dict], seed: int) -> List[Dict]:
    """Shuffle items using a deterministic seed for reproducibility."""
    shuffled = items.copy()
    random.Random(seed).shuffle(shuffled)
    return shuffled


@dataclass
class PromptContext:
    """All inputs needed to build a styling prompt"""
    user_profile: Dict
    available_items: List[Dict]
    styling_challenges: List[Dict]
    occasion: Optional[str] = None
    weather_condition: Optional[str] = None
    temperature_range: Optional[str] = None
    user_id: Optional[str] = None  # For seeded shuffling to prevent position bias


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
