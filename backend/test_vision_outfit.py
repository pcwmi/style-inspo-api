"""
Test: Image-based outfit generation with GPT-5.1/5.2 vision

Hypothesis: Sending actual wardrobe images to GPT produces better outfit suggestions
than text metadata, because the model can SEE physical details (ruffled hems, etc.)

Test approach:
1. Load 30 wardrobe items (images + minimal metadata)
2. Send to GPT-5.1 and GPT-5.2 with vision
3. Compare quality, latency, and cost vs current text-based approach
"""

import os
import sys
import time
import json
import base64
import requests
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Models to test
MODELS = ["gpt-5.1", "gpt-5.2"]


def load_wardrobe_sample(user_id: str, limit: int = 30) -> List[Dict]:
    """Load a sample of wardrobe items with image URLs."""
    from services.storage_manager import StorageManager

    storage_type = os.getenv("STORAGE_TYPE", "local")
    storage = StorageManager(storage_type=storage_type, user_id=user_id)

    wardrobe_data = storage.load_json("wardrobe.json")
    if not wardrobe_data:
        print(f"No wardrobe found for user {user_id}")
        return []

    items = wardrobe_data.get("items", [])[:limit]

    # Extract just what we need: image URL + name
    sample = []
    for item in items:
        image_path = item.get("image_path", "")
        name = item.get("styling_details", {}).get("name", "Unknown item")
        category = item.get("styling_details", {}).get("category", "")

        if image_path:
            sample.append({
                "name": name,
                "category": category,
                "image_url": image_path
            })

    return sample


def encode_image_url(url: str) -> Dict:
    """Prepare image for OpenAI vision API."""
    if url.startswith("http"):
        return {
            "type": "image_url",
            "image_url": {
                "url": url,
                "detail": "low"  # 85 tokens per image
            }
        }
    else:
        # Local file - encode as base64
        with open(url, "rb") as f:
            base64_data = base64.b64encode(f.read()).decode("utf-8")
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_data}",
                "detail": "low"
            }
        }


def build_vision_prompt(items: List[Dict], occasion: str) -> List[Dict]:
    """Build a multi-image prompt for outfit generation."""

    # Build content array with text + images
    content = []

    # System context as first text block
    prompt_text = f"""You are a fashion editor creating outfits from this wardrobe.

OCCASION: {occasion}

WARDROBE ITEMS (shown as images below, numbered 1-{len(items)}):
"""

    # Add item list with numbers
    for i, item in enumerate(items, 1):
        prompt_text += f"{i}. {item['name']} ({item['category']})\n"

    prompt_text += """
TASK: Create 3 complete outfits for this occasion.

For each outfit:
1. List the item NUMBERS you're using (e.g., "Items: 3, 7, 12, 15")
2. Explain why these pieces work together (what you SEE in the images)
3. Note any specific styling (tucked, cuffed, layered, etc.)

IMPORTANT: Actually LOOK at the images. Note textures, details, silhouettes.
If an item has ruffles, volume, or structure that affects how it should be styled - mention it.

Output as JSON:
[
  {
    "items": [3, 7, 12, 15],
    "item_names": ["name1", "name2", ...],
    "why_it_works": "Max 200 chars. What you SEE that makes this work.",
    "styling_notes": "Max 150 chars. Non-obvious styling based on what you SEE."
  }
]
"""

    content.append({"type": "text", "text": prompt_text})

    # Add all images
    for item in items:
        try:
            image_content = encode_image_url(item["image_url"])
            content.append(image_content)
        except Exception as e:
            print(f"Warning: Could not load image for {item['name']}: {e}")

    return content


def run_vision_test(model: str, items: List[Dict], occasion: str) -> Dict:
    """Run outfit generation with vision model."""

    print(f"\n{'='*60}")
    print(f"Testing {model} with {len(items)} images")
    print(f"Occasion: {occasion}")
    print(f"{'='*60}")

    content = build_vision_prompt(items, occasion)

    # Count expected tokens
    image_count = len([c for c in content if c["type"] == "image_url"])
    expected_image_tokens = image_count * 85  # low detail
    print(f"Expected image tokens: {expected_image_tokens} ({image_count} images × 85)")

    start_time = time.time()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_completion_tokens=2000,
            temperature=0.7
        )

        latency = time.time() - start_time

        result = {
            "model": model,
            "success": True,
            "latency_seconds": latency,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "response": response.choices[0].message.content,
            "image_count": image_count
        }

        # Calculate cost (gpt-5.1/5.2 pricing)
        input_cost = (response.usage.prompt_tokens / 1_000_000) * 2.50
        output_cost = (response.usage.completion_tokens / 1_000_000) * 10.00
        result["cost_usd"] = input_cost + output_cost

        print(f"\n✅ Success!")
        print(f"Latency: {latency:.1f}s")
        print(f"Tokens: {response.usage.prompt_tokens} in / {response.usage.completion_tokens} out")
        print(f"Cost: ${result['cost_usd']:.4f}")
        print(f"\nResponse:\n{response.choices[0].message.content[:500]}...")

        return result

    except Exception as e:
        latency = time.time() - start_time
        print(f"\n❌ Error: {e}")
        return {
            "model": model,
            "success": False,
            "error": str(e),
            "latency_seconds": latency,
            "image_count": image_count
        }


def main():
    """Run the vision outfit generation test."""

    user_id = "peichin"
    occasion = "casual Friday at a creative office"
    image_limit = 30

    print("="*60)
    print("VISION-BASED OUTFIT GENERATION TEST")
    print("="*60)
    print(f"User: {user_id}")
    print(f"Occasion: {occasion}")
    print(f"Image limit: {image_limit}")

    # Load wardrobe sample
    items = load_wardrobe_sample(user_id, limit=image_limit)
    print(f"\nLoaded {len(items)} wardrobe items")

    if not items:
        print("No items found. Exiting.")
        return

    # Print item summary
    print("\nItems to send:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item['name']} ({item['category']})")

    results = []

    # Test each model
    for model in MODELS:
        result = run_vision_test(model, items, occasion)
        results.append(result)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"\n{status} {r['model']}:")
        print(f"   Latency: {r['latency_seconds']:.1f}s")
        if r["success"]:
            print(f"   Tokens: {r['usage']['prompt_tokens']} in / {r['usage']['completion_tokens']} out")
            print(f"   Cost: ${r['cost_usd']:.4f}")
        else:
            print(f"   Error: {r.get('error', 'Unknown')}")

    # Save results
    output_file = f"vision_test_results_{int(time.time())}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()
