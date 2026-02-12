"""Chain-of-Thought with Reasoning prompt variant - January 2026
A/B test variant: Adds explicit reasoning question about physical fit.

Hypothesis: Adding "ask yourself" prompt triggers general reasoning about physical fit,
reducing nonsensical styling suggestions (tucking ruffled shirts, layering bulky knits).
"""

from .chain_of_thought_v1 import ChainOfThoughtPromptV1
from .base import PromptContext


class ChainOfThoughtReasoningV1(ChainOfThoughtPromptV1):
    """Chain-of-thought prompt with added reasoning question about physical fit

    The only change from chain_of_thought_v1 is in STEP 3's physical fit bullet:
    Original: "Work physically together (fabric weights, volumes, construction)"
    Treatment: Adds "Before finalizing, ask yourself: would anything bunch up, create bulk, or feel uncomfortable?"
    """

    @property
    def version(self) -> str:
        return "chain_of_thought_reasoning_v1"

    def build(self, context: PromptContext) -> str:
        """Build the chain-of-thought styling prompt with reasoning addition"""
        # Get the base prompt from parent
        base_prompt = super().build(context)

        # Replace the physical fit bullet with the reasoning variant
        # Original text in STEP 3:
        old_text = "- Work physically together (fabric weights, volumes, construction)"

        # New text with reasoning question:
        new_text = """- Work physically together (fabric weights, volumes, construction)
  Before finalizing, ask yourself: "If I actually styled it this way, would anything bunch up, create bulk, or feel uncomfortable?\""""

        # Apply the replacement
        return base_prompt.replace(old_text, new_text)
