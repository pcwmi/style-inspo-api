"""Chain-of-Thought prompt with explicit weather constraints - January 2026

This variant adds HARD weather constraints to the chain-of-thought prompt.
Designed to test whether explicit prohibitions make the AI respect temperature requirements.

Key changes from chain_of_thought_v1:
1. Adds weather context section with explicit temperature rules
2. Adds weather to STEP 1 (FUNCTION) - must state temperature constraint
3. Adds weather rules in REQUIREMENTS with explicit prohibitions
4. Adds weather check in STEP 8 (FINAL CHECK)
"""

from typing import List, Optional
from .chain_of_thought_v1 import ChainOfThoughtPromptV1
from .base import PromptContext


class ChainOfThoughtWeatherV1(ChainOfThoughtPromptV1):
    """Chain-of-thought prompt with explicit weather constraints"""

    @property
    def version(self) -> str:
        return "chain_of_thought_weather_v1"

    def build(self, context: PromptContext) -> str:
        """Build the chain-of-thought styling prompt with weather constraints"""
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

        # Format weather context
        weather_context = self._format_weather_context(context.weather_condition, context.temperature_range, context.occasion)
        weather_rules = self._format_weather_rules(context.weather_condition, context.temperature_range)
        weather_step1_addition = self._format_weather_step1(context.weather_condition, context.temperature_range)
        weather_final_check = self._format_weather_final_check(context.weather_condition, context.temperature_range)

        prompt = f"""You are a fashion editor styling real people for a "Best Dressed" feature. Your signature is the "unexpected perfect" - outfits that are completely appropriate but have one element that makes people stop and say "I wouldn't have thought of that, but it works."

Safe outfits don't get photographed. Predictable is a failure mode. Your job is to create outfits with a point of view.

---

## USER CONTEXT

Style DNA: {current_style} + {aspirational_style} + wants to feel {feeling}
Occasion: {context.occasion or 'N/A'}
{weather_context}

---

## STYLE DNA PRINCIPLE

All three style words must be present in the final outfit.

The anchor, supporting pieces, and unexpected element should work together to express all three words. This creates natural tension and interest - it's what makes an outfit feel like YOU rather than a costume.

---
{weather_rules}
## AVAILABLE WARDROBE

{self._format_combined_wardrobe(context.available_items, context.styling_challenges)}

---

## OUTFIT CONSTRUCTION PROCESS

For each outfit, think through these steps:

**STEP 1: FUNCTION + WEATHER**
What must this outfit accomplish? Name the ONE primary job.
{weather_step1_addition}

**STEP 2: ANCHOR**
{self._format_anchor_step(has_anchor_items, anchor_items_text, len(context.styling_challenges) if has_anchor_items else None)}

**STEP 3: SUPPORTING PIECES**
Select 2-4 pieces that complete the outfit. These pieces should:
- Support the anchor without competing
- Create at least one intentional contrast (texture, volume, structure)
- Bring in the style words the anchor doesn't carry
- Work physically together (fabric weights, volumes, construction)
- BE APPROPRIATE FOR THE TEMPERATURE (if weather is specified)

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
{weather_final_check}

---

## REQUIREMENTS

1. Create 3 outfits

2. Each outfit MUST have an explicitly named unexpected element

{self._format_anchor_requirement(has_anchor_items, anchor_items_text if has_anchor_items else "", len(context.styling_challenges) if has_anchor_items else None)}

4. No item can appear in more than 2 of the 3 outfits

5. Each outfit must carry ALL THREE style words

6. Each outfit must be COMPLETE - including shoes (REQUIRED) and any finishing touches that elevate it

7. Show reasoning for each step

8. **No two pants in the same outfit**: A person can only wear one pair of pants at a time.

9. **No two shoes in the same outfit**: A person can only wear one pair of shoes at a time.

10. **Bottoms layering rule**: Wearing pants under a skirt is rare and requires specific silhouettes:
    - INVALID: Wide-leg/flared pants under any skirt (too much bulk)
    - INVALID: Any pants under a short/fitted skirt (nowhere for fabric to go)
    - VALID: Skinny jeans or leggings under a long, flowing skirt
    - DEFAULT: One bottom per outfit unless the silhouette works physically

11. **Layering order rule**: Each layer must be looser than the previous:
    - INVALID: Oversized top under fitted sweater (sleeves won't fit)
    - INVALID: Loose blouse under tight cardigan (bunches up)
    - VALID: Fitted tee under oversized cardigan
    - Order: fitted → relaxed → oversized

{self._format_weather_requirement(context.weather_condition, context.temperature_range)}

---
{self._format_critical_anchor_reminder(has_anchor_items, anchor_items_text if has_anchor_items else "", len(context.styling_challenges) if has_anchor_items else None)}
## OUTPUT FORMAT

For each outfit, first show your reasoning:

FUNCTION: [What this outfit needs to accomplish]
WEATHER: [Temperature and how outfit addresses it]

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
WEATHER CHECK: [Confirmation outfit is appropriate for temperature]

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

    def _format_weather_context(self, weather_condition: Optional[str], temperature_range: Optional[str], occasion: Optional[str]) -> str:
        """Format weather context section for USER CONTEXT"""
        if not weather_condition and not temperature_range:
            # Check if occasion text contains temperature info
            if occasion and any(temp_word in occasion.lower() for temp_word in ['degree', '°f', '°c', 'cold', 'freezing', 'chilly', 'cool', 'warm', 'hot']):
                return f"Weather: EXTRACT FROM OCCASION TEXT - look for temperature mentions"
            return ""

        parts = []
        if weather_condition:
            parts.append(weather_condition)
        if temperature_range:
            parts.append(temperature_range)

        return f"Weather: {', '.join(parts)}"

    def _format_weather_rules(self, weather_condition: Optional[str], temperature_range: Optional[str]) -> str:
        """Format hard weather rules section - these are CONSTRAINTS not suggestions"""
        if not weather_condition and not temperature_range:
            return ""

        # Determine temperature category
        temp_category = self._categorize_temperature(temperature_range, weather_condition)

        rules = """
## WEATHER CONSTRAINTS (CRITICAL - MUST FOLLOW)

"""

        if temp_category == "cold":
            rules += """**COLD WEATHER RULES (<50°F / <10°C):**
- REQUIRED: Outfit MUST include at least one warm layer (jacket, coat, cardigan, sweater, or blazer)
- INVALID: Short-sleeve or sleeveless tops as the ONLY upper body piece
- INVALID: Outfit with no warmth layer - this is not weather-appropriate
- VALID: Short-sleeve top WITH a jacket/cardigan/coat layered over it
- VALID: Long-sleeve sweater, knit, or layered outfit
- Fabric preference: Wool, cashmere, heavy cotton, leather, denim

If you suggest a short-sleeve top without a layer for cold weather, the outfit is WRONG.
"""
        elif temp_category == "cool":
            rules += """**COOL WEATHER RULES (50-65°F / 10-18°C):**
- RECOMMENDED: Include a light layer (cardigan, light jacket, blazer) for temperature regulation
- VALID: Long-sleeve pieces without additional layers
- VALID: Short-sleeve with a light layer
- CAUTION: Sleeveless without a layer may be too cold
- Fabric preference: Mid-weight fabrics, light wool, cotton blends

"""
        elif temp_category == "mild":
            rules += """**MILD WEATHER RULES (65-75°F / 18-24°C):**
- Flexible layering - optional light layer for morning/evening
- All sleeve lengths acceptable
- Fabric preference: Mid-weight to lightweight fabrics

"""
        elif temp_category == "warm":
            rules += """**WARM WEATHER RULES (75-85°F / 24-29°C):**
- AVOID heavy layers and thick fabrics
- PREFER lightweight, breathable fabrics (linen, lightweight cotton, silk)
- Short sleeves and sleeveless are ideal
- Keep layering minimal

"""
        elif temp_category == "hot":
            rules += """**HOT WEATHER RULES (>85°F / >29°C):**
- REQUIRED: Lightweight, breathable fabrics only
- INVALID: Wool, heavy denim, leather jackets
- PREFER: Linen, thin cotton, flowy silhouettes
- Minimal layering - keep it simple and breathable

"""

        return rules

    def _format_weather_step1(self, weather_condition: Optional[str], temperature_range: Optional[str]) -> str:
        """Format the weather addition to STEP 1"""
        if not weather_condition and not temperature_range:
            return ""

        temp_category = self._categorize_temperature(temperature_range, weather_condition)

        if temp_category == "cold":
            return """
STATE THE TEMPERATURE: This outfit must work for COLD weather.
REQUIREMENT: I will include a warm layer (jacket/coat/cardigan/sweater)."""
        elif temp_category == "cool":
            return """
STATE THE TEMPERATURE: This outfit must work for COOL weather.
CONSIDERATION: Should include a light layer for temperature regulation."""
        elif temp_category in ["warm", "hot"]:
            return """
STATE THE TEMPERATURE: This outfit must work for WARM/HOT weather.
REQUIREMENT: Keep it lightweight and breathable."""
        else:
            return f"""
STATE THE TEMPERATURE: This outfit must work for {temperature_range or weather_condition}."""

    def _format_weather_final_check(self, weather_condition: Optional[str], temperature_range: Optional[str]) -> str:
        """Format the weather check for STEP 8"""
        if not weather_condition and not temperature_range:
            return ""

        temp_category = self._categorize_temperature(temperature_range, weather_condition)

        if temp_category == "cold":
            return """- Weather: Is there a warm layer included? Would you actually wear this outside in cold weather without freezing?"""
        elif temp_category == "cool":
            return """- Weather: Is there appropriate layering for cool temperatures?"""
        elif temp_category in ["warm", "hot"]:
            return """- Weather: Is this outfit breathable enough for warm weather? No heavy layers?"""
        else:
            return f"""- Weather: Is this outfit appropriate for {temperature_range or weather_condition}?"""

    def _format_weather_requirement(self, weather_condition: Optional[str], temperature_range: Optional[str]) -> str:
        """Format the weather requirement for REQUIREMENTS section"""
        if not weather_condition and not temperature_range:
            return ""

        temp_category = self._categorize_temperature(temperature_range, weather_condition)

        if temp_category == "cold":
            return """12. **COLD WEATHER REQUIREMENT (CRITICAL)**: Every outfit MUST include a warm outer layer (jacket, coat, cardigan, sweater, or blazer). Outfits without adequate warmth for cold weather are INVALID and will be rejected."""
        elif temp_category == "cool":
            return """12. **COOL WEATHER GUIDELINE**: Outfits should include layering options for temperature regulation."""
        elif temp_category in ["warm", "hot"]:
            return """12. **WARM WEATHER REQUIREMENT**: Outfits must be lightweight and breathable. Avoid heavy layers."""
        else:
            return f"""12. **WEATHER APPROPRIATENESS**: Outfit must be appropriate for {temperature_range or weather_condition}."""

    def _categorize_temperature(self, temperature_range: Optional[str], weather_condition: Optional[str]) -> str:
        """Categorize temperature into: cold, cool, mild, warm, hot"""
        combined = f"{temperature_range or ''} {weather_condition or ''}".lower()

        # Check for explicit temperature numbers
        import re
        temp_match = re.search(r'(\d+)', combined)
        if temp_match:
            temp = int(temp_match.group(1))
            # Assume Fahrenheit if no unit specified and temp > 45
            if temp < 50:
                return "cold"
            elif temp < 65:
                return "cool"
            elif temp < 75:
                return "mild"
            elif temp < 85:
                return "warm"
            else:
                return "hot"

        # Check for keywords
        if any(word in combined for word in ['cold', 'freezing', 'frigid', 'icy', 'winter', '<50', 'below 50']):
            return "cold"
        elif any(word in combined for word in ['cool', 'crisp', 'chilly', 'brisk', '50-65', '55-65']):
            return "cool"
        elif any(word in combined for word in ['mild', 'moderate', 'pleasant', '65-75', '60-70']):
            return "mild"
        elif any(word in combined for word in ['warm', 'sunny', '75-85', '70-80']):
            return "warm"
        elif any(word in combined for word in ['hot', 'humid', 'scorching', '85+', '>85', 'above 85']):
            return "hot"

        # Default to mild if can't determine
        return "mild"
