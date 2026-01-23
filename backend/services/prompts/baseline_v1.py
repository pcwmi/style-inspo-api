"""Baseline Style Constitution prompt (current production version)"""

from typing import List, Optional
from .base import PromptTemplate, PromptContext, generate_shuffle_seed, shuffle_items_seeded


class BaselinePromptV1(PromptTemplate):
    """Original Style Constitution prompt - extracted from style_engine.py"""

    @property
    def version(self) -> str:
        return "baseline_v1"

    @property
    def system_message(self) -> str:
        return "You are an expert fashion stylist. Return ONLY valid JSON arrays, no other text."

    def build(self, context: PromptContext) -> str:
        """Build the complete styling prompt"""
        # Extract user style information
        three_words = context.user_profile.get("three_words", {})
        daily_emotion = context.user_profile.get("daily_emotion", {})

        # Build explicit challenge item list for the prompt
        challenge_item_names = [
            item.get('styling_details', {}).get('name', 'Unknown')
            for item in context.styling_challenges
        ]
        challenge_items_text = ', '.join([f'"{name}"' for name in challenge_item_names])

        # Determine opening statement based on flow type
        if context.occasion or context.weather_condition:
            opening_statement = "Your job is to create outfit combinations that are appropriate for the user's occasion and weather, while honoring their personal style DNA."
        else:
            opening_statement = "Your job is to create outfit combinations that help the user wear pieces they love but struggle to style."

        prompt = f"""
You are an expert fashion stylist inspired by Allison Bornstein's "Wear it Well" methodology. {opening_statement}

## USER STYLE PROFILE
- **Current Style**: {three_words.get('current', 'N/A')}
- **Aspirational Style**: {three_words.get('aspirational', 'N/A')}
- **How They Want to Feel**: {three_words.get('feeling', 'N/A')}

## TODAY'S CONTEXT
{self._format_todays_context(context.occasion, context.weather_condition, context.temperature_range)}

## AVAILABLE WARDROBE
{self._format_combined_wardrobe(context.available_items, context.styling_challenges, context.user_id, context.occasion)}

## STYLE CONSTITUTION: Core Principles for Great Outfits

Apply these principles to create truly exceptional styling:

**Principle 1: Style DNA Alignment**
Every outfit MUST reflect ALL three aspects of the user's style DNA throughout the look.
- Their go-to style is {three_words.get('current', 'N/A')}, and their aspiration is to be {three_words.get('aspirational', 'N/A')}, and they want to feel {three_words.get('feeling', 'N/A')} via this outfit
- Each element should contribute to expressing at least one of these characteristics
- Example: If their go-to style is "classic", their aspiration is to be "bold", and they want to feel "confident", include classic foundations, bold statement pieces, AND styling that creates confidence through intentional details

**Principle 2: Intentional Contrast**
Create visual interest through thoughtful contrast across multiple dimensions:

A. **Proportional Contrast**: Mix fitted with loose, minimal with voluminous
   - Fitted top + wide-leg pants, or oversized sweater + slim jeans
   - Less clothes + bigger accessories (cropped top + oversized bag)
   - wide leg pants + shoes with a sharper toe like almond toe or pointy toe

B. **Wrong Shoe Theory**: Break footwear expectations for surprise
   - Sneakers with dresses instead of heels
   - Western boots with elegant pieces instead of expected casual
   - Dress shoes with jeans instead of sneakers

C. **Textural Contrast**: Combine different textures even in similar colors
   - Smooth leather + soft knit + crisp cotton
   - Structured denim + flowing silk
   - A tonal outfit creates the sense of intentionality and depth. e.g. every item is in similar shade but have different textures.

D. **Expectation Contrast**: Mix styles that don't typically go together
   - Statement + Statement (bold scarf + statement boots)
   - Western + elegant, preppy + grunge
   - Formal pieces in casual settings

**Principle 3: Intentional Details**
Add purposeful styling gestures that demonstrate care:

A. **Layering**: Show underlayers strategically
   - Tee showing beneath sweater
   - Collar peeking from pullover

B. **Repetition**: Repeat colors or textures for visual rhythm
   - Multiple necklaces, stacked belts
   - Echo textures across pieces

C. **Styling Gestures**: Specify deliberate styling techniques
   - Partial tuck (front only)
   - Cuffed sleeves or pant legs
   - Draped belts vs. cinched
   - Unbuttoned elements

## WARDROBE CONSTRAINTS
Before creating outfits, review the available wardrobe items for appropriateness:

- **Weather-Appropriateness Check**: Review items for temperature fit. If wardrobe lacks appropriate items for the temperature (e.g., no mid-weight/heavy fabrics for cool weather, no lightweight fabrics for hot weather), acknowledge this limitation in the `style_opportunity` field and suggest specific missing pieces with fabric type and weight.
- **Occasion-Appropriateness Check**: Review items for occasion fit. If wardrobe lacks pieces that would make the outfit more appropriate for the occasion (e.g., no blazer for business meeting, no structured pieces for formal event), acknowledge this in `style_opportunity` and suggest specific missing pieces.
- **The `style_opportunity` field should be used to address wardrobe gaps that prevent optimal occasion/weather fit**, not just style DNA gaps. Be specific about what's missing and why it matters for the occasion/weather.

**Example**: If generating for "Business meeting" in "Cool (50-65°F)" but wardrobe only has lightweight summer fabrics, `style_opportunity` should say: "A mid-weight blazer or structured cardigan would make this outfit more appropriate for the business meeting and provide warmth for cool weather. Consider a navy or charcoal blazer in wool or cashmere blend."

## YOUR TASK
{self._format_task_instructions(context.occasion, context.weather_condition, context.temperature_range, context.styling_challenges, challenge_item_names, challenge_items_text)}

## OPTIONAL: Style Opportunities
If an outfit would significantly benefit from an item not in their wardrobe to better express their style words, you may suggest it. Be specific:
- What item (category, color, style details like "structured blazer in navy" or "ankle boots with block heel")
- How it would enhance expression of their three style words
- Why it matters for this particular outfit
Only suggest if there's a genuine gap that would meaningfully improve the outfit's ability to express their style DNA - don't force suggestions. If the outfit already fully expresses their style words with available items, omit this field or set to null.

## OUTPUT FORMAT
Return a valid JSON array with 1-3 outfits (generate as many as genuinely work with their style). Each outfit must include:

```json
{{
  "items": ["Item Name 1", "Item Name 2", ...],
  "styling_notes": "Specific instructions: tucking, cuffing, layering, etc. For boots, describe if the pants are tucked inside the boot or outisde.",
  "why_it_works": "MUST explain THREE aspects concisely (keep to 3-4 sentences total): (1) How this outfit is appropriate for the occasion(s) - address each occasion mentioned and why the outfit works for it, (2) How this outfit works for the weather/temperature - explain fabric choices, layering strategy, and temperature appropriateness, (3) How this honors their style DNA and applies Constitution principles. Be punchy and succinct - focus on the key reasons, not exhaustive detail. MUST explain the role of EACH item in the outfit and how it contributes to occasion fit, weather fit, AND overall style.",
  "style_opportunity": "Optional: If wardrobe lacks items needed for optimal occasion/weather fit OR to better express their three style words, suggest specific missing pieces here. Be specific about fabric type and weight for weather gaps (e.g., 'a mid-weight blazer in navy wool' for business meeting in cool weather). Only include if there's a genuine gap - if the outfit already fully works for occasion/weather/style, omit this field or set to null.",
  "constitution_principles": {{
    "style_dna_alignment": "How each style word appears (soft: X, elegant: Y, playful: Z)",
    "intentional_contrast": "Which types used (proportional: X, wrong shoe: Y, textural: Z)",
    "intentional_details": "Specific gestures specified (partial tuck, cuffed sleeves, etc.)"
  }}
}}
```

IMPORTANT: Return ONLY valid JSON. Start with [ and end with ]. Use exact item names from the wardrobe list above.

{self._format_critical_reminder(context.styling_challenges, challenge_item_names, challenge_items_text)}
"""
        return prompt

    def _format_todays_context(self, occasion: Optional[str], weather_condition: Optional[str], temperature_range: Optional[str]) -> str:
        """Format today's context section for the prompt with specific guidance"""
        if not occasion and not weather_condition:
            return "No specific occasion or weather context provided."

        context_parts = []

        # Format occasion with specific guidance
        if occasion:
            # Parse multi-occasion days
            occasions = [o.strip() for o in occasion.split("+")]

            # Determine formality requirements based on occasion keywords
            formality_requirements = []
            if any("business" in o.lower() or "meeting" in o.lower() or "formal" in o.lower() or "event" in o.lower() for o in occasions):
                formality_requirements.append("Business meeting/formal events require business casual or business formal attire (blazer, closed-toe shoes, structured pieces)")

            # Determine transition needs for multi-occasion days
            transition_guidance = ""
            if len(occasions) > 1:
                transition_guidance = f"Outfit must work across multiple occasions: {' → '.join(occasions)}. Prioritize the most formal occasion while ensuring comfort for casual activities."

            context_parts.append(f"- **Occasion**: {occasion}")
            if formality_requirements:
                context_parts.append(f"  - **Formality Requirements**: {formality_requirements[0]}")
            if transition_guidance:
                context_parts.append(f"  - **Transition Needs**: {transition_guidance}")

        # Format weather with specific guidance
        if weather_condition and temperature_range:
            # Parse temperature range
            temp_guidance = ""
            layering_strategy = ""
            fabric_guidance = ""

            if "Cold" in temperature_range or "<50" in temperature_range:
                temp_guidance = "Requires multiple layers (base layer + mid layer + outer layer)"
                layering_strategy = "Include at least one layerable piece (cardigan, blazer, jacket, coat) for warmth"
                fabric_guidance = "Choose mid-weight to heavy fabrics (wool, cashmere, heavy cotton). Avoid lightweight summer fabrics unless layered."
            elif "Cool" in temperature_range or "50-65" in temperature_range:
                temp_guidance = "Requires layering (base layer + mid layer + optional outer layer)"
                layering_strategy = "Include at least one layerable piece (cardigan, blazer, light jacket) for temperature regulation"
                fabric_guidance = "Choose mid-weight fabrics (wool, cashmere, mid-weight cotton). Avoid lightweight summer fabrics (linen, thin cotton) unless layered."
            elif "Mild" in temperature_range or "65-75" in temperature_range:
                temp_guidance = "Comfortable temperature, light layering optional"
                layering_strategy = "Optional light layer (cardigan, light jacket) for morning/evening"
                fabric_guidance = "Mid-weight to lightweight fabrics work well"
            elif "Warm" in temperature_range or "75-85" in temperature_range:
                temp_guidance = "Warm weather, minimal layering"
                layering_strategy = "Light layers only if needed"
                fabric_guidance = "Choose lightweight, breathable fabrics (linen, lightweight cotton, silk)"
            elif "Hot" in temperature_range or "85+" in temperature_range:
                temp_guidance = "Hot weather, avoid heavy layers"
                layering_strategy = "Minimal to no layering"
                fabric_guidance = "Choose lightweight, breathable fabrics (linen, thin cotton, silk). Avoid heavy fabrics."

            context_parts.append(f"- **Weather**: {weather_condition}, {temperature_range}")
            if temp_guidance:
                context_parts.append(f"  - **Temperature Requirements**: {temp_guidance}")
            if fabric_guidance:
                context_parts.append(f"  - **Fabric Guidance**: {fabric_guidance}")
            if layering_strategy:
                context_parts.append(f"  - **Layering Strategy**: {layering_strategy}")
        elif weather_condition:
            context_parts.append(f"- **Weather**: {weather_condition}")
        elif temperature_range:
            context_parts.append(f"- **Temperature**: {temperature_range}")

        return "\n".join(context_parts) if context_parts else "No specific occasion or weather context provided."

    def _format_task_instructions(self, occasion: Optional[str], weather_condition: Optional[str],
                                 temperature_range: Optional[str], styling_challenges: List,
                                 challenge_item_names: List[str], challenge_items_text: str) -> str:
        """Build task instructions dynamically based on whether challenge items, occasion, and weather are provided."""
        # Build task intro
        task_intro = "Create"
        task_steps = []

        # Add occasion/weather context if provided
        if occasion or weather_condition:
            context_parts = []
            if occasion:
                context_parts.append(occasion)
            if weather_condition and temperature_range:
                context_parts.append(f"{weather_condition}, {temperature_range}")
            elif weather_condition:
                context_parts.append(weather_condition)
            task_intro = f"Given today's context ({', '.join(context_parts)}), create"

            # Add appropriateness requirement as #1 (CRITICAL - takes priority)
            occasion_text = occasion if occasion else "the activities"
            weather_text = temperature_range if temperature_range else "the climate"
            occasion_fit_detail = f"Outfit must be appropriate for {occasion_text}" if occasion else ""
            weather_fit_detail = f"Outfit must work for {weather_text} with appropriate layering strategy" if temperature_range else f"Outfit must work for {weather_condition}" if weather_condition else ""

            fit_details = []
            if occasion_fit_detail:
                fit_details.append(f"**Occasion Fit**: {occasion_fit_detail}")
            if weather_fit_detail:
                fit_details.append(f"**Weather Fit**: {weather_fit_detail}")

            fit_detail_text = ". ".join(fit_details) if fit_details else f"Ensure items work for {occasion_text} and {weather_text}"

            task_steps.append(f"1. **MUST be appropriate for the occasion and weather** (CRITICAL - this takes priority over style principles): {fit_detail_text}. If wardrobe lacks appropriate items, acknowledge this in `style_opportunity` field.")

        # Add style DNA requirement (always present, but after occasion/weather if provided)
        step_num = 2 if (occasion or weather_condition) else 1
        task_steps.append(f"{step_num}. **Honor their style DNA** (Principle 1): Ensure all three style words appear in the outfit")

        # Add anchor item requirement (only if anchor items provided)
        if styling_challenges and challenge_item_names:
            next_num = step_num + 1
            anchor_requirement = f"{next_num}. **REQUIRED: Use these anchor pieces**: Every outfit MUST include {challenge_items_text} in the items array. These are the pieces the user wants to wear today - style them in a fresh, wearable way that makes the user feel put-together. Complete the outfit with complementary items from their wardrobe."
            task_steps.append(anchor_requirement)
            next_num = next_num + 1
        else:
            next_num = step_num + 1

        # Add remaining standard requirements (adjust numbering)
        task_steps.append(f"{next_num}. **Apply Intentional Contrast** (Principle 2): Use at least 2 types of contrast per outfit")
        task_steps.append(f"{next_num + 1}. **Add Intentional Details** (Principle 3): Specify concrete styling gestures")
        task_steps.append(f"{next_num + 2}. **No two pants in the same outfit**: A person can only wear one pair of pants at a time.")
        task_steps.append(f"{next_num + 3}. **No two shoes in the same outfit**: A person can only wear one pair of shoes at a time.")
        task_steps.append(f"{next_num + 4}. **Neck space**: Consider visual balance when styling neck area (scarves, necklaces, tops with details)")

        # Assemble final task section
        result = f"{task_intro} 3 outfit combinations that:\n\n"
        result += "\n".join(task_steps)
        return result

    def _format_critical_reminder(self, styling_challenges: List, challenge_item_names: List[str], challenge_items_text: str) -> str:
        """Format critical reminder only if anchor items are required."""
        if styling_challenges and challenge_item_names:
            return f"CRITICAL: Each outfit MUST include {challenge_items_text} (marked \"(ANCHOR PIECE - REQUIRED)\") in the items array. These are the pieces the user wants to wear - use them in every outfit combination and complete the look with complementary items."
        return ""

    def _format_combined_wardrobe(self, available_items: List, styling_challenges: List,
                                   user_id: Optional[str] = None, occasion: Optional[str] = None) -> str:
        """Format combined wardrobe including both regular items and challenge items in a single list.

        Items are shuffled using a seeded random to prevent LLM position bias while maintaining
        reproducibility for debugging. The seed is based on user_id + occasion + today's date.
        """

        def _summarize_item(item: dict) -> str:
            """Create a compact, information-rich summary for a wardrobe item."""
            details = item.get("styling_details") or {}
            usage = item.get("usage_metadata") or {}

            def _first_non_empty(*candidates):
                for candidate in candidates:
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate.strip()
                    if candidate:
                        return candidate
                return None

            category = _first_non_empty(details.get("category"), item.get("category"))
            sub_category = _first_non_empty(details.get("sub_category"), item.get("sub_category"))

            parts: List[str] = []

            if category:
                parts.append(f"category: {category}")
            if sub_category:
                parts.append(f"subcategory: {sub_category}")

            colors = details.get("colors") or item.get("colors")
            if colors:
                if isinstance(colors, (list, tuple)):
                    color_list = [str(c).strip() for c in colors if str(c).strip()]
                    if color_list:
                        parts.append(f"colors: {', '.join(color_list[:3])}")
                elif isinstance(colors, str) and colors.strip():
                    parts.append(f"colors: {colors.strip()}")

            # Add fabric type and weight (important for weather appropriateness)
            fabric_type = _first_non_empty(details.get("fabric_type"), item.get("fabric_type"), details.get("fabric"), item.get("fabric"))
            if fabric_type:
                parts.append(f"fabric: {fabric_type}")

            fabric_weight = _first_non_empty(details.get("fabric_weight"), item.get("fabric_weight"), details.get("weight"), item.get("weight"))
            if fabric_weight:
                parts.append(f"weight: {fabric_weight}")

            # Add design_details (patterns, embellishments) - critical for pattern clash prevention
            design_details = _first_non_empty(details.get("design_details"), item.get("design_details"))
            if design_details and design_details.lower() not in ['none', 'solid/plain', 'n/a', 'not specified']:
                parts.append(f"design: {design_details}")

            key_fields = [
                ("style", details.get("style") or item.get("style")),
                ("fit", details.get("fit") or item.get("fit")),
                ("cut", details.get("cut") or item.get("cut")),
                ("texture", details.get("texture") or item.get("texture")),
            ]

            for label, value in key_fields:
                if value and isinstance(value, str) and value.strip():
                    parts.append(f"{label}: {value.strip()}")
                if len(parts) >= 6:  # increased limit to accommodate fabric info
                    break

            if len(parts) < 6:
                brand = details.get("brand") or item.get("brand")
                if brand and isinstance(brand, str) and brand.strip():
                    parts.append(f"brand: {brand.strip()}")

            notes = details.get("styling_notes") or item.get("styling_notes")
            if notes and isinstance(notes, str):
                cleaned = " ".join(notes.strip().split())
                if cleaned:
                    if len(cleaned) > 140:
                        cleaned = cleaned[:137].rstrip() + "..."
                    parts.append(f"note: {cleaned}")

            # Fallback for legacy description fields
            if not parts:
                description = item.get("description") or details.get("description")
                if description and isinstance(description, str) and description.strip():
                    parts.append(description.strip())

            if not parts:
                return "no details"

            return "; ".join(parts[:8])  # increased to accommodate fabric info

        formatted: List[str] = []

        # Shuffle items to prevent LLM position bias (primacy/recency effects)
        # Use seeded random for reproducibility: same user + occasion + day = same order
        if user_id:
            seed = generate_shuffle_seed(user_id, occasion)
            shuffled_items = shuffle_items_seeded(available_items, seed)
        else:
            # Fallback: no shuffle if user_id not provided (backward compatibility)
            shuffled_items = available_items

        # First add regular wardrobe items (shuffled to prevent position bias)
        for item in shuffled_items:
            details = item.get("styling_details") or {}
            name = details.get("name") or item.get("name") or "Unnamed Piece"
            formatted.append(f"- {name}: {_summarize_item(item)}")

        # Then add anchor items with clear marking (not shuffled - these are user-selected)
        for item in styling_challenges:
            details = item.get("styling_details") or {}
            name = details.get("name") or item.get("name") or "Unnamed Piece"
            formatted.append(
                f"- {name} (ANCHOR PIECE - REQUIRED): {_summarize_item(item)}"
            )

        return "\n".join(formatted)
