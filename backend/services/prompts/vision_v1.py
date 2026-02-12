"""Vision-informed outfit generation prompt (Feb 2026 A/B test)

This prompt is designed to work with images sent alongside text.
The StyleGenerationEngine will detect `requires_images=True` and send
wardrobe item images to the vision API.

Hypothesis: Vision-informed generation produces fewer physically
nonsensical outfits (ruffled tucking, impossible layering) because
the model can SEE garment details.

FAIR TEST: This prompt includes the SAME metadata as baseline_v1,
PLUS images. This isolates the variable: "Do images add value beyond text?"
"""

from typing import List, Optional
from .base import PromptTemplate, PromptContext, generate_shuffle_seed, shuffle_items_seeded


class VisionPromptV1(PromptTemplate):
    """Vision-informed prompt that includes wardrobe images.

    Key differences from baseline_v1:
    - requires_images=True signals style_engine to send images
    - Visual analysis guidance added to prompt
    - Emphasizes looking at actual garment details
    - SAME metadata as baseline_v1 for fair comparison
    """

    @property
    def version(self) -> str:
        return "vision_v1"

    @property
    def requires_images(self) -> bool:
        """Signal that this prompt needs images passed to the API."""
        return True

    @property
    def system_message(self) -> str:
        return "You are an expert fashion stylist with access to wardrobe images. Analyze visual details (textures, silhouettes, construction) to create physically sensible outfits. Return ONLY valid JSON arrays."

    def _summarize_item(self, item: dict) -> str:
        """Create a compact, information-rich summary for a wardrobe item.

        Same logic as baseline_v1 for fair comparison.
        """
        details = item.get("styling_details") or {}

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

        # Design details (patterns, embellishments) - critical for vision to verify
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
            if len(parts) >= 6:
                break

        notes = details.get("styling_notes") or item.get("styling_notes")
        if notes and isinstance(notes, str):
            cleaned = " ".join(notes.strip().split())
            if cleaned:
                if len(cleaned) > 100:
                    cleaned = cleaned[:97].rstrip() + "..."
                parts.append(f"note: {cleaned}")

        if not parts:
            return "no details"

        return "; ".join(parts[:7])

    def build(self, context: PromptContext) -> str:
        """Build the vision-informed styling prompt."""
        # Extract user style information
        three_words = context.user_profile.get("three_words", {})

        # Build item reference list (numbered to match images)
        items_with_images = context.available_items + context.styling_challenges

        # Shuffle items to prevent position bias
        if context.user_id:
            seed = generate_shuffle_seed(context.user_id, context.occasion)
            items_with_images = shuffle_items_seeded(items_with_images, seed)

        # Build numbered item list WITH FULL METADATA (same as baseline_v1)
        item_list = []
        for i, item in enumerate(items_with_images, 1):
            name = item.get('styling_details', {}).get('name', 'Unknown')
            summary = self._summarize_item(item)
            is_anchor = item in context.styling_challenges
            anchor_tag = " (ANCHOR - MUST INCLUDE)" if is_anchor else ""
            item_list.append(f"{i}. {name}{anchor_tag}: {summary}")

        items_text = "\n".join(item_list)

        # Build challenge items text
        challenge_item_names = [
            item.get('styling_details', {}).get('name', 'Unknown')
            for item in context.styling_challenges
        ]
        challenge_items_text = ', '.join([f'"{name}"' for name in challenge_item_names])

        prompt = f"""You are an expert fashion stylist with access to wardrobe images. Your job is to create outfit combinations that are physically sensible and honor the user's style DNA.

## VISUAL ANALYSIS GUIDANCE

You have access to images of each wardrobe item (shown below, numbered to match the list).

**USE YOUR VISION to analyze:**
- Actual fabric textures (is it stiff, flowy, bulky, structured?)
- Garment construction (ruffles, pleats, volume, tailoring)
- Real colors and patterns (not just what the name says)
- Silhouette and fit (fitted, oversized, cropped, long)
- Details that affect styling (high necklines, wide hems, delicate fabrics)

**CRITICAL - Avoid physically impossible combinations:**
- DON'T tuck bulky/ruffled items (creates visible bunching)
- DON'T layer oversized under fitted (proportions break)
- DON'T combine two bottoms that can't physically layer
- DON'T suggest styling that the garment's construction prevents

## USER STYLE PROFILE
- **Current Style**: {three_words.get('current', 'N/A')}
- **Aspirational Style**: {three_words.get('aspirational', 'N/A')}
- **How They Want to Feel**: {three_words.get('feeling', 'N/A')}

## TODAY'S CONTEXT
{self._format_context(context.occasion, context.weather_condition, context.temperature_range)}

## WARDROBE ITEMS (images shown below, numbered)
{items_text}

## YOUR TASK
Create 3 complete outfits using items from the wardrobe above.

{"**IMPORTANT**: Each outfit MUST include at least one of these anchor items: " + challenge_items_text if challenge_item_names else ""}

For each outfit:
1. Select items that work PHYSICALLY together (based on what you SEE in the images)
2. Ensure the combination honors their style DNA
3. Provide specific styling notes based on actual garment details you observe

## OUTPUT FORMAT
Return a valid JSON array. Each outfit must include:

```json
{{
  "items": ["Item Name 1", "Item Name 2", ...],
  "styling_notes": "Specific instructions based on what you SEE: e.g., 'Leave the ruffled hem untucked to avoid bunching' or 'The structured blazer balances the flowy skirt'",
  "why_it_works": "Reference VISUAL details: what you see in the fabrics, silhouettes, and construction that makes this work physically and stylistically.",
  "constitution_principles": {{
    "style_dna_alignment": "How this honors their three words",
    "intentional_contrast": "Visual contrasts you observe (texture, proportion, etc.)",
    "physical_sensibility": "Why these items work together physically (based on what you SEE)"
  }}
}}
```

IMPORTANT: Return ONLY valid JSON. Start with [ and end with ]. Use exact item names from the list above.

## CRITICAL REMINDERS
- LOOK at the images - don't just read the names
- If an item has ruffles, volume, or structure that affects styling, mention it
- Avoid suggesting styling that would look awkward in real life
- {"EVERY outfit must include at least one anchor item: " + challenge_items_text if challenge_item_names else "Create outfits that best express their style DNA"}
"""
        return prompt

    def _format_context(self, occasion: Optional[str], weather_condition: Optional[str], temperature_range: Optional[str]) -> str:
        """Format occasion/weather context."""
        if not occasion and not weather_condition:
            return "No specific occasion or weather context provided."

        parts = []
        if occasion:
            parts.append(f"- **Occasion**: {occasion}")
        if weather_condition and temperature_range:
            parts.append(f"- **Weather**: {weather_condition}, {temperature_range}")
        elif weather_condition:
            parts.append(f"- **Weather**: {weather_condition}")

        return "\n".join(parts)
