"""
AI-powered outfit failure analysis using vision.

Analyzes why users didn't save generated outfits by LOOKING at the actual images.
"""

import logging
import os
from typing import Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


VISION_ANALYSIS_PROMPT = """You are an expert fashion stylist. Look at these clothing items that were suggested as an outfit together.

The user did NOT save this outfit. Analyze WHY by actually looking at the garments:

1. **Visual cohesion**: Do these pieces actually work together visually? Colors, patterns, textures?
2. **Layering issues**: If layered, does it make physical sense? (e.g., bulky items under fitted ones?)
3. **Proportions**: Would the silhouette be balanced or awkward?
4. **Style coherence**: Do the pieces belong in the same outfit, or do they clash in style/formality?
5. **Practicality**: Can you actually wear these together? (e.g., two bottoms, incompatible necklines)

Be SPECIFIC about what you SEE. Reference actual visual details from the images.
Keep it to 2-3 sentences. Be direct and critical."""


def get_image_urls(outfit: Dict) -> List[str]:
    """Extract valid image URLs from outfit items."""
    urls = []
    for item in outfit.get("items", []):
        image_path = item.get("image_path", "")
        if image_path and image_path.startswith("http"):
            urls.append(image_path)
    return urls


async def analyze_outfit_failure(
    outfit: Dict,
    user_profile: Optional[Dict] = None,
    occasion: Optional[str] = None,
    model: str = "gpt-4o"
) -> str:
    """
    Analyze why a user might not have saved an outfit by LOOKING at the images.

    Args:
        outfit: The outfit data (items with image_path, styling_notes, why_it_works)
        user_profile: Optional user style profile (current, aspirational, feeling)
        occasion: Optional occasion context
        model: AI model to use (default: gpt-4o for vision)

    Returns:
        Analysis text explaining why the outfit might have failed
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "Analysis unavailable: No API key configured"

        client = OpenAI(api_key=api_key)

        # Get image URLs
        image_urls = get_image_urls(outfit)

        if not image_urls:
            # Fall back to text-only analysis if no images
            return await _analyze_text_only(outfit, user_profile, occasion, client)

        # Build the message content with images
        content = []

        # Add context text first
        context_parts = []

        items = outfit.get("items", [])
        item_names = [item.get("name", "Unknown") for item in items]
        context_parts.append(f"Items in this outfit suggestion: {', '.join(item_names)}")

        styling_notes = outfit.get("styling_notes", "")
        if styling_notes:
            context_parts.append(f"Styling suggestion: \"{styling_notes}\"")

        if occasion:
            context_parts.append(f"Occasion: {occasion}")

        if user_profile:
            current = user_profile.get("current", "")
            aspirational = user_profile.get("aspirational", "")
            if current or aspirational:
                context_parts.append(f"User's style: {current} → {aspirational}")

        context_parts.append("\nLook at these garment images and explain why someone might NOT want to wear them together:")

        content.append({
            "type": "text",
            "text": "\n".join(context_parts)
        })

        # Add each image
        for url in image_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url, "detail": "low"}  # low detail for cost efficiency
            })

        # Call GPT-4o with vision
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": VISION_ANALYSIS_PROMPT},
                {"role": "user", "content": content}
            ],
            max_tokens=300,
            temperature=0.7
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Error analyzing outfit with vision: {e}")
        return f"Analysis unavailable: {str(e)}"


async def _analyze_text_only(
    outfit: Dict,
    user_profile: Optional[Dict],
    occasion: Optional[str],
    client: OpenAI
) -> str:
    """Fallback to text-only analysis when images aren't available."""
    items = outfit.get("items", [])
    styling_notes = outfit.get("styling_notes", "")

    prompt_parts = [
        "Outfit items:",
        *[f"- {item.get('name', 'Unknown')} ({item.get('category', '')})" for item in items],
        f"\nStyling notes: {styling_notes}"
    ]

    if occasion:
        prompt_parts.append(f"Occasion: {occasion}")

    prompt_parts.append("\nWhy might this outfit not work? (Note: no images available)")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a fashion stylist. Briefly explain why this outfit might not work. Be specific. 2-3 sentences max."},
            {"role": "user", "content": "\n".join(prompt_parts)}
        ],
        max_tokens=200,
        temperature=0.7
    )

    return response.choices[0].message.content.strip()


async def analyze_failure_patterns(analyses: List[Dict]) -> str:
    """
    Analyze patterns across multiple outfit failures for a user.

    Args:
        analyses: List of dicts with 'outfit', 'analysis' keys

    Returns:
        Pattern summary text
    """
    if not analyses:
        return "No failure patterns to analyze."

    if len(analyses) < 2:
        return "Not enough data to identify patterns."

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "Pattern analysis unavailable: No API key"

        client = OpenAI(api_key=api_key)

        # Format analyses for pattern detection
        analyses_text = []
        for idx, analysis_item in enumerate(analyses[:5], 1):  # Limit to 5 for cost
            outfit_items = ", ".join(
                itm.get("name", "Unknown")
                for itm in analysis_item.get("outfit", {}).get("items", [])
            )
            analysis_text = analysis_item.get("analysis", "")
            analyses_text.append(f"Outfit {idx}: {outfit_items}\nIssue: {analysis_text}")

        prompt = f"""Here are outfits a user did NOT save, with analysis of each:

{chr(10).join(analyses_text)}

What's the common PATTERN? What types of outfits does this user consistently reject?
1-2 sentences only."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You identify patterns in fashion preferences. Be concise and specific."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.5
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Error analyzing patterns: {e}")
        return "Pattern analysis unavailable."
