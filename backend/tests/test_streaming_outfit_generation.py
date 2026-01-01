#!/usr/bin/env python3
"""Test the streaming outfit generation implementation"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

load_dotenv()
os.environ['STORAGE_TYPE'] = 's3'

from services.style_engine import StyleGenerationEngine
from services.wardrobe_manager import WardrobeManager


def test_streaming_outfit_generation():
    """Test that streaming generates outfits incrementally"""
    print("=" * 60)
    print("STREAMING OUTFIT GENERATION TEST")
    print("=" * 60)

    # Initialize engine with streaming prompt
    engine = StyleGenerationEngine(
        model="gpt-4o",
        prompt_version="chain_of_thought_streaming_v1",  # Use streaming prompt
        max_tokens=6000
    )

    # Load wardrobe
    print("\nLoading wardrobe for user 'peichin'...")
    wardrobe_manager = WardrobeManager(user_id='peichin')
    wardrobe_items = wardrobe_manager.get_wardrobe_items('all')
    print(f"Loaded {len(wardrobe_items)} items")

    # Prepare user profile
    user_profile = {
        "three_words": {
            "current": "casual",
            "aspirational": "polished",
            "feeling": "chic"
        }
    }

    # Track timing
    start_time = time.time()
    outfit_times = []

    print("\nGenerating outfits with streaming...")
    print("-" * 40)

    outfit_count = 0
    for outfit in engine.generate_outfit_combinations_stream(
        user_profile=user_profile,
        available_items=wardrobe_items,
        styling_challenges=[],
        occasion="casual coffee with friends"
    ):
        outfit_count += 1
        elapsed = time.time() - start_time
        outfit_times.append(elapsed)

        print(f"\n[{elapsed:.2f}s] Outfit {outfit_count} received:")
        print(f"  Items: {outfit.get('items', [])}")
        print(f"  Styling: {outfit.get('styling_notes', 'N/A')[:80]}...")

    total_time = time.time() - start_time

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total outfits: {outfit_count}")
    print(f"Total time: {total_time:.2f}s")
    if outfit_times:
        print(f"First outfit at: {outfit_times[0]:.2f}s")
        if len(outfit_times) > 1:
            print(f"Second outfit at: {outfit_times[1]:.2f}s")
        if len(outfit_times) > 2:
            print(f"Third outfit at: {outfit_times[2]:.2f}s")

    # Validate
    if outfit_count == 3:
        print("\nSUCCESS: All 3 outfits generated")
    else:
        print(f"\nWARNING: Expected 3 outfits, got {outfit_count}")

    if outfit_times and outfit_times[0] < 10:
        print(f"SUCCESS: First outfit arrived fast ({outfit_times[0]:.2f}s < 10s)")
    elif outfit_times:
        print(f"WARNING: First outfit took {outfit_times[0]:.2f}s (expected < 10s)")

    return outfit_count == 3


if __name__ == "__main__":
    test_streaming_outfit_generation()
