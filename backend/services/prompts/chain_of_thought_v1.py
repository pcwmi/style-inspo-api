"""Chain-of-Thought prompt variant - December 2025
Designed to push models toward creative tail (5-star outputs) through explicit reasoning steps.
"""

from typing import List, Optional
from .base import PromptTemplate, PromptContext
from .baseline_v1 import BaselinePromptV1


class ChainOfThoughtPromptV1(BaselinePromptV1):
    """Chain-of-thought prompt with explicit reasoning steps to avoid 4-star plateau"""

    @property
    def version(self) -> str:
        return "chain_of_thought_v1"

    @property
    def system_message(self) -> str:
        return "You are a fashion editor. Show your reasoning for each step, then return valid JSON."

    def build(self, context: PromptContext) -> str:
        """Build the chain-of-thought styling prompt"""
        # Extract user style information
        three_words = context.user_profile.get("three_words", {})
        current_style = three_words.get('current', 'N/A')
        aspirational_style = three_words.get('aspirational', 'N/A')
        feeling = three_words.get('feeling', 'N/A')

        # Determine if this is complete-my-outfit (has anchor items) or occasion-based
        has_anchor_items = context.styling_challenges and len(context.styling_challenges) > 0

        # Build anchor item text for complete-my-outfit scenarios
        if has_anchor_items:
            anchor_item_names = [
                item.get('styling_details', {}).get('name', 'Unknown')
                for item in context.styling_challenges
            ]
            anchor_items_text = ', '.join([f'"{name}"' for name in anchor_item_names])
        else:
            anchor_items_text = ""

        prompt = f"""You are a fashion editor styling real people for a "Best Dressed" feature. Your signature is the "unexpected perfect" - outfits that are completely appropriate but have one element that makes people stop and say "I wouldn't have thought of that, but it works."

Safe outfits don't get photographed. Predictable is a failure mode. Your job is to create outfits with a point of view.

---

## USER CONTEXT

Style DNA: {current_style} + {aspirational_style} + wants to feel {feeling}
Occasion: {context.occasion or 'N/A'}
Weather: {context.weather_condition or 'N/A'} ({context.temperature_range or 'N/A'})

---

## STYLE DNA PRINCIPLE

All three style words must be present in the final outfit.

The anchor, supporting pieces, and unexpected element should work together to express all three words. This creates natural tension and interest - it's what makes an outfit feel like YOU rather than a costume.

---

## AVAILABLE WARDROBE

{self._format_combined_wardrobe(context.available_items, context.styling_challenges)}

---

## OUTFIT CONSTRUCTION PROCESS

For each outfit, think through these steps:

**STEP 1: FUNCTION**
What must this outfit accomplish? Name the ONE primary job.

**STEP 2: ANCHOR**
{self._format_anchor_step(has_anchor_items, anchor_items_text)}

**STEP 3: SUPPORTING PIECES**
Select 2-4 pieces that complete the outfit. These pieces should:
- Support the anchor without competing
- Create at least one intentional contrast (texture, volume, structure)
- Bring in the style words the anchor doesn't carry
- Work physically together (fabric weights, volumes, construction)

One of these supporting pieces WILL BE your unexpected element (identified in Step 4).

**STEP 4: IDENTIFY THE UNEXPECTED ELEMENT**
From your supporting pieces, identify THE ONE that breaks a conventional expectation.
This is not a separate item - it's highlighting which supporting piece creates the "unexpected perfect" moment.
- What does it break?
- Why does it work anyway?

**STEP 5: STYLE DNA CHECK**
Verify all three words are present. If any is missing, adjust.

**STEP 6: COMPLETE THE LOOK**
This outfit will be photographed head-to-toe. Is it walk-out-the-door ready?

REQUIRED: Every outfit MUST include footwear. No outfit is complete without shoes.

Scan the full silhouette:
- Footwear included? (REQUIRED - must be present)
- Is anything else missing that would make this incomplete?
- Are there finishing opportunities that would elevate without cluttering?

Consider: layers, accessories (belt, jewelry, scarf, bag)

Don't add for the sake of adding. But a half-finished outfit isn't editorial-worthy.

**STEP 7: STORY**
Complete: "This outfit says: I'm someone who ___"

**STEP 8: FINAL CHECK**
- Physical: Can these pieces actually work together?
- Function: Does this accomplish the job from Step 1?

---

## REQUIREMENTS

1. Create 3 outfits

2. Each outfit MUST have an explicitly named unexpected element

{self._format_anchor_requirement(has_anchor_items)}

4. No item can appear in more than 2 of the 3 outfits

5. Each outfit must carry ALL THREE style words

6. Each outfit must be COMPLETE - including shoes (REQUIRED) and any finishing touches that elevate it

7. Show reasoning for each step

---

## OUTPUT FORMAT

For each outfit, first show your reasoning:

FUNCTION: [What this outfit needs to accomplish]

ANCHOR: [Item name]
- Why it's the hero: [One sentence]
- Style words: [Which it carries]

SUPPORTING PIECES:
- [Item]: [How it supports] - carries [style word]
- [Item]: [How it supports] - carries [style word]
- Contrast created: [Texture/volume/structure contrast]

UNEXPECTED ELEMENT: [One of the items listed above]
- Breaks: [Convention]
- Works because: [Resolution]

STYLE DNA: {current_style} ✓ [item] | {aspirational_style} ✓ [item] | {feeling} ✓ [item]

COMPLETING THE LOOK:
- [Any items added to complete the silhouette and why]
- Or: "Core pieces complete the look - no additions needed"
                
STORY: "I'm someone who ___"

PHYSICAL CHECK: [Brief confirmation pieces work together]

FINAL OUTFIT:
- [Item 1]
- [Item 2]
- [Item 3]
- [Item 4 if applicable]
- [etc.]

STYLING: [Concrete details - tucked/untucked, sleeves, etc.]

---

## FINAL OUTPUT

First, show your complete reasoning for all 3 outfits using the format above.

Then, you MUST include this exact line:
===JSON OUTPUT===

After that line, output ONLY the JSON array. No text before or after the JSON.

{self._get_json_schema()}

The JSON must:
- Start with [ and end with ]
- Contain exactly 3 outfit objects
- Use exact item names from the wardrobe
- Include all items from each outfit's FINAL OUTFIT list

CRITICAL: You MUST include both the reasoning AND the JSON. Do not stop after the reasoning.
"""
        return prompt

    def _format_anchor_step(self, has_anchor_items: bool, anchor_items_text: str) -> str:
        """Format STEP 2 based on whether this is complete-my-outfit or occasion-based"""
        if has_anchor_items:
            return f"""The user has selected {anchor_items_text} to wear today. This is your hero piece (or pieces) - style it in a fresh, wearable way that makes the user feel put-together.
Note which style word(s) this piece carries."""
        else:
            return """Select the HERO piece - the one that makes this outfit worth photographing.
Note which style word(s) this piece carries."""

    def _format_anchor_requirement(self, has_anchor_items: bool) -> str:
        """Format REQUIREMENT #3 based on whether this is complete-my-outfit or occasion-based"""
        if has_anchor_items:
            return "3. The anchor item(s) MUST appear in ALL 3 outfits. Style them differently each time to show versatility."
        else:
            return "3. Anchor pieces must be DIFFERENT across all 3 outfits"

    def _get_json_schema(self) -> str:
        """JSON schema for outfit response"""
        return """[
  {
    "items": ["item name 1", "item name 2", ...],
    "styling_notes": "Concrete styling details",
    "why_it_works": "Why this combination succeeds"
  }
]"""
