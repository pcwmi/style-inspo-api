#!/usr/bin/env python3
"""Test that baseline_v1 prompt template produces correct structure.

This script verifies the prompt abstraction without needing OpenAI API.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from services.prompts import PromptLibrary, PromptContext

def test_baseline_v1_structure():
    """Test that baseline_v1 produces expected prompt structure."""

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

    print("Testing prompt template system...")
    print(f"\nAvailable prompt versions: {PromptLibrary.list_versions()}")

    # Test baseline_v1
    print("\n" + "="*80)
    print("Testing baseline_v1...")
    print("="*80)

    baseline_prompt = PromptLibrary.get_prompt("baseline_v1")
    context = PromptContext(
        user_profile=user_profile,
        available_items=available_items,
        styling_challenges=styling_challenges,
        occasion="Business meeting",
        weather_condition="Cool",
        temperature_range="50-65°F"
    )

    prompt = baseline_prompt.build(context)

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

    print(f"\nPrompt length: {len(prompt)} characters")
    print(f"\nChecking for required sections:")

    all_present = True
    for section in required_sections:
        present = section in prompt
        status = "✅" if present else "❌"
        print(f"  {status} {section}")
        if not present:
            all_present = False

    # Test fit_constraints_v2
    print("\n" + "="*80)
    print("Testing fit_constraints_v2...")
    print("="*80)

    fit_prompt = PromptLibrary.get_prompt("fit_constraints_v2")
    fit_prompt_text = fit_prompt.build(context)

    fit_required_sections = [
        "GARMENT FIT CONSTRAINTS",
        "LAYERING RULES",
        "Fitted garments CANNOT go over loose/oversized garments",
        "Each layer must be looser",
        "VALIDATION CHECKLIST"
    ]

    print(f"\nPrompt length: {len(fit_prompt_text)} characters")
    print(f"\nChecking for fit constraint sections:")

    fit_all_present = True
    for section in fit_required_sections:
        present = section in fit_prompt_text
        status = "✅" if present else "❌"
        print(f"  {status} {section}")
        if not present:
            fit_all_present = False

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    if all_present and fit_all_present:
        print("✅ All tests passed!")
        print(f"\nbaseline_v1: {len(prompt)} chars")
        print(f"fit_constraints_v2: {len(fit_prompt_text)} chars")
        print(f"Difference: {len(fit_prompt_text) - len(prompt)} chars (fit constraints added)")
        return True
    else:
        print("❌ Some tests failed!")
        if not all_present:
            print("  - baseline_v1 missing required sections")
        if not fit_all_present:
            print("  - fit_constraints_v2 missing required sections")
        return False


if __name__ == "__main__":
    success = test_baseline_v1_structure()
    sys.exit(0 if success else 1)
