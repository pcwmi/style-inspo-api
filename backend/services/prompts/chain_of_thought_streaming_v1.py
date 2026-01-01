"""Chain-of-Thought Streaming prompt variant - December 2025
Outputs JSON immediately after each outfit's reasoning for faster first-outfit delivery.

Key difference from chain_of_thought_v1:
- Instead of all JSON at the end after ===JSON OUTPUT===
- Each outfit's JSON appears immediately after its reasoning with ===OUTFIT N JSON===

This enables streaming UX where users see first outfit ~9 seconds earlier.
"""

from .chain_of_thought_v1 import ChainOfThoughtPromptV1
from .base import PromptContext


class ChainOfThoughtStreamingV1(ChainOfThoughtPromptV1):
    """Chain-of-thought prompt with interleaved JSON output for streaming UX

    Validated in streaming_production_comparison.py:
    - First outfit JSON arrives at ~6.7s vs ~16s (9.3s faster)
    - Total time unchanged (~19.5s)
    - Quality equivalent (same constraint compliance, comparable outfit quality)
    """

    @property
    def version(self) -> str:
        return "chain_of_thought_streaming_v1"

    def build(self, context: PromptContext) -> str:
        """Build prompt with interleaved JSON output format"""
        # Get base prompt from parent
        base_prompt = super().build(context)

        # Replace the FINAL OUTPUT section with interleaved format
        old_final_output = """## FINAL OUTPUT

First, show your complete reasoning for all 3 outfits using the format above.

Then, you MUST include this exact line:
===JSON OUTPUT===

After that line, output ONLY the JSON array. No text before or after the JSON."""

        new_final_output = """## FINAL OUTPUT

For EACH outfit, show your reasoning IMMEDIATELY FOLLOWED by that outfit's JSON.

After each outfit's reasoning section, output:
===OUTFIT N JSON===
{"items": [...], "styling_notes": "...", "why_it_works": "..."}

Then continue to the next outfit.

Example flow:
- Outfit 1 reasoning... ===OUTFIT 1 JSON=== {...}
- Outfit 2 reasoning... ===OUTFIT 2 JSON=== {...}
- Outfit 3 reasoning... ===OUTFIT 3 JSON=== {...}

Do NOT batch all JSON at the end. Output each outfit's JSON immediately after its reasoning."""

        prompt = base_prompt.replace(old_final_output, new_final_output)

        # Update the JSON schema section - we're outputting individual objects, not an array
        old_json_schema = """The JSON must:
- Start with [ and end with ]
- Contain exactly 3 outfit objects
- Use exact item names from the wardrobe
- Include all items from each outfit's FINAL OUTFIT list"""

        new_json_schema = """Each JSON object must:
- Use exact item names from the wardrobe
- Include all items from that outfit's FINAL OUTFIT list"""

        prompt = prompt.replace(old_json_schema, new_json_schema)

        # Update the critical reminder at the end
        old_critical = "CRITICAL: You MUST include both the reasoning AND the JSON. Do not stop after the reasoning."
        new_critical = "CRITICAL: Output each outfit's JSON immediately after its reasoning. Do not wait until the end."

        prompt = prompt.replace(old_critical, new_critical)

        return prompt
