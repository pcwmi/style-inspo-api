#!/usr/bin/env python3
"""
Local Agent Test Script

Run the styling agent without SMS/WhatsApp.
Uses MockOutput to capture what would be sent.

Usage:
    cd backend
    python test_agent_local.py "What should I wear to brunch?"
    python test_agent_local.py "How can I style this better?" --with-photo
"""

import os
import sys
import argparse
import logging

# Setup path and env
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


def run_test(
    message: str,
    user_id: str = "peichin",
    with_context: bool = True,
    with_photo: bool = False,
    provider: str = "openai"
):
    """Run the agent with a test message."""
    from agent.agent import StylingAgent
    from agent.output import MockOutput

    # Build conversation context (simulating multi-turn SMS)
    conversation_context = {}
    if with_context:
        conversation_context = {
            "last_outfit": {
                "items": [
                    {"name": "Grey cashmere crewneck sweater"},
                    {"name": "Black wide-leg trousers"},
                    {"name": "Black patent leather loafers"}
                ],
                "styling_notes": "The magic: The unexpected loafer grounds the feminine sweater."
            },
            "outfit_history": [
                {
                    "items": [
                        {"name": "White button-up shirt"},
                        {"name": "High-waisted jeans"},
                        {"name": "Brown suede ankle boots"}
                    ]
                }
            ],
            "messages": [
                {"role": "user", "content": "What should I wear to work today?"},
                {"role": "assistant", "content": "Here's a polished look with your grey sweater..."},
                {"role": "user", "content": "I like it but can we try different shoes?"},
            ],
            "image_descriptions": [],
            # TODO: Add synthesized_preferences when implemented
            # "synthesized_preferences": {
            #     "style_words": ["classic", "playful", "relaxed"],
            #     "likes": ["high-low mixing", "one polished element"],
            #     "avoids": ["costume-y vibes", "too-matched looks"],
            #     "style_dna": "Classic with playful unexpected edits"
            # }
        }

    # Create mock output to capture what agent sends
    output = MockOutput()

    # Create agent
    agent = StylingAgent(
        user_id=user_id,
        provider=provider,
        output=output,
        conversation_context=conversation_context
    )

    # Show what context we're passing
    print("\n" + "="*60)
    print("CONTEXT BEING PASSED TO AGENT:")
    print("="*60)
    prefix = agent._build_context_prefix()
    if prefix:
        print(prefix)
    else:
        print("(no context)")
    print("="*60 + "\n")

    # Run agent
    print(f"USER MESSAGE: {message}")
    print("-"*60)

    image_urls = None
    if with_photo:
        # Use a test image URL (user's wardrobe item as stand-in for "what they're wearing")
        from services.wardrobe_manager import WardrobeManager
        wm = WardrobeManager(user_id=user_id)
        items = wm.get_wardrobe_items(filter_type="all")
        if items:
            # Find first item with an image
            for item in items:
                url = item.get("system_metadata", {}).get("image_url")
                if url:
                    image_urls = [url]
                    print(f"(Including test image: {url[:50]}...)")
                    break
            if not image_urls:
                print("(No wardrobe images found, running without photo)")

    response = agent.run(message, image_urls=image_urls)

    # Show results
    print("\n" + "="*60)
    print("AGENT RESPONSE:")
    print("="*60)
    print(response)

    print("\n" + "="*60)
    print("MESSAGES SENT (via MockOutput):")
    print("="*60)
    for i, msg in enumerate(output.messages):
        print(f"\n[Message {i+1}]")
        print(f"  Text: {msg['text'][:200] if msg['text'] else '(none)'}...")
        print(f"  Images: {len(msg['images'])} images")
        print(f"  Layout: {msg['layout']}")
        if msg['images']:
            for j, img in enumerate(msg['images'][:3]):
                print(f"    Image {j+1}: {img[:60]}...")

    return response, output.messages


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test styling agent locally")
    parser.add_argument("message", nargs="?", default="What should I wear to brunch?",
                        help="Message to send to agent")
    parser.add_argument("--user", default="peichin", help="User ID")
    parser.add_argument("--no-context", action="store_true", help="Run without conversation context")
    parser.add_argument("--with-photo", action="store_true", help="Include a test photo")
    parser.add_argument("--provider", default="openai", choices=["openai", "anthropic"],
                        help="LLM provider")

    args = parser.parse_args()

    run_test(
        message=args.message,
        user_id=args.user,
        with_context=not args.no_context,
        with_photo=args.with_photo,
        provider=args.provider
    )
