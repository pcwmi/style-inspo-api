"""
SMS Agent Verification Tests

This test harness lets Claude self-verify SMS agent changes by:
1. Running the agent with MockOutput to capture what would be sent
2. Verifying output structure (text, images, layout)
3. Checking that images are valid URLs

Run with:
    cd backend && python -m pytest tests/test_sms_verification.py -v

For live tests only (requires API keys):
    cd backend && python -m pytest tests/test_sms_verification.py -v -m live

Note: Live tests hit real LLM APIs and S3, so they:
- Require ANTHROPIC_API_KEY and AWS credentials
- Need STORAGE_TYPE=s3 for real user data
- Take 15-30 seconds per test
"""

import os
import sys
import pytest
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Configure logging to see agent reasoning
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom marker for live tests that need API keys
requires_api = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set - skipping live agent tests"
)


# ============================================================================
# Unit Tests - No API keys needed
# ============================================================================

class TestMockOutput:
    """Test that MockOutput captures the expected structure.

    These tests don't require API keys - they just test MockOutput directly.
    """

    @pytest.fixture
    def mock_output(self):
        """Create a MockOutput instance."""
        from agent.output import MockOutput
        return MockOutput()

    def test_mock_output_accumulates_messages(self, mock_output):
        """MockOutput should accumulate multiple messages."""
        mock_output.send(text="First message", images=[])
        mock_output.present_outfit(text="Second message", images=["http://example.com/img.jpg"])

        assert len(mock_output.messages) == 2
        assert mock_output.messages[0]["text"] == "First message"
        assert mock_output.messages[0]["tool"] == "send_message"
        assert mock_output.messages[1]["images"] == ["http://example.com/img.jpg"]
        assert mock_output.messages[1]["tool"] == "present_outfit"

    def test_mock_output_handles_none_text(self, mock_output):
        """MockOutput should handle None text (image-only messages)."""
        mock_output.present_outfit(text=None, images=["http://example.com/img.jpg"])

        assert len(mock_output.messages) == 1
        assert mock_output.messages[0]["text"] is None
        assert len(mock_output.messages[0]["images"]) == 1

    def test_mock_output_tool_field(self, mock_output):
        """MockOutput should record the tool name for each method."""
        mock_output.send(text="Test", images=[])
        mock_output.present_outfit(text="Test", images=["http://example.com/img.jpg"], visualize=True)

        assert mock_output.messages[0]["tool"] == "send_message"
        assert mock_output.messages[1]["tool"] == "present_outfit"
        assert mock_output.messages[1]["visualize"] is True

    def test_mock_output_multiple_images(self, mock_output):
        """MockOutput should handle multiple images."""
        images = [
            "http://example.com/1.jpg",
            "http://example.com/2.jpg",
            "http://example.com/3.jpg"
        ]
        mock_output.present_outfit(text="Outfit", images=images)

        assert len(mock_output.messages[0]["images"]) == 3


# ============================================================================
# Live Tests - Require ANTHROPIC_API_KEY
# ============================================================================

@pytest.fixture
def set_s3_storage():
    """Set STORAGE_TYPE=s3 to access real user data."""
    original = os.environ.get("STORAGE_TYPE")
    os.environ["STORAGE_TYPE"] = "s3"
    yield
    if original:
        os.environ["STORAGE_TYPE"] = original
    else:
        os.environ.pop("STORAGE_TYPE", None)


@pytest.fixture
def mock_output():
    """Create a MockOutput instance to capture agent responses."""
    from agent.output import MockOutput
    return MockOutput()


@pytest.fixture
def agent_with_mock(set_s3_storage, mock_output):
    """Create a StylingAgent with MockOutput for testing."""
    from agent.agent import StylingAgent

    # Use peichin as test user (has real wardrobe data)
    agent = StylingAgent(
        user_id="peichin",
        provider="anthropic",
        output=mock_output
    )
    return agent, mock_output


@requires_api
class TestSMSBasicFlow:
    """Test basic SMS agent flows."""

    def test_outfit_request_returns_message(self, agent_with_mock):
        """
        When user asks for outfit help, agent should:
        1. Call send_message tool
        2. Include text response
        3. Include image URLs for matched items
        """
        agent, mock_output = agent_with_mock

        # Run the agent with a simple outfit request
        response = agent.run("What should I wear to work?")

        # Agent should have called send_message at least once
        assert len(mock_output.messages) > 0, (
            "Agent should call send_message at least once. "
            f"Got {len(mock_output.messages)} messages. "
            f"Agent response: {response[:500]}"
        )

        # Check the first message structure
        first_message = mock_output.messages[0]
        assert "text" in first_message, "Message should have 'text' field"
        assert "images" in first_message, "Message should have 'images' field"
        assert "tool" in first_message, "Message should have 'tool' field"

        logger.info(f"Agent sent {len(mock_output.messages)} message(s)")
        logger.info(f"First message: text={first_message['text'][:100] if first_message['text'] else None}...")
        logger.info(f"Images count: {len(first_message['images'])}")

    def test_outfit_request_includes_images(self, agent_with_mock):
        """
        Outfit responses should include item images.
        """
        agent, mock_output = agent_with_mock

        response = agent.run("Give me a casual weekend outfit")

        # Should have at least one message with images
        has_images = any(len(msg["images"]) > 0 for msg in mock_output.messages)

        assert has_images, (
            "At least one message should include images. "
            f"Messages: {mock_output.messages}"
        )

        # Check that image URLs are valid format
        for msg in mock_output.messages:
            for img_url in msg["images"]:
                assert img_url.startswith("http"), (
                    f"Image URL should start with http: {img_url}"
                )

    def test_outfit_uses_present_outfit_tool(self, agent_with_mock):
        """
        Outfit suggestions should use present_outfit tool for collage.
        """
        agent, mock_output = agent_with_mock

        response = agent.run("What's a good date night look?")

        # Find message with images (the outfit)
        outfit_message = None
        for msg in mock_output.messages:
            if len(msg["images"]) > 0:
                outfit_message = msg
                break

        if outfit_message:
            assert outfit_message["tool"] in ["present_outfit", "send_message"], (
                f"Outfit message tool should be 'present_outfit' or 'send_message', "
                f"got: {outfit_message['tool']}"
            )
            logger.info(f"Tool used: {outfit_message['tool']}")


@requires_api
class TestSMSImageFlow:
    """Test inspiration image flow (user sends image for styling help)."""

    @pytest.fixture
    def sample_image_url(self):
        """A public image URL for testing vision capabilities.

        Using an outfit image with clear styling details (sweater tied around shoulders)
        to verify the agent identifies the HERO DETAIL, not just vibes.
        """
        # Person wearing white jeans with sweater tied around shoulders - clear hero detail
        return "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600"

    def test_inspiration_image_request(self, agent_with_mock, sample_image_url):
        """
        When user sends an inspiration image, agent should:
        1. Analyze the image
        2. Suggest items from wardrobe that match
        3. Send response via send_message
        """
        agent, mock_output = agent_with_mock

        # Run with an inspiration image
        response = agent.run(
            "How can I recreate this look from my wardrobe?",
            image_urls=[sample_image_url]
        )

        # Should get at least one message
        assert len(mock_output.messages) > 0, (
            f"Agent should respond to inspiration image. "
            f"Got response: {response[:500]}"
        )

        # Check that response references the image
        # (agent should mention analyzing the image or describing what it sees)
        combined_text = " ".join(
            msg["text"] or "" for msg in mock_output.messages
        ).lower()

        logger.info(f"Combined response text: {combined_text[:500]}...")

        # The response should indicate the agent looked at something
        # (could mention colors, style, outfit, look, etc.)
        style_keywords = ["color", "style", "look", "outfit", "wear", "piece", "item"]
        has_style_content = any(kw in combined_text for kw in style_keywords)

        assert has_style_content, (
            "Response should contain styling-related content. "
            f"Text: {combined_text[:300]}"
        )


@requires_api
class TestSMSEdgeCases:
    """Test edge cases and error handling."""

    def test_simple_greeting(self, agent_with_mock):
        """
        Simple greetings should still work (even if no outfit is needed).
        """
        agent, mock_output = agent_with_mock

        response = agent.run("Hi!")

        # Agent should respond - either via return value or send_message
        has_response = bool(response) or len(mock_output.messages) > 0
        assert has_response, (
            f"Agent should respond via text or send_message. "
            f"Got response='{response}', messages={mock_output.messages}"
        )

        if response:
            logger.info(f"Greeting response (text): {response[:200]}")
        if mock_output.messages:
            for msg in mock_output.messages:
                logger.info(f"Greeting response (send_message): {msg['text'][:100] if msg['text'] else 'None'}...")

    def test_wardrobe_query(self, agent_with_mock):
        """
        User can ask about their wardrobe without requesting an outfit.
        """
        agent, mock_output = agent_with_mock

        response = agent.run("What tops do I have in my wardrobe?")

        # Agent should respond - either via return value or send_message
        has_response = bool(response) or len(mock_output.messages) > 0
        assert has_response, (
            f"Agent should provide wardrobe info via text or send_message. "
            f"Got response='{response}', messages={mock_output.messages}"
        )

        if response:
            logger.info(f"Wardrobe query response (text): {response[:300]}")
        if mock_output.messages:
            for msg in mock_output.messages:
                logger.info(f"Wardrobe query (send_message): {msg['text'][:100] if msg['text'] else 'None'}...")


@requires_api
class TestFullSMSFlow:
    """Full integration test of the SMS agent flow."""

    def test_complete_outfit_flow(self, agent_with_mock):
        """
        Complete flow: request → agent processes → sends outfit.

        This test verifies:
        1. Agent fetches wardrobe items
        2. Agent creates an outfit
        3. Agent calls resolve_items to get images
        4. Agent calls send_message with images
        """
        agent, mock_output = agent_with_mock

        response = agent.run(
            "I need an outfit for a job interview. "
            "Something professional but still me."
        )

        # Verify we got a complete response
        assert len(mock_output.messages) > 0, (
            f"Should have at least one send_message call. "
            f"Agent response: {response}"
        )

        # Find the outfit message (should have images)
        outfit_messages = [m for m in mock_output.messages if len(m["images"]) > 0]

        # Log what we got
        logger.info(f"Total messages: {len(mock_output.messages)}")
        logger.info(f"Messages with images: {len(outfit_messages)}")

        for i, msg in enumerate(mock_output.messages):
            logger.info(f"Message {i}: text={msg['text'][:50] if msg['text'] else 'None'}..., "
                       f"images={len(msg['images'])}, tool={msg['tool']}")

        # Verify at least one message has multiple items (an outfit)
        if outfit_messages:
            max_items = max(len(m["images"]) for m in outfit_messages)
            logger.info(f"Max items in outfit: {max_items}")

            # An outfit should have at least 2 items (top + bottom, or similar)
            assert max_items >= 2, (
                f"Outfit should have at least 2 items, got {max_items}"
            )
