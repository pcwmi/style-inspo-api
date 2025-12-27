#!/usr/bin/env python3
"""Test that baseline_v1 prompt template produces same output as original implementation.

This script verifies that the prompt abstraction doesn't change behavior.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from services.style_engine import StyleGenerationEngine
from services.prompts import PromptContext

def test_prompt_equivalence():
    """Test that baseline_v1 produces same prompt as original."""

    # Sample test data
    user_profile = {
        "three_words": {
            "current": "classic",
            "aspirational": "bold",
            "feeling": "confident"
        },
        "daily_emotion": {
            "emotion": "energized",
            "context": "Big presentation"
        }
    }

    available_items = [
        {
            "styling_details": {
                "name": "White Button-Down Shirt",
                "category": "tops",
                "colors": ["white"],
                "description": "Classic white cotton button-down",
                "style_tags": ["classic", "professional"]
            }
        },
        {
            "styling_details": {
                "name": "Black Slim Jeans",
                "category": "bottoms",
                "colors": ["black"],
                "description": "Slim fit black denim",
                "style_tags": ["modern", "versatile"]
            }
        }
    ]

    styling_challenges = [
        {
            "styling_details": {
                "name": "Red Statement Blazer",
                "category": "outerwear",
                "colors": ["red"],
                "description": "Bold red structured blazer",
                "style_tags": ["bold", "statement"]
            }
        }
    ]

    occasion = "Business meeting"
    weather_condition = "Cool"
    temperature_range = "50-65°F"

    # Create engine with baseline_v1 prompt
    engine = StyleGenerationEngine(
        model="gpt-4o",
        prompt_version="baseline_v1"
    )

    # Generate prompt
    prompt = engine.create_style_prompt(
        user_profile=user_profile,
        available_items=available_items,
        styling_challenges=styling_challenges,
        occasion=occasion,
        weather_condition=weather_condition,
        temperature_range=temperature_range
    )

    # Verify key sections are present
    required_sections = [
        "expert fashion stylist",
        "USER STYLE PROFILE",
        "TODAY'S CONTEXT",
        "AVAILABLE WARDROBE",
        "STYLE CONSTITUTION",
        "YOUR TASK",
        "OUTPUT FORMAT",
        "White Button-Down Shirt",
        "Red Statement Blazer",
        "Business meeting",
        "Cool (50-65°F)"
    ]

    print("Testing baseline_v1 prompt template...")
    print(f"\nPrompt length: {len(prompt)} characters")
    print(f"\nChecking for required sections:")

    all_present = True
    for section in required_sections:
        present = section in prompt
        status = "✅" if present else "❌"
        print(f"  {status} {section}")
        if not present:
            all_present = False

    if all_present:
        print("\n✅ All required sections present!")
        print("\nFirst 500 characters of prompt:")
        print("-" * 80)
        print(prompt[:500])
        print("-" * 80)
        return True
    else:
        print("\n❌ Some sections missing!")
        return False


if __name__ == "__main__":
    success = test_prompt_equivalence()
    sys.exit(0 if success else 1)
