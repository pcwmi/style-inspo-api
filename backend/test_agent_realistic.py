#!/usr/bin/env python3
"""
Realistic Agent Test - Simulates actual SMS multi-turn flow.

Uses StatefulSMSOutput (mocked to avoid real SMS) to test:
1. Outfit sent → saved to state with real item names
2. Next turn → agent sees real context
3. "Save this" / "swap shoes" work correctly

Usage:
    cd backend
    python test_agent_realistic.py
"""

import os
import sys
import logging
from unittest.mock import patch, MagicMock

# Setup path and env
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


def simulate_sms_conversation(user_id: str = "peichin"):
    """Simulate a realistic multi-turn SMS conversation."""
    from agent.agent import StylingAgent
    from agent.output import StatefulSMSOutput
    from services.conversation_state import ConversationStateManager, ConversationState

    # Mock Redis with in-memory storage
    storage = {}
    mock_redis = MagicMock()
    mock_redis.get = lambda k: storage.get(k)
    mock_redis.setex = lambda k, ttl, v: storage.update({k: v})
    mock_redis.delete = lambda k: storage.pop(k, None)

    phone = "+15551234567"

    with patch("services.conversation_state.Redis") as MockRedis, \
         patch("services.twilio_service.send_sms") as mock_send_sms, \
         patch("services.twilio_service.send_mms") as mock_send_mms, \
         patch("services.collage.generate_outfit_collage", return_value="https://collage.jpg"):

        MockRedis.from_url.return_value = mock_redis

        # Initialize state manager
        state_manager = ConversationStateManager(phone)
        state_manager.save_state(ConversationState(user_id=user_id, phone=phone))

        print("\n" + "="*70)
        print("SIMULATING MULTI-TURN SMS CONVERSATION")
        print("="*70)

        # =====================================================================
        # TURN 1: User asks for outfit
        # =====================================================================
        print("\n" + "-"*70)
        print("TURN 1: User asks for outfit")
        print("-"*70)

        message1 = "What should I wear to a casual brunch?"
        state_manager.append_message("user", message1)
        print(f"USER: {message1}")

        # Get current state for context
        state = state_manager.get_state()
        conversation_context = {
            "last_outfit": state.last_outfit,
            "outfit_history": state.outfit_history,
            "messages": state.messages,
            "image_descriptions": state.image_descriptions,
        }

        # Create output handler (captures outfit to state)
        output1 = StatefulSMSOutput(phone=phone, user_id=user_id, state_manager=state_manager)

        # Disable background visualization for test
        output1._trigger_background_visualization = lambda *args: None

        agent1 = StylingAgent(
            user_id=user_id,
            provider="openai",
            output=output1,
            conversation_context=conversation_context
        )

        # Show context being passed
        prefix1 = agent1._build_context_prefix()
        print(f"\nCONTEXT PASSED TO AGENT:\n{prefix1 if prefix1 else '(empty - first turn)'}")

        response1 = agent1.run(message1)
        print(f"\nAGENT RESPONSE:\n{response1[:300]}...")

        # Record assistant message
        state_manager.append_message("assistant", response1)

        # Show what was captured to state
        state = state_manager.get_state()
        print(f"\n📦 STATE AFTER TURN 1:")
        print(f"   last_outfit.items: {[item.get('name') for item in state.last_outfit.get('items', [])]}")
        print(f"   messages: {len(state.messages)} messages")

        # Show SMS that would be sent
        print(f"\n📱 SMS SENT:")
        for call in mock_send_sms.call_args_list:
            print(f"   TEXT: {call[0][1][:80]}...")
        for call in mock_send_mms.call_args_list:
            print(f"   MMS: {call[0][1][:50]}... + {len(call[0][2])} images")

        # Reset mocks for next turn
        mock_send_sms.reset_mock()
        mock_send_mms.reset_mock()

        # =====================================================================
        # TURN 2: User wants to swap shoes
        # =====================================================================
        print("\n" + "-"*70)
        print("TURN 2: User wants to swap shoes")
        print("-"*70)

        message2 = "Can we try different shoes? Something more casual"
        state_manager.append_message("user", message2)
        print(f"USER: {message2}")

        # Get updated state
        state = state_manager.get_state()
        conversation_context = {
            "last_outfit": state.last_outfit,
            "outfit_history": state.outfit_history,
            "messages": state.messages,
            "image_descriptions": state.image_descriptions,
        }

        output2 = StatefulSMSOutput(phone=phone, user_id=user_id, state_manager=state_manager)
        output2._trigger_background_visualization = lambda *args: None

        agent2 = StylingAgent(
            user_id=user_id,
            provider="openai",
            output=output2,
            conversation_context=conversation_context
        )

        # Show context - THIS IS THE KEY TEST
        prefix2 = agent2._build_context_prefix()
        print(f"\nCONTEXT PASSED TO AGENT:")
        print(prefix2)

        response2 = agent2.run(message2)
        print(f"\nAGENT RESPONSE:\n{response2[:300]}...")

        state_manager.append_message("assistant", response2)

        # Show state after turn 2
        state = state_manager.get_state()
        print(f"\n📦 STATE AFTER TURN 2:")
        print(f"   last_outfit.items: {[item.get('name') for item in state.last_outfit.get('items', [])]}")
        print(f"   outfit_history: {len(state.outfit_history)} previous outfits")
        print(f"   messages: {len(state.messages)} messages")

        # =====================================================================
        # TURN 3: User wants to save
        # =====================================================================
        print("\n" + "-"*70)
        print("TURN 3: User saves the outfit")
        print("-"*70)

        message3 = "Love it! Save this"
        state_manager.append_message("user", message3)
        print(f"USER: {message3}")

        state = state_manager.get_state()
        conversation_context = {
            "last_outfit": state.last_outfit,
            "outfit_history": state.outfit_history,
            "messages": state.messages,
            "image_descriptions": state.image_descriptions,
        }

        output3 = StatefulSMSOutput(phone=phone, user_id=user_id, state_manager=state_manager)
        output3._trigger_background_visualization = lambda *args: None

        agent3 = StylingAgent(
            user_id=user_id,
            provider="openai",
            output=output3,
            conversation_context=conversation_context
        )

        prefix3 = agent3._build_context_prefix()
        print(f"\nCONTEXT PASSED TO AGENT:")
        print(prefix3)

        response3 = agent3.run(message3)
        print(f"\nAGENT RESPONSE:\n{response3}")

        print("\n" + "="*70)
        print("TEST COMPLETE")
        print("="*70)


if __name__ == "__main__":
    simulate_sms_conversation()
