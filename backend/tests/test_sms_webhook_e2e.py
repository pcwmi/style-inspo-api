"""Local end-to-end SMS orchestration tests with all external providers mocked."""

import asyncio
import json
import os
import sys
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class FakeOpenAIClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return next(self.responses)


def tool_response(name, arguments):
    return SimpleNamespace(
        choices=[SimpleNamespace(
            finish_reason="tool_calls",
            message=SimpleNamespace(
                content=None,
                tool_calls=[SimpleNamespace(
                    id="tool-1",
                    function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
                )],
            ),
        )],
    )


def text_response(text):
    return SimpleNamespace(
        choices=[SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(content=text, tool_calls=None),
        )],
    )


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
            "occasion": occasion,
            "styling_notes": outfit_combo.styling_notes,
        })
        return outfit_id

    def update_outfit_visualization(self, outfit_id, visualization_url):
        self.visualizations.append((outfit_id, visualization_url))
        return True


class FakeProfileManager:
    profile = {"style_words": ["Classic", "Playful", "Relaxed"]}
    saved_data = None

    def __init__(self, user_id):
        self.user_id = user_id

    def get_profile(self, user_id):
        return deepcopy(self.profile)

    def save_profile(self, profile_data):
        self.__class__.saved_data = deepcopy(profile_data)
        self.__class__.profile.update(profile_data)
        if "three_words" in profile_data:
            words = profile_data["three_words"]
            self.__class__.profile["style_words"] = [
                words["current"], words["aspirational"], words["feeling"],
            ]
        return True


@pytest.fixture
def mock_redis():
    storage = {}
    client = MagicMock()
    client.get = lambda key: storage.get(key)
    client.setex = lambda key, ttl, value: storage.update({key: value})

    with patch("services.conversation_state.Redis") as redis_cls:
        redis_cls.from_url.return_value = client
        yield storage


def seed_active_pack(phone):
    from services.conversation_state import ConversationState, ConversationStateManager

    manager = ConversationStateManager(phone)
    state = ConversationState(user_id="test", phone=phone)
    state.last_outfit = {"visualization_url": "https://viz/brunch.jpg"}
    state.active_pack = {
        "outfits": [
            {
                "label": "First day at work",
                "item_names": ["White ruffled blouse", "Black wide-leg trousers"],
                "items": [
                    {"id": "blouse-id", "name": "White ruffled blouse", "category": "tops", "image_path": "https://img/blouse.jpg"},
                    {"id": "trousers-id", "name": "Black wide-leg trousers", "category": "bottoms", "image_path": "https://img/trousers.jpg"},
                ],
                "image_urls": ["https://img/blouse.jpg", "https://img/trousers.jpg"],
                "styling_notes": "Structured but feminine.",
                "visualization_url": "https://viz/first-day.jpg",
            },
            {
                "label": "Family birthday party",
                "item_names": ["Blue floral dress", "Silver sandals"],
                "items": [
                    {"id": "dress-id", "name": "Blue floral dress", "category": "dresses", "image_path": "https://img/dress.jpg"},
                    {"id": "sandals-id", "name": "Silver sandals", "category": "shoes", "image_path": "https://img/sandals.jpg"},
                ],
                "image_urls": ["https://img/dress.jpg", "https://img/sandals.jpg"],
                "styling_notes": "Easy polish for family.",
                "visualization_url": "https://viz/birthday.jpg",
            },
            {
                "label": "Brunch with Andy",
                "item_names": ["White bow tee", "Cape jacket"],
                "items": [
                    {"id": "tee-id", "name": "White bow tee", "category": "tops", "image_path": "https://img/bow-tee.jpg"},
                    {"id": "jacket-id", "name": "Cape jacket", "category": "outerwear", "image_path": "https://img/cape.jpg"},
                ],
                "image_urls": ["https://img/bow-tee.jpg", "https://img/cape.jpg"],
                "styling_notes": "Playful brunch layers.",
                "visualization_url": "https://viz/brunch.jpg",
            },
        ]
    }
    manager.save_state(state)
    return manager


def matcher(user_id, names):
    return [
        {"id": f"matched-{index}", "name": name, "category": "other", "image_path": f"https://matched/{index}.jpg", "matched": True}
        for index, name in enumerate(names, start=1)
    ]


def test_whatsapp_numbered_like_e2e_saves_active_pack_records_without_real_sms(mock_redis):
    from api import sms

    phone = "whatsapp:+15551234567"
    seed_active_pack(phone)
    FakeSavedOutfitsManager.saved = []
    FakeSavedOutfitsManager.visualizations = []
    client = FakeOpenAIClient([
        tool_response("save_outfit", {
            "reasoning": "The user explicitly liked active-pack outfits 1 and 3.",
            "active_pack_indices": [1, 3],
        }),
        text_response("Saved outfits 1 and 3."),
    ])

    with patch("openai.OpenAI", return_value=client), \
         patch("api.sms.preload_user_context", return_value=""), \
         patch("api.sms.send_sms") as send_sms, \
         patch("services.agent_logger.log_agent_turn"), \
         patch("services.saved_outfits_manager.SavedOutfitsManager", FakeSavedOutfitsManager), \
         patch("primitives.matching.match_items_to_wardrobe", side_effect=matcher):
        asyncio.run(sms.process_outfit_request("test", phone, "I like outfit 1 and 3"))

    system_prompt = client.requests[0]["messages"][0]["content"]
    tool_result = json.loads(client.requests[1]["messages"][-1]["content"])
    assert "# Explicit Save Intent" in system_prompt
    assert tool_result["outfit_ids"] == ["saved-1", "saved-2"]
    assert [saved["occasion"] for saved in FakeSavedOutfitsManager.saved] == [
        "First day at work", "Brunch with Andy",
    ]
    assert [item["name"] for item in FakeSavedOutfitsManager.saved[0]["items"]] == [
        "White ruffled blouse", "Black wide-leg trousers",
    ]
    assert [item["name"] for item in FakeSavedOutfitsManager.saved[1]["items"]] == [
        "White bow tee", "Cape jacket",
    ]
    assert all(item["id"] != "unknown" and item["image_path"] for saved in FakeSavedOutfitsManager.saved for item in saved["items"])
    assert FakeSavedOutfitsManager.visualizations == [
        ("saved-1", "https://viz/first-day.jpg"),
        ("saved-2", "https://viz/brunch.jpg"),
    ]
    send_sms.assert_called_once_with(phone, "Saved outfits 1 and 3.")


def test_whatsapp_profile_update_e2e_persists_before_confirmation(mock_redis):
    from api import sms

    phone = "whatsapp:+15551234567"
    FakeProfileManager.profile = {"style_words": ["Classic", "Playful", "Relaxed"]}
    FakeProfileManager.saved_data = None
    client = FakeOpenAIClient([
        tool_response("update_profile", {
            "reasoning": "The user approved new style words and a note about flowy silhouettes.",
            "three_words": {
                "current": "Feminine",
                "aspirational": "Whimsical",
                "feeling": "Grounded",
            },
            "style_note": "Open to flowy silhouettes when they still feel grounded.",
        }),
        text_response("Done. Your profile is updated."),
    ])

    with patch("openai.OpenAI", return_value=client), \
         patch("api.sms.preload_user_context", return_value=""), \
         patch("api.sms.send_sms") as send_sms, \
         patch("services.agent_logger.log_agent_turn"), \
         patch("services.activity_logger.log_activity") as log_activity, \
         patch("services.user_profile_manager.UserProfileManager", FakeProfileManager):
        asyncio.run(sms.process_outfit_request(
            "test",
            phone,
            "Please update my profile to feminine, whimsical, grounded, with a note that flowy should still feel grounded.",
        ))

    assert FakeProfileManager.saved_data["three_words"] == {
        "current": "Feminine",
        "aspirational": "Whimsical",
        "feeling": "Grounded",
    }
    assert FakeProfileManager.saved_data["style_notes"] == [
        "Open to flowy silhouettes when they still feel grounded.",
    ]
    log_activity.assert_called_once()
    send_sms.assert_called_once_with(phone, "Done. Your profile is updated.")
