"""Vision + Chain-of-Thought prompt - February 2026

Combines chain-of-thought reasoning with vision capabilities.
Fair A/B test: Same CoT structure, but treatment gets images.
"""

from .chain_of_thought_v1 import ChainOfThoughtPromptV1
from .base import PromptContext


class VisionChainOfThoughtV1(ChainOfThoughtPromptV1):
    """Chain-of-thought prompt with vision capabilities.

    Inherits all CoT reasoning from production prompt, adds:
    - requires_images=True to signal style_engine to send images
    - Visual analysis guidance in the prompt
    """

    @property
    def version(self) -> str:
        return "vision_cot_v1"

    @property
    def requires_images(self) -> bool:
        """Signal that this prompt needs images passed to the API."""
        return True

    def build(self, context: PromptContext) -> str:
        """Build CoT prompt with visual analysis guidance."""
        # Get the full production CoT prompt
        base_prompt = super().build(context)

        # Add visual analysis guidance after the opening paragraph
        visual_guidance = """

---

## VISUAL ANALYSIS (You have images of each item)

You can SEE the actual garments. Use your vision to verify:

**Before combining any pieces, LOOK at them:**
- What is the actual fabric weight and texture?
- Is this piece structured or flowy? Fitted or oversized?
- Does it have volume, ruffles, or bulk that affects layering?

**PHYSICAL CHECK using what you SEE:**
- If layering: Look at BOTH pieces. Will the inner one create bulk under the outer?
- If tucking: Look at the hem. Is it bulky, ruffled, or thick? Would tucking create visible bunching?
- If pairing tops: Is there a base layer, or is skin showing where it shouldn't?

**Trust your eyes over the item names.** A "sleeveless knit vest" might be chunky or thin - LOOK at it.

---
"""

        # Insert visual guidance after the first paragraph
        # Find the first "---" separator and insert after it
        first_separator = base_prompt.find("---")
        if first_separator != -1:
            prompt = base_prompt[:first_separator] + visual_guidance + base_prompt[first_separator:]
        else:
            prompt = visual_guidance + base_prompt

        # Enhance the PHYSICAL CHECK step to reference vision
        old_physical = "PHYSICAL CHECK: [Brief confirmation pieces work together]"
        new_physical = "PHYSICAL CHECK: [Based on what you SEE in the images - do these pieces actually layer/fit together?]"
        prompt = prompt.replace(old_physical, new_physical)

        # Enhance Step 8 to use vision
        old_step8 = "**STEP 8: FINAL CHECK**\n- Physical: Can these pieces actually work together?"
        new_step8 = "**STEP 8: FINAL CHECK**\n- Physical: LOOK at the images - can these pieces actually work together? Check bulk, structure, layers."
        prompt = prompt.replace(old_step8, new_step8)

        return prompt
