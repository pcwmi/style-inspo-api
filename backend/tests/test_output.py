"""
Unit tests for agent/output.py shared helpers.

Tests parse_outfit_text(), resolve_items_from_urls(), and APIOutput behavior.
No external deps needed (no Twilio, S3, OpenAI).
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('STORAGE_TYPE', 'local')
os.environ.setdefault('OPENAI_API_KEY', 'test-key')

from agent.output import parse_outfit_text, resolve_items_from_urls, APIOutput


# --- parse_outfit_text ---

class TestParseOutfitText:

    def test_full_format_bold(self):
        text = "**The magic:** Pink cardigan softens the look\n\n**This outfit says:** I'm playful but put-together"
        r = parse_outfit_text(text)
        assert r["magic"] == "Pink cardigan softens the look"
        assert r["identity"] == "I'm playful but put-together"
        assert r["full"] == text

    def test_full_format_no_bold(self):
        text = "The magic: Clean lines\n\nThis outfit says: Effortless"
        r = parse_outfit_text(text)
        assert r["magic"] == "Clean lines"
        assert r["identity"] == "Effortless"

    def test_no_markers(self):
        text = "Just a regular styling note"
        r = parse_outfit_text(text)
        assert r["magic"] == "Just a regular styling note"
        assert r["identity"] == ""

    def test_magic_only(self):
        text = "**The magic:** Great color combo"
        r = parse_outfit_text(text)
        assert r["magic"] == "Great color combo"
        assert r["identity"] == ""

    def test_empty_string(self):
        r = parse_outfit_text("")
        assert r["magic"] == ""
        assert r["identity"] == ""
        assert r["full"] == ""

    def test_none(self):
        r = parse_outfit_text(None)
        assert r["magic"] == ""
        assert r["identity"] == ""
        assert r["full"] == ""

    def test_asterisks_stripped(self):
        text = "**The magic:** **Bold** text with *emphasis*\n\n**This outfit says:** More **bold**"
        r = parse_outfit_text(text)
        assert "**" not in r["magic"]
        assert "**" not in r["identity"]
        assert "*" not in r["magic"]
        assert "*" not in r["identity"]

    def test_multiline_magic(self):
        text = "**The magic:** First line\nSecond line of magic\n\n**This outfit says:** Identity here"
        r = parse_outfit_text(text)
        assert "First line" in r["magic"]
        assert "Second line" in r["magic"]
        assert r["identity"] == "Identity here"


# --- resolve_items_from_urls ---

SAMPLE_ITEMS = [
    {
        "id": "item_001",
        "styling_details": {
            "name": "White T-Shirt",
            "category": "tops",
            "sub_category": "",
        },
        "system_metadata": {"image_path": "https://example.com/white-tshirt.jpg"},
    },
    {
        "id": "item_002",
        "styling_details": {
            "name": "Blue Jeans",
            "category": "bottoms",
            "sub_category": "jeans",
        },
        "system_metadata": {"image_path": "https://example.com/blue-jeans.jpg"},
    },
]


@pytest.fixture
def mock_wardrobe():
    mock_wm = MagicMock()
    mock_wm.get_wardrobe_items.return_value = SAMPLE_ITEMS
    with patch('services.wardrobe_manager.WardrobeManager', return_value=mock_wm) as mock_class:
        yield mock_class


class TestResolveItemsFromUrls:

    def test_returns_correct_shape(self, mock_wardrobe):
        result = resolve_items_from_urls("test", ["https://example.com/white-tshirt.jpg"])
        assert len(result) == 1
        item = result[0]
        assert item["id"] == "item_001"
        assert item["name"] == "White T-Shirt"
        assert item["category"] == "tops"
        assert item["sub_category"] == ""
        assert item["image_url"] == "https://example.com/white-tshirt.jpg"

    def test_all_fields_present(self, mock_wardrobe):
        result = resolve_items_from_urls("test", ["https://example.com/blue-jeans.jpg"])
        required_keys = {"id", "name", "category", "sub_category", "image_url"}
        assert set(result[0].keys()) == required_keys

    def test_unknown_url_placeholder(self, mock_wardrobe):
        result = resolve_items_from_urls("test", ["https://example.com/unknown.jpg"])
        assert result[0]["name"] == "Item 1"
        assert result[0]["category"] == "unknown"
        assert result[0]["id"] == ""

    def test_multiple_urls_mixed(self, mock_wardrobe):
        urls = [
            "https://example.com/white-tshirt.jpg",
            "https://example.com/unknown.jpg",
            "https://example.com/blue-jeans.jpg",
        ]
        result = resolve_items_from_urls("test", urls)
        assert len(result) == 3
        assert result[0]["name"] == "White T-Shirt"
        assert result[1]["name"] == "Item 2"  # unknown gets numbered
        assert result[2]["name"] == "Blue Jeans"

    def test_empty_list(self, mock_wardrobe):
        result = resolve_items_from_urls("test", [])
        assert result == []

    def test_wardrobe_error_returns_placeholders(self):
        """When WardrobeManager throws, we get graceful fallback."""
        with patch('services.wardrobe_manager.WardrobeManager', side_effect=Exception("S3 down")):
            result = resolve_items_from_urls("test", ["https://example.com/a.jpg"])
            assert len(result) == 1
            assert result[0]["name"] == "Item 1"
            assert result[0]["category"] == "unknown"


# --- APIOutput ---

class TestAPIOutput:

    def test_send_goes_to_messages_not_outfits(self):
        out = APIOutput(user_id="test")
        out.send("hello", [])
        out.send("browse results", ["img.jpg"])
        assert len(out.outfits) == 0
        assert len(out.messages) == 2

    def test_present_outfit_goes_to_outfits(self):
        out = APIOutput(user_id="test")
        out.present_outfit("outfit text", [], visualize=False)
        assert len(out.outfits) == 1
        assert out.outfits[0]["text"] == "outfit text"

    def test_present_outfit_text_also_in_messages(self):
        out = APIOutput(user_id="test")
        out.present_outfit("outfit text", [], visualize=False)
        assert "outfit text" in out.messages

    def test_mixed_calls_correct_counts(self):
        out = APIOutput(user_id="test")
        out.send("msg 1", [])
        out.send("msg 2", ["img.jpg"])
        out.present_outfit("outfit 1", [], visualize=False)
        out.present_outfit("outfit 2", [], visualize=False)
        assert len(out.outfits) == 2
        # messages: 2 from send + 2 text from present_outfit
        assert len(out.messages) == 4

    def test_send_message_structure(self):
        out = APIOutput(user_id="test")
        out.send("hello", ["img1.jpg", "img2.jpg"])
        msg = out.messages[0]
        assert msg["text"] == "hello"
        assert msg["images"] == ["img1.jpg", "img2.jpg"]
