"""
Stateful SMS Conversation Tests

Tests for conversation state management and multi-turn SMS flows.

Run with:
    cd backend && python -m pytest tests/test_stateful_sms.py -v
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


# ============================================================================
# Phase 1: ConversationStateManager Tests
# ============================================================================

class TestConversationStateManager:
    """Test Redis-backed conversation state management."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis for unit tests."""
        storage = {}

        mock = MagicMock()
        mock.get = lambda k: storage.get(k)
        mock.setex = lambda k, ttl, v: storage.update({k: v})
        mock.delete = lambda k: storage.pop(k, None)

        with patch("services.conversation_state.Redis") as MockRedis:
            MockRedis.from_url.return_value = mock
            yield mock, storage

    def test_normalize_phone_strips_whatsapp(self, mock_redis):
        """WhatsApp prefix should be stripped for consistent keys."""
        from services.conversation_state import ConversationStateManager

        manager1 = ConversationStateManager("whatsapp:+15551234567")
        manager2 = ConversationStateManager("+15551234567")

        assert manager1.phone == manager2.phone
        assert manager1.key == manager2.key

    def test_new_conversation_returns_none(self, mock_redis):
        """First lookup for a phone should return None."""
        from services.conversation_state import ConversationStateManager

        manager = ConversationStateManager("+15551234567")
        state = manager.get_state()

        assert state is None

    def test_save_and_retrieve_state(self, mock_redis):
        """State should persist and be retrievable."""
        from services.conversation_state import ConversationStateManager, ConversationState

        phone = "+15551234567"

        # Save state
        manager1 = ConversationStateManager(phone)
        state = ConversationState(
            user_id="testuser",
            phone=phone,
            last_outfit={"items": [{"name": "Grey sweater"}]}
        )
        manager1.save_state(state)

        # Retrieve with new manager instance
        manager2 = ConversationStateManager(phone)
        retrieved = manager2.get_state()

        assert retrieved is not None
        assert retrieved.user_id == "testuser"
        assert retrieved.last_outfit["items"][0]["name"] == "Grey sweater"

    def test_message_history_capped(self, mock_redis):
        """Message history should be capped at MAX_MESSAGES."""
        from services.conversation_state import ConversationStateManager, ConversationState, MAX_MESSAGES

        manager = ConversationStateManager("+15551234567")
        state = ConversationState(
            user_id="testuser",
            phone="+15551234567"
        )
        # Add more messages than the cap
        state.messages = [{"role": "user", "content": f"msg{i}"} for i in range(20)]
        manager.save_state(state)

        retrieved = manager.get_state()
        assert len(retrieved.messages) == MAX_MESSAGES

    def test_get_or_create_creates_new(self, mock_redis):
        """get_or_create should create state if none exists."""
        from services.conversation_state import ConversationStateManager

        manager = ConversationStateManager("+15551234567")
        state = manager.get_or_create_state(user_id="testuser")

        assert state is not None
        assert state.user_id == "testuser"

    def test_set_last_outfit(self, mock_redis):
        """set_last_outfit should update outfit in state."""
        from services.conversation_state import ConversationStateManager, ConversationState

        manager = ConversationStateManager("+15551234567")
        manager.save_state(ConversationState(user_id="test", phone="+15551234567"))

        outfit = {
            "items": [{"name": "Black pants"}, {"name": "White shirt"}],
            "styling_notes": "Tuck shirt in"
        }
        manager.set_last_outfit(outfit)

        state = manager.get_state()
        assert state.last_outfit["items"][0]["name"] == "Black pants"
        assert state.last_outfit["styling_notes"] == "Tuck shirt in"

    def test_append_message(self, mock_redis):
        """append_message should add to message history."""
        from services.conversation_state import ConversationStateManager, ConversationState

        manager = ConversationStateManager("+15551234567")
        manager.save_state(ConversationState(user_id="test", phone="+15551234567"))

        manager.append_message("user", "What should I wear?")
        manager.append_message("assistant", "Here's an outfit...")

        state = manager.get_state()
        assert len(state.messages) == 2
        assert state.messages[0]["role"] == "user"
        assert state.messages[1]["role"] == "assistant"

    def test_clear_removes_state(self, mock_redis):
        """clear should remove state from Redis."""
        from services.conversation_state import ConversationStateManager, ConversationState

        manager = ConversationStateManager("+15551234567")
        manager.save_state(ConversationState(user_id="test", phone="+15551234567"))

        manager.clear()

        state = manager.get_state()
        assert state is None


# ============================================================================
# Phase 2: Agent Context Tests (placeholder)
# ============================================================================

class TestAgentWithContext:
    """Test agent receives and uses conversation context."""

    def test_agent_accepts_context_param(self):
        """Agent should accept conversation_context parameter."""
        from agent.agent import StylingAgent
        from agent.output import MockOutput

        context = {
            "last_outfit": {
                "items": [{"name": "Grey sweater"}, {"name": "Black pants"}],
                "styling_notes": "Tuck sweater in"
            },
            "messages": [
                {"role": "user", "content": "What should I wear?"},
                {"role": "assistant", "content": "Here's an outfit..."}
            ]
        }

        output = MockOutput()
        agent = StylingAgent(
            user_id="testuser",
            provider="anthropic",
            output=output,
            conversation_context=context
        )

        assert agent.conversation_context == context

    def test_context_prefix_built_correctly(self):
        """Context prefix should include last outfit and messages."""
        from agent.agent import StylingAgent

        context = {
            "last_outfit": {
                "items": [{"name": "Grey sweater"}, {"name": "Black pants"}],
                "styling_notes": "Tuck sweater in"
            },
            "messages": [
                {"role": "user", "content": "What should I wear?"},
                {"role": "assistant", "content": "Here's an outfit..."}
            ]
        }

        agent = StylingAgent(
            user_id="testuser",
            conversation_context=context
        )

        prefix = agent._build_context_prefix()

        assert "[CONTEXT]" in prefix
        assert "Grey sweater" in prefix
        assert "Black pants" in prefix
        assert "Tuck sweater in" in prefix

    def test_no_context_returns_empty_prefix(self):
        """No context should return empty prefix."""
        from agent.agent import StylingAgent

        agent = StylingAgent(user_id="testuser")
        prefix = agent._build_context_prefix()

        assert prefix == ""

    def test_empty_context_returns_empty_prefix(self):
        """Empty context dict should return empty prefix."""
        from agent.agent import StylingAgent

        agent = StylingAgent(user_id="testuser", conversation_context={})
        prefix = agent._build_context_prefix()

        assert prefix == ""


# ============================================================================
# Phase 3: SMS Endpoint Tests (placeholder)
# ============================================================================

class TestSMSEndpointStateful:
    """Test SMS endpoint loads/saves conversation state."""

    def test_endpoint_loads_state(self):
        """SMS endpoint should load existing state."""
        # Will be implemented in Phase 3
        pass


# ============================================================================
# Phase 4: Stateful Output Tests
# ============================================================================

class TestStatefulOutput:
    """Test StatefulSMSOutput captures outfits."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis for unit tests."""
        storage = {}

        mock = MagicMock()
        mock.get = lambda k: storage.get(k)
        mock.setex = lambda k, ttl, v: storage.update({k: v})
        mock.delete = lambda k: storage.pop(k, None)

        with patch("services.conversation_state.Redis") as MockRedis:
            MockRedis.from_url.return_value = mock
            yield mock, storage

    def test_output_captures_outfit(self, mock_redis):
        """StatefulSMSOutput should capture sent outfit to state."""
        from services.conversation_state import ConversationStateManager, ConversationState
        from agent.output import StatefulSMSOutput

        # Setup: create state
        phone = "+15551234567"
        manager = ConversationStateManager(phone)
        manager.save_state(ConversationState(user_id="test", phone=phone))

        # Mock the send methods to avoid actual Twilio calls
        with patch("services.twilio_service.send_sms"), \
             patch("services.twilio_service.send_mms"), \
             patch("services.collage.generate_outfit_collage", return_value="https://example.com/collage.jpg"):

            output = StatefulSMSOutput(phone=phone, user_id="test", state_manager=manager)

            # Send outfit
            output.send(
                text="Here's your outfit!",
                images=["https://img1.jpg", "https://img2.jpg", "https://img3.jpg"],
                layout="outfit"
            )

        # Verify outfit was captured
        state = manager.get_state()
        assert state.last_outfit is not None
        assert len(state.last_outfit["image_urls"]) == 3
        assert state.last_outfit["styling_notes"] == "Here's your outfit!"

    def test_output_captures_multi_image_as_outfit(self, mock_redis):
        """Multiple images should be captured even with layout='list'."""
        from services.conversation_state import ConversationStateManager, ConversationState
        from agent.output import StatefulSMSOutput

        phone = "+15551234567"
        manager = ConversationStateManager(phone)
        manager.save_state(ConversationState(user_id="test", phone=phone))

        with patch("services.twilio_service.send_sms"), \
             patch("services.twilio_service.send_mms"), \
             patch("services.collage.generate_outfit_collage", return_value="https://example.com/collage.jpg"):

            output = StatefulSMSOutput(phone=phone, user_id="test", state_manager=manager)
            output.send(
                text="Your sweaters:",
                images=["https://img1.jpg", "https://img2.jpg"],
                layout="list"  # Not "outfit" but still 2+ images
            )

        state = manager.get_state()
        assert state.last_outfit is not None
        assert len(state.last_outfit["image_urls"]) == 2

    def test_single_image_not_captured(self, mock_redis):
        """Single image should not be captured as outfit."""
        from services.conversation_state import ConversationStateManager, ConversationState
        from agent.output import StatefulSMSOutput

        phone = "+15551234567"
        manager = ConversationStateManager(phone)
        manager.save_state(ConversationState(user_id="test", phone=phone))

        with patch("services.twilio_service.send_sms"), \
             patch("services.twilio_service.send_mms"), \
             patch("services.collage.generate_outfit_collage", return_value="https://example.com/collage.jpg"):

            output = StatefulSMSOutput(phone=phone, user_id="test", state_manager=manager)
            output.send(
                text="Here's that item:",
                images=["https://img1.jpg"],
                layout="list"
            )

        state = manager.get_state()
        # Should not have captured (single image, not outfit layout)
        assert state.last_outfit == {}


# ============================================================================
# Phase 5: Conversational Intent Tests (placeholder)
# ============================================================================

class TestConversationalIntents:
    """Test agent recognizes save/feedback/refine intents."""

    def test_save_this_intent(self):
        """'Save this' should trigger save_outfit."""
        # Will be implemented in Phase 5
        pass


# ============================================================================
# Phase 6: Heart Reaction Tests
# ============================================================================

class TestHeartReaction:
    """Test heart reaction auto-saves outfit."""

    def test_heart_emoji_detected(self):
        """Heart emoji should be recognized as save intent."""
        # Test various heart emoji formats
        heart_messages = ["❤️", "❤", "♥️", "🩷", "💕", "Love it!", "love this"]

        for msg in heart_messages:
            # Agent prompt includes "SAVE INTENT: ... ❤️" so these should trigger save
            assert any(c in msg.lower() for c in ["❤", "♥", "🩷", "💕", "love"])

    def test_heart_uses_last_outfit(self):
        """Heart reaction should save the last outfit from context."""
        from agent.agent import StylingAgent
        from agent.output import MockOutput

        context = {
            "last_outfit": {
                "items": [
                    {"name": "Grey sweater", "image_url": "https://img1.jpg"},
                    {"name": "Black pants", "image_url": "https://img2.jpg"}
                ],
                "styling_notes": "Tuck sweater into pants"
            },
            "messages": []
        }

        output = MockOutput()
        agent = StylingAgent(
            user_id="testuser",
            provider="anthropic",
            output=output,
            conversation_context=context
        )

        # Verify context is injected
        prefix = agent._build_context_prefix()
        assert "Grey sweater" in prefix
        assert "Black pants" in prefix
        # Agent should use this context when receiving "❤️" message
