import json
import os
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

# AI Provider abstraction
from services.ai.factory import AIProviderFactory
from services.ai.providers.base import AIResponse

# Legacy OpenAI imports for backward compatibility
try:
    from openai import OpenAIError, APIError, APIConnectionError, RateLimitError
except ImportError:
    # Fallback for older OpenAI SDK versions
    OpenAIError = Exception
    APIError = Exception
    APIConnectionError = Exception
    RateLimitError = Exception

# Load environment variables
load_dotenv()

@dataclass
class OutfitCombination:
    """Represents a styled outfit combination"""
    items: List[Dict]
    styling_notes: str
    why_it_works: str
    confidence_level: str
    vibe_keywords: List[str]
    constitution_principles: Dict = None  # Track which Constitution principles were applied
    style_opportunity: Optional[str] = None  # Optional suggestion for items not in wardrobe that would enhance the outfit

class StyleGenerationEngine:
    """AI-powered style generation engine"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        """
        Initialize Style Generation Engine.

        Args:
            api_key: Optional API key (if not provided, uses environment variables)
            model: Model to use (default: gpt-4o). Supports OpenAI, Gemini, Claude models.
            temperature: Temperature for generation (default: 0.7)
            max_tokens: Max tokens to generate (default: 2000)
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Create AI provider using factory
        self.ai_provider = AIProviderFactory.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key
        )

    def create_style_prompt(self,
                          user_profile: Dict,
                          available_items: List[Dict],
                          styling_challenges: List[Dict],
                          occasion: Optional[str] = None,
                          weather_condition: Optional[str] = None,
                          temperature_range: Optional[str] = None) -> str:
        """Create the main styling prompt for AI with Style Constitution principles"""

        # Extract user style information
        three_words = user_profile.get("three_words", {})
        daily_emotion = user_profile.get("daily_emotion", {})
        
        # Build explicit challenge item list for the prompt
        challenge_item_names = [item.get('styling_details', {}).get('name', 'Unknown') for item in styling_challenges]
        challenge_items_text = ', '.join([f'"{name}"' for name in challenge_item_names])

        # Determine opening statement based on flow type
        if occasion or weather_condition:
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
{self._format_todays_context(occasion, weather_condition, temperature_range)}

## AVAILABLE WARDROBE
{self._format_combined_wardrobe(available_items, styling_challenges)}

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
{self._format_task_instructions(occasion, weather_condition, temperature_range, styling_challenges, challenge_item_names, challenge_items_text)}

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

{self._format_critical_reminder(styling_challenges, challenge_item_names, challenge_items_text)}
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
                                 temperature_range: Optional[str], styling_challenges: List[Dict],
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

    def _format_critical_reminder(self, styling_challenges: List[Dict], challenge_item_names: List[str], challenge_items_text: str) -> str:
        """Format critical reminder only if anchor items are required."""
        if styling_challenges and challenge_item_names:
            return f"CRITICAL: Each outfit MUST include {challenge_items_text} (marked \"(ANCHOR PIECE - REQUIRED)\") in the items array. These are the pieces the user wants to wear - use them in every outfit combination and complete the look with complementary items."
        return ""

    def _format_combined_wardrobe(self, available_items: List[Dict], styling_challenges: List[Dict]) -> str:
        """Format combined wardrobe including both regular items and challenge items in a single list"""

        def _summarize_item(item: Dict) -> str:
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

        # First add regular wardrobe items
        for item in available_items:
            details = item.get("styling_details") or {}
            name = details.get("name") or item.get("name") or "Unnamed Piece"
            formatted.append(f"- {name}: {_summarize_item(item)}")

        # Then add anchor items with clear marking
        for item in styling_challenges:
            details = item.get("styling_details") or {}
            name = details.get("name") or item.get("name") or "Unnamed Piece"
            formatted.append(
                f"- {name} (ANCHOR PIECE - REQUIRED): {_summarize_item(item)}"
            )

        return "\n".join(formatted)

    def _format_wardrobe_items(self, items: List[Dict]) -> str:
        """Format regular wardrobe items for the prompt with new rich metadata"""
        formatted = []
        for item in items:
            # Build rich description from new fields
            parts = []
            if item.get('colors'):
                parts.append(f"colors: {item['colors']}")
            sub_category = item.get('sub_category') or item.get('styling_details', {}).get('sub_category')
            if sub_category:
                parts.append(f"subcategory: {sub_category}")
            if item.get('texture'):
                parts.append(f"texture: {item['texture']}")
            if item.get('cut'):
                parts.append(f"cut: {item['cut']}")
            if item.get('design_details'):
                parts.append(f"details: {item['design_details']}")
            if item.get('style'):
                parts.append(f"style: {item['style']}")
            if item.get('fit'):
                parts.append(f"fit: {item['fit']}")

            # Fallback to old description field for backward compatibility
            if not parts and item.get('description'):
                parts.append(item['description'])

            description = "; ".join(parts) if parts else "no details"
            formatted.append(f"- {item['styling_details']['name']}: {description}")
        return "\n".join(formatted)

    def _format_styling_challenges(self, items: List[Dict]) -> str:
        """Format styling challenge items for the prompt with new rich metadata"""
        formatted = []
        for item in items:
            # Build rich description from new fields
            parts = []
            if item.get('colors'):
                parts.append(f"colors: {item['colors']}")
            sub_category = item.get('sub_category') or item.get('styling_details', {}).get('sub_category')
            if sub_category:
                parts.append(f"subcategory: {sub_category}")
            if item.get('texture'):
                parts.append(f"texture: {item['texture']}")
            if item.get('cut'):
                parts.append(f"cut: {item['cut']}")
            if item.get('design_details'):
                parts.append(f"details: {item['design_details']}")
            if item.get('style'):
                parts.append(f"style: {item['style']}")
            if item.get('fit'):
                parts.append(f"fit: {item['fit']}")

            # Fallback to old description field for backward compatibility
            if not parts and item.get('description'):
                parts.append(item['description'])

            description = "; ".join(parts) if parts else "no details"
            challenge_reason = item.get('usage_metadata', {}).get('challenge_reason', 'No reason specified')
            formatted.append(f"- {item['styling_details']['name']}: {description} | Challenge: {challenge_reason}")
        return "\n".join(formatted)

    def generate_outfit_combinations(self,
                                   user_profile: Dict,
                                   available_items: List[Dict],
                                   styling_challenges: List[Dict],
                                   num_outfits: int = 3,
                                   occasion: Optional[str] = None,
                                   weather_condition: Optional[str] = None,
                                   temperature_range: Optional[str] = None) -> List[OutfitCombination]:
        """Generate outfit combinations using AI"""

        # If no API key, return empty list with error message
        if not self.client:
            print("⚠️ No OpenAI API key found. Cannot generate outfits.")
            self._safe_stderr_write("⚠️ No OpenAI API key found. Cannot generate outfits.\n\n")
            return []

        prompt = self.create_style_prompt(
            user_profile=user_profile,
            available_items=available_items,
            styling_challenges=styling_challenges,
            occasion=occasion,
            weather_condition=weather_condition,
            temperature_range=temperature_range
        )

        try:
            # DEBUG: Print prompt sent to AI
            self._safe_stderr_write("\n" + "=" * 80 + "\n")
            self._safe_stderr_write("📝 AI PROMPT SENT:\n")
            self._safe_stderr_write("=" * 80 + "\n")
            self._safe_stderr_write(prompt + "\n")
            self._safe_stderr_write("=" * 80 + "\n\n")

            # Call AI provider (supports OpenAI, Gemini, Claude)
            ai_result: AIResponse = self.ai_provider.generate_text(
                prompt=prompt,
                system_message="You are an expert fashion stylist. Return ONLY valid JSON arrays, no other text.",
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            # Parse the AI response
            ai_response = ai_result.content

            # DEBUG: Log provider metadata
            self._safe_stderr_write(f"\n📊 Provider: {self.ai_provider.provider_name} | Model: {ai_result.model}\n")
            self._safe_stderr_write(f"⏱️  Latency: {ai_result.latency_seconds:.2f}s | Tokens: {ai_result.usage.get('total_tokens', 0)}\n")
            cost = self.ai_provider.calculate_cost(ai_result.usage)
            if cost > 0:
                self._safe_stderr_write(f"💰 Cost: ${cost:.4f}\n")

            # DEBUG: Print raw AI response to stderr (so it shows in terminal)
            self._safe_stderr_write("\n" + "="*80 + "\n")
            self._safe_stderr_write("🤖 RAW AI RESPONSE:\n")
            self._safe_stderr_write("="*80 + "\n")
            self._safe_stderr_write(ai_response + "\n")
            self._safe_stderr_write("="*80 + "\n\n")

            # Clean the AI response - remove markdown code blocks if present
            cleaned_response = ai_response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]   # Remove ```
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```
            cleaned_response = cleaned_response.strip()
            
            outfits_data = json.loads(cleaned_response)

            # Handle different response formats
            if isinstance(outfits_data, dict):
                # Single outfit object - wrap in array
                if "items" in outfits_data:
                    outfits_data = [outfits_data]
                # Object with outfits array
                elif "outfits" in outfits_data:
                    outfits_data = outfits_data["outfits"]
                else:
                    # Unknown dict format - try to treat as single outfit
                    outfits_data = [outfits_data]
            elif isinstance(outfits_data, list):
                # Already an array - use as is
                pass
            else:
                # Unexpected format
                outfits_data = []

            # Validate outfit quality
            valid_outfits = []
            for outfit_data in outfits_data:
                # Check if outfit has required fields
                if not (outfit_data.get("items") and
                        len(outfit_data["items"]) >= 2 and
                        outfit_data.get("styling_notes") and
                        outfit_data.get("why_it_works")):
                    continue

                # Match AI item names to actual wardrobe items for validation
                ai_item_names = outfit_data.get("items", [])
                temp_items = []
                for item_name in ai_item_names:
                    matched_item = self._find_item_by_name(item_name, available_items + styling_challenges)
                    if matched_item:
                        temp_items.append(matched_item)

                # Validate outfit structure (no two bottoms, etc.)
                is_valid, error_msg = self._validate_outfit_structure(temp_items)
                if not is_valid:
                    self._safe_stderr_write(f"⚠️  REJECTED outfit: {error_msg}\n")
                    self._safe_stderr_write(f"   Items were: {ai_item_names}\n")
                    continue

                valid_outfits.append(outfit_data)

            # DEBUG: Print structure
            rejected_count = len(outfits_data) - len(valid_outfits)
            if rejected_count > 0:
                self._safe_stderr_write(f"🚫 Rejected {rejected_count} invalid outfit(s)\n")
            self._safe_stderr_write(f"📊 AI returned {len(valid_outfits)} valid outfits\n")

            outfits_data = valid_outfits

            # DEBUG: Print available wardrobe item names
            all_items = available_items + styling_challenges
            self._safe_stderr_write(f"\n👗 AVAILABLE WARDROBE ITEMS ({len(all_items)} total):\n")
            for item in all_items:
                self._safe_stderr_write(f"  - {item.get('styling_details', {}).get('name', 'UNKNOWN')}\n")
            self._safe_stderr_write("\n")

            # Convert AI response to OutfitCombination objects
            combinations = []
            for idx, outfit_data in enumerate(outfits_data):
                self._safe_stderr_write(f"\n🎨 OUTFIT {idx + 1} - AI Item Names:\n")
                
                # Ensure outfit_data is a dictionary
                if not isinstance(outfit_data, dict):
                    self._safe_stderr_write(f"  ❌ SKIPPED outfit {idx + 1} - not a dictionary: {type(outfit_data)}\n")
                    continue
                    
                ai_item_names = outfit_data.get("items", [])
                self._safe_stderr_write(f"  AI wants: {ai_item_names}\n")

                # Find actual wardrobe items by name
                outfit_items = []
                for item_name in ai_item_names:
                    matched_item = self._find_item_by_name(item_name, all_items)
                    if matched_item:
                        self._safe_stderr_write(f"  ✅ Matched '{item_name}' → '{matched_item.get('styling_details', {}).get('name', 'UNKNOWN')}'\n")
                        outfit_items.append(matched_item)
                    else:
                        self._safe_stderr_write(f"  ❌ FAILED to match '{item_name}'\n")

                if outfit_items:
                    # Validate that anchor items are included when styling_challenges is provided
                    if styling_challenges:
                        anchor_item_ids = {item.get('id') for item in styling_challenges if item.get('id')}
                        outfit_item_ids = {item.get('id') for item in outfit_items if item.get('id')}
                        
                        # Check if all anchor items are in the outfit (for multi-select)
                        has_all_anchors = anchor_item_ids.issubset(outfit_item_ids)
                        
                        if not has_all_anchors:
                            missing = anchor_item_ids - outfit_item_ids
                            self._safe_stderr_write(f"  → ❌ SKIPPED outfit {idx + 1}: Missing anchor item(s) (required in 'Complete My Look' flow)\n")
                            self._safe_stderr_write(f"     Anchor item IDs: {anchor_item_ids}\n")
                            self._safe_stderr_write(f"     Missing IDs: {missing}\n")
                            self._safe_stderr_write(f"     Outfit item IDs: {outfit_item_ids}\n")
                            continue
                        else:
                            matched_anchors = [item for item in styling_challenges if item.get('id') in outfit_item_ids]
                            anchor_names = [item.get('styling_details', {}).get('name', 'UNKNOWN') for item in matched_anchors]
                            self._safe_stderr_write(f"  ✅ All anchor items included: {anchor_names}\n")
                    
                    self._safe_stderr_write(f"  → Created outfit with {len(outfit_items)} items\n")
                    combinations.append(OutfitCombination(
                        items=outfit_items,
                        styling_notes=outfit_data.get("styling_notes", ""),
                        why_it_works=outfit_data.get("why_it_works", ""),
                        confidence_level=outfit_data.get("confidence_level", "Gentle Push"),
                        vibe_keywords=outfit_data.get("vibe", []),
                        constitution_principles=outfit_data.get("constitution_principles", {}),
                        style_opportunity=outfit_data.get("style_opportunity") or None
                    ))
                else:
                    self._safe_stderr_write(f"  → ⚠️ SKIPPED outfit (no items matched)\n")

            self._safe_stderr_write(f"\n✨ FINAL RESULT: {len(combinations)} outfits created from AI\n")
            if not combinations:
                self._safe_stderr_write("⚠️ No valid outfits generated from AI - returning empty list\n\n")

            return combinations

        except json.JSONDecodeError as e:
            error_details = f"JSON parsing error: {str(e)}\n"
            error_details += f"Failed to parse AI response as JSON. Response may be malformed.\n"
            self._safe_stderr_write(error_details)
            print(f"⚠️ JSON parsing error: {e}")
            return []
        
        except RateLimitError as e:
            error_details = f"OpenAI Rate Limit Error:\n"
            error_details += f"  Message: {str(e)}\n"
            if hasattr(e, 'status_code'):
                error_details += f"  Status Code: {e.status_code}\n"
            if hasattr(e, 'response') and e.response:
                if hasattr(e.response, 'status_code'):
                    error_details += f"  HTTP Status: {e.response.status_code}\n"
                if hasattr(e.response, 'text'):
                    error_details += f"  Response Text: {e.response.text[:500]}\n"
            error_details += "  Please wait a moment and try again.\n"
            self._safe_stderr_write(error_details)
            print(f"⚠️ OpenAI rate limit error: {e}")
            return []
        
        except APIConnectionError as e:
            error_details = f"OpenAI API Connection Error:\n"
            error_details += f"  Message: {str(e)}\n"
            if hasattr(e, 'message'):
                error_details += f"  Details: {e.message}\n"
            error_details += "  Check your internet connection and try again.\n"
            self._safe_stderr_write(error_details)
            print(f"⚠️ OpenAI connection error: {e}")
            return []
        
        except (APIError, OpenAIError) as e:
            error_details = f"OpenAI API Error:\n"
            error_details += f"  Error Type: {type(e).__name__}\n"
            error_details += f"  Message: {str(e)}\n"
            
            # Extract status code
            if hasattr(e, 'status_code'):
                error_details += f"  Status Code: {e.status_code}\n"
            elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                error_details += f"  HTTP Status Code: {e.response.status_code}\n"
            
            # Extract error message/details
            if hasattr(e, 'message'):
                error_details += f"  Error Message: {e.message}\n"
            if hasattr(e, 'code'):
                error_details += f"  Error Code: {e.code}\n"
            if hasattr(e, 'body'):
                try:
                    if isinstance(e.body, dict):
                        error_details += f"  Error Body: {json.dumps(e.body, indent=2)}\n"
                    else:
                        error_details += f"  Error Body: {str(e.body)[:500]}\n"
                except:
                    pass
            
            # Extract response details
            if hasattr(e, 'response') and e.response:
                try:
                    if hasattr(e.response, 'json'):
                        error_body = e.response.json()
                        error_details += f"  Response JSON: {json.dumps(error_body, indent=2)}\n"
                    elif hasattr(e.response, 'text'):
                        error_details += f"  Response Text: {e.response.text[:500]}\n"
                except Exception as parse_err:
                    error_details += f"  Could not parse response: {parse_err}\n"
            
            self._safe_stderr_write(error_details)
            print(f"⚠️ OpenAI API error ({type(e).__name__}): {e}")
            return []
        
        except Exception as e:
            error_details = f"Unexpected Error:\n"
            error_details += f"  Error Type: {type(e).__name__}\n"
            error_details += f"  Message: {str(e)}\n"
            error_details += f"  Full traceback available in console\n"
            self._safe_stderr_write(error_details)
            print(f"⚠️ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _safe_stderr_write(self, message: str):
        """Safely write to stderr, handling BrokenPipeError gracefully"""
        try:
            sys.stderr.write(message)
            sys.stderr.flush()
        except BrokenPipeError:
            # Streamlit may redirect stderr, causing broken pipe
            # Just print to stdout as fallback
            print(message, end='')
        except Exception:
            # If all else fails, silently ignore (don't break the flow)
            pass

    def _validate_outfit_structure(self, outfit_items: List[Dict]) -> Tuple[bool, str]:
        """
        Validate outfit has valid structure (no duplicate bottoms, has essential pieces, etc.)

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not outfit_items or len(outfit_items) < 2:
            return False, "Outfit needs at least 2 items"

        # Extract categories from items
        categories = []
        for item in outfit_items:
            details = item.get('styling_details', {})
            category = details.get('category', '').lower()
            if category:
                categories.append(category)

        # Count bottom pieces (bottoms and dresses both count as bottoms)
        bottom_categories = ['bottoms', 'dresses']
        bottom_count = sum(1 for cat in categories if cat in bottom_categories)

        # Rule 1: Can't have more than 1 bottom (either pants OR dress, not both)
        if bottom_count > 1:
            return False, "Outfit has multiple bottoms (can only wear one pair of pants or one dress at a time)"

        # Rule 2: Must have at least 1 bottom
        if bottom_count == 0:
            return False, "Outfit is missing a bottom (needs pants, skirt, or dress)"

        # Rule 3: Can't have more than 1 pair of shoes
        shoe_categories = ['shoes', 'footwear']
        shoe_count = sum(1 for cat in categories if cat in shoe_categories)
        if shoe_count > 1:
            return False, "Outfit has multiple shoes (can only wear one pair of shoes at a time)"

        # Rule 4: Check for excessive tops/outerwear (allow max 3 for layering)
        # Count both tops and outerwear since outerwear (blazers, cardigans, jackets) are layered on top
        #top_count = sum(1 for cat in categories if cat in ['tops', 'outerwear'])
        #if top_count > 3:
        #    return False, f"Too many tops/outerwear ({top_count}) - maximum 3 for layering"

        return True, "Valid outfit structure"

    def _find_item_by_name(self, item_name: str, all_items: List[Dict]) -> Optional[Dict]:
        """Find a wardrobe item by name (fuzzy matching)"""
        item_name_lower = item_name.lower()

        # First try exact match
        for item in all_items:
            if item.get('styling_details', {}).get('name', '').lower() == item_name_lower:
                return item

        # Then try partial match
        for item in all_items:
            wardrobe_name = item.get('styling_details', {}).get('name', '').lower()
            if item_name_lower in wardrobe_name or wardrobe_name in item_name_lower:
                return item

        return None

    def _generate_mock_combinations(self,
                                  user_profile: Dict,
                                  regular_wear: List[Dict],
                                  styling_challenges: List[Dict]) -> List[OutfitCombination]:
        """Generate mock outfit combinations but use real wardrobe photos when available"""

        # Helper function to find matching wardrobe items for thumbnails
        def find_wardrobe_item(name_pattern: str, all_items: List[Dict]) -> Dict:
            pattern_words = name_pattern.lower().split()
            for item in all_items:
                # Prefer structured name if available
                item_name = (
                    item.get('styling_details', {}).get('name')
                    or item.get('name', '')
                ).lower()
                if item_name and any(word in item_name for word in pattern_words):
                    return item
            # Return mock item if not found (no photo available in this case)
            return {"name": name_pattern, "category": "unknown"}

        # Combine all wardrobe items for searching
        all_wardrobe_items = regular_wear + styling_challenges

        def fill_min_items(items: List[Dict], pool: List[Dict], minimum: int = 3) -> List[Dict]:
            """Ensure a minimum number of items by topping up with available wardrobe pieces."""
            result = [i for i in items if isinstance(i, dict)]
            seen_ids = {i.get('id') for i in result if i.get('id')}
            for it in pool:
                if len(result) >= minimum:
                    break
                if it.get('id') and it.get('id') in seen_ids:
                    continue
                result.append(it)
                if it.get('id'):
                    seen_ids.add(it['id'])
            return result

        def ensure_challenge_item_included(items: List[Dict]) -> List[Dict]:
            """Ensure at least one challenge item is included when styling_challenges is provided."""
            if not styling_challenges:
                return items
            
            challenge_item_ids = {item.get('id') for item in styling_challenges if item.get('id')}
            outfit_item_ids = {item.get('id') for item in items if item.get('id')}
            
            # If no challenge item is present, add the first one
            if not (challenge_item_ids & outfit_item_ids):
                # Add the first challenge item to the outfit (check by ID to avoid duplicates)
                challenge_to_add = styling_challenges[0]
                challenge_id = challenge_to_add.get('id')
                if challenge_id and not any(item.get('id') == challenge_id for item in items):
                    items.insert(0, challenge_to_add)
            
            return items

        # Mock combination 1: Cowboy boots + soft pieces
        # Try to find items matching patterns, but prioritize actual challenge items
        combo1_items = [
            find_wardrobe_item("white t-shirt", all_wardrobe_items),
            find_wardrobe_item("light wash jeans", all_wardrobe_items),
            find_wardrobe_item("white cowboy", all_wardrobe_items),
            find_wardrobe_item("brown belt", all_wardrobe_items),
        ]
        combo1_items = fill_min_items(combo1_items, all_wardrobe_items, minimum=3)
        # Ensure challenge item is included
        combo1_items = ensure_challenge_item_included(combo1_items)
        combo1 = OutfitCombination(
            items=combo1_items,
            styling_notes="Tuck the white tee into the jeans and add the brown belt to define your waist. The light wash jeans keep the cowboy boots feeling casual and approachable rather than costume-y.",
            why_it_works="This grounds your challenging white cowboy boots with your most comfortable pieces (white tee + light jeans). The western boots add the 'playful' element you're seeking while staying true to your soft, elegant foundation.",
            confidence_level="Gentle Push",
            vibe_keywords=["casual-cool", "western-chic", "approachable"]
        )

        # Mock combination 2: Plaid skirt with elevated casual
        combo2_items = [
            find_wardrobe_item("white t-shirt", all_wardrobe_items),
            find_wardrobe_item("plaid", all_wardrobe_items),
            find_wardrobe_item("denim jacket", all_wardrobe_items),
            find_wardrobe_item("sneaker", all_wardrobe_items),
        ]
        combo2_items = fill_min_items(combo2_items, all_wardrobe_items, minimum=3)
        # Ensure challenge item is included
        combo2_items = ensure_challenge_item_included(combo2_items)
        combo2 = OutfitCombination(
            items=combo2_items,
            styling_notes="Pair the plaid skirt with your most casual pieces to avoid the schoolgirl effect. The denim jacket adds structure while the sneakers keep it grounded and fun.",
            why_it_works="The plaid pattern brings your aspirational 'playful' energy, but pairing it with your go-to white tee and sneakers keeps it feeling authentically you. The cropped jacket adds the perfect casual-cool balance.",
            confidence_level="Comfort Zone",
            vibe_keywords=["preppy-casual", "fun", "accessible"]
        )

        # Mock combination 3: Green dress styled down
        combo3_items = [
            find_wardrobe_item("green", all_wardrobe_items),
            find_wardrobe_item("denim jacket", all_wardrobe_items),
            find_wardrobe_item("sneaker", all_wardrobe_items),
        ]
        combo3_items = fill_min_items(combo3_items, all_wardrobe_items, minimum=3)
        # Ensure challenge item is included
        combo3_items = ensure_challenge_item_included(combo3_items)
        combo3 = OutfitCombination(
            items=combo3_items,
            styling_notes="Style the dress down with your cropped denim jacket and sneakers. This casual layering makes the dress feel like everyday wear rather than special occasion.",
            why_it_works="Your elegant dress gets a playful, casual twist with the denim and sneakers. This combination honors your soft, elegant nature while pushing toward the fun, playful energy you want to feel.",
            confidence_level="Bold Move",
            vibe_keywords=["dress-down", "unexpected", "effortless"]
        )

        return [combo1, combo2, combo3]

    def explain_styling_philosophy(self, user_profile: Dict) -> str:
        """Explain the styling approach for this user"""
        three_words = user_profile.get("three_words", {})
        daily_emotion = user_profile.get("daily_emotion", {})

        return f"""
        ## Your Styling Philosophy

        **Foundation**: Your go-to style is {three_words.get('current', '')},
        which means you're drawn to pieces that reflect this aesthetic.

        **Aspiration**: You want to incorporate {three_words.get('aspirational', '')} elements,
        which adds new dimensions to your looks.

        **Feeling Goal**: You want to feel {three_words.get('feeling', 'good')} in your outfits,
        which guides how we style pieces to create that emotional experience.

        **Today's Focus**: Since you want to feel {daily_emotion.get('want_to_feel', 'good')},
        we're focusing on combinations that boost your mood while staying true to your style DNA.

        **Strategy**: Use your most comfortable pieces as anchors when incorporating challenging items.
        This keeps outfits feeling authentically "you" while gently expanding your comfort zone.
        """