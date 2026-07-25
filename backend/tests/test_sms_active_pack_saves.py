"""Regression coverage for active-pack saves in the SMS/WhatsApp agent."""

import os
import sys
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class FakeStateManager:
    def __init__(self, active_pack):
        self.state = SimpleNamespace(active_pack=deepcopy(active_pack))

    def get_state(self):
        return self.state


class FakeSavedOutfitsManager:
    saved = []
    visualizations = []

    def __init__(self, user_id):
        self.user_id = user_id

    def save_outfit(self, outfit_combo, reason="", occasion=None, context=None):
        outfit_id = f"saved-{len(self.saved) + 1}"
        self.saved.append({
            "id": outfit_id,
            "items": deepcopy(outfit_combo.items),
            "styling_notes": outfit_combo.styling_notes,
            "occasion": occasion,
        })
        return outfit_id

    def update_outfit_visualization(self, outfit_id, visualization_url):
        self.visualizations.append((outfit_id, visualization_url))
        return True


def make_agent(active_pack):
    from agent.agent import StylingAgent

    agent = object.__new__(StylingAgent)
    agent.user_id = "test"
    agent.conversation_context = {"active_pack": deepcopy(active_pack)}
    agent.output = SimpleNamespace(state_manager=FakeStateManager(active_pack))
    return agent


def active_pack():
    return {
        "outfits": [
            {
                "label": "First day at work",
                "item_names": ["White ruffled long-sleeve blouse", "Black wide-leg trousers"],
                "items": [
                    {"name": "White ruffled long-sleeve blouse", "category": "tops", "image_path": "https://img/blouse.jpg"},
                    {"name": "Black wide-leg trousers", "category": "bottoms", "image_path": "https://img/trousers.jpg"},
                ],
                "image_urls": ["https://img/blouse.jpg", "https://img/trousers.jpg"],
                "styling_notes": "Structured but feminine for the first day.",
                "visualization_url": "https://viz/first-day.jpg",
            },
            {
                "label": "Family birthday party",
                "item_names": ["Blue floral dress", "Silver sandals"],
                "items": [
                    {"name": "Blue floral dress", "category": "dresses", "image_path": "https://img/dress.jpg"},
                    {"name": "Silver sandals", "category": "shoes", "image_path": "https://img/sandals.jpg"},
                ],
                "image_urls": ["https://img/dress.jpg", "https://img/sandals.jpg"],
                "styling_notes": "Easy polish for family.",
                "visualization_url": "https://viz/birthday.jpg",
            },
            {
                "label": "Brunch with Andy",
                "item_names": ["White tee with black bow detail", "FRAME The Cape Jacket"],
                "items": [
                    {"name": "White tee with black bow detail", "category": "tops", "image_path": "https://img/bow-tee.jpg"},
                    {"name": "FRAME The Cape Jacket", "category": "outerwear", "image_path": "https://img/cape.jpg"},
                ],
                "image_urls": ["https://img/bow-tee.jpg", "https://img/cape.jpg"],
                "styling_notes": "Playful and relaxed for brunch.",
                "visualization_url": "https://viz/brunch.jpg",
            },
        ]
    }


def matcher(user_id, names):
    return [
        {
            "id": f"wardrobe-{index}",
            "name": name,
            "category": "tops" if "blouse" in name.lower() or "tee" in name.lower() else "other",
            "image_path": f"https://wardrobe/{index}.jpg",
            "matched": True,
        }
        for index, name in enumerate(names, start=1)
    ]


def test_numbered_active_pack_save_uses_exact_items_and_per_outfit_visualizations():
    FakeSavedOutfitsManager.saved = []
    FakeSavedOutfitsManager.visualizations = []
    pack = active_pack()
    agent = make_agent(pack)

    with patch("services.saved_outfits_manager.SavedOutfitsManager", FakeSavedOutfitsManager), \
         patch("primitives.matching.match_items_to_wardrobe", side_effect=matcher):
        result = agent._execute_tool("save_outfit", {
            "reasoning": "The user likes numbered outfits 1 and 3.",
            "active_pack_indices": [1, 3],
            # These are deliberately wrong: active pack must win over model reconstruction.
            "items": [{"id": "unknown", "name": "Wrong outfit", "category": "unknown"}],
        })

    assert result["status"] == "saved"
    assert result["outfit_ids"] == ["saved-1", "saved-2"]
    assert [entry["occasion"] for entry in FakeSavedOutfitsManager.saved] == [
        "First day at work",
        "Brunch with Andy",
    ]
    assert [item["name"] for item in FakeSavedOutfitsManager.saved[0]["items"]] == pack["outfits"][0]["item_names"]
    assert [item["name"] for item in FakeSavedOutfitsManager.saved[1]["items"]] == pack["outfits"][2]["item_names"]
    assert all(item["id"] != "unknown" for saved in FakeSavedOutfitsManager.saved for item in saved["items"])
    assert all(item["image_path"] for saved in FakeSavedOutfitsManager.saved for item in saved["items"])
    assert FakeSavedOutfitsManager.visualizations == [
        ("saved-1", "https://viz/first-day.jpg"),
        ("saved-2", "https://viz/brunch.jpg"),
    ]


def test_active_pack_save_refuses_missing_item_data_instead_of_creating_unknown_items():
    FakeSavedOutfitsManager.saved = []
    pack = active_pack()
    pack["outfits"][0]["items"][0].pop("image_path")
    pack["outfits"][0]["image_urls"] = [None, "https://img/trousers.jpg"]
    agent = make_agent(pack)

    with patch("services.saved_outfits_manager.SavedOutfitsManager", FakeSavedOutfitsManager), \
         patch("primitives.matching.match_items_to_wardrobe", return_value=[
             {"id": None, "name": "White ruffled long-sleeve blouse", "image_path": None, "matched": False},
             {"id": "trousers-id", "name": "Black wide-leg trousers", "image_path": "https://img/trousers.jpg", "matched": True},
         ]):
        result = agent._execute_tool("save_outfit", {
            "reasoning": "Save outfit 1.",
            "active_pack_indices": [1],
        })

    assert "didn't save a corrupted outfit" in result["error"]
    assert FakeSavedOutfitsManager.saved == []


def test_active_pack_context_explicitly_instructs_numbered_likes_to_save():
    from agent.agent import _positive_active_pack_indices

    agent = make_agent(active_pack())

    state_context = agent._build_state_context("I like outfit 1 and 3")

    assert _positive_active_pack_indices("I like outfit 1 and 3", 3) == [1, 3]
    assert _positive_active_pack_indices("I don't like outfit 1", 3) == []
    assert "Outfit 1 (First day at work)" in state_context
    assert "active_pack_indices" in state_context
    assert "# Explicit Save Intent" in state_context
    assert "1, 3" in state_context


def test_update_profile_tool_persists_words_and_style_note():
    from agent.agent import StylingAgent

    class FakeProfileManager:
        profile = {"style_words": ["Classic", "Playful", "Relaxed"], "style_notes": ["Keep tailoring easy."]}
        saved_data = None

        def __init__(self, user_id):
            self.user_id = user_id

        def get_profile(self, user_id):
            return deepcopy(self.profile)

        def save_profile(self, profile_data):
            self.__class__.saved_data = deepcopy(profile_data)
            self.__class__.profile.update(profile_data)
            self.__class__.profile["style_words"] = [
                profile_data["three_words"]["current"],
                profile_data["three_words"]["aspirational"],
                profile_data["three_words"]["feeling"],
            ]
            return True

    agent = object.__new__(StylingAgent)
    agent.user_id = "test"
    agent.output = None
    agent.conversation_context = {}

    with patch("services.user_profile_manager.UserProfileManager", FakeProfileManager), \
         patch("services.activity_logger.log_activity") as log_activity:
        result = agent._execute_tool("update_profile", {
            "reasoning": "The user approved these words and asked to retain the flowy nuance.",
            "three_words": {
                "current": "Feminine",
                "aspirational": "Whimsical",
                "feeling": "Grounded",
            },
            "style_note": "Open to flowy silhouettes when they still feel grounded.",
        })

    assert result["success"] is True
    assert FakeProfileManager.saved_data["three_words"]["aspirational"] == "Whimsical"
    assert FakeProfileManager.saved_data["style_notes"] == [
        "Keep tailoring easy.",
        "Open to flowy silhouettes when they still feel grounded.",
    ]
    log_activity.assert_called_once_with("test", "style_words_updated", {
        "current": "Feminine",
        "aspirational": "Whimsical",
        "feeling": "Grounded",
    })


@pytest.fixture
def mock_redis():
    storage = {}
    mock = MagicMock()
    mock.get = lambda key: storage.get(key)
    mock.setex = lambda key, ttl, value: storage.update({key: value})

    with patch("services.conversation_state.Redis") as redis_cls:
        redis_cls.from_url.return_value = mock
        yield storage


def test_presented_active_pack_records_item_ids_for_future_exact_saves(mock_redis):
    from agent.output import StatefulSMSOutput
    from services.conversation_state import ConversationState, ConversationStateManager

    manager = ConversationStateManager("+15551234567")
    manager.save_state(ConversationState(user_id="test", phone="+15551234567"))
    resolved = [
        {"id": "top-id", "name": "White tee", "category": "tops", "sub_category": "", "image_url": "https://img/tee.jpg"},
        {"id": "jeans-id", "name": "Blue jeans", "category": "bottoms", "sub_category": "", "image_url": "https://img/jeans.jpg"},
    ]

    with patch("agent.output.resolve_items_from_urls", return_value=resolved), \
         patch("services.twilio_service.send_sms"), \
         patch("services.twilio_service.send_mms"), \
         patch("services.collage.generate_outfit_collage", return_value="https://img/collage.jpg"), \
         patch("time.sleep"):
        output = StatefulSMSOutput("+15551234567", "test", manager)
        output.present_outfit(
            "Outfit 1: easy brunch.",
            ["https://img/tee.jpg", "https://img/jeans.jpg"],
            visualize=True,
            item_names=["White tee", "Blue jeans"],
        )

    stored = manager.get_state().active_pack["outfits"][0]["items"]
    assert [item["id"] for item in stored] == ["top-id", "jeans-id"]
    assert [item["image_path"] for item in stored] == ["https://img/tee.jpg", "https://img/jeans.jpg"]
