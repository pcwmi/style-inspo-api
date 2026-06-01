import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def mock_redis():
    storage = {}
    mock = MagicMock()
    mock.get = lambda key: storage.get(key)
    mock.setex = lambda key, ttl, value: storage.update({key: value})

    with patch("services.conversation_state.Redis") as redis_cls:
        redis_cls.from_url.return_value = mock
        yield storage


@pytest.mark.parametrize(
    ("capsule", "outfit_texts", "expected_labels"),
    [
        (
            "WOFs: sneakers + denim jacket repeat; tops shift the mood.",
            [
                "Day 1 travel: cozy island layers.",
                "Day 2 light hike: same anchors, easier top.",
                "Dinner: birthday polish without overpacking.",
            ],
            ["Day 1", "Day 2", "Dinner"],
        ),
        (
            "WOFs: flat sandals + raffia tote repeat; linen handles the heat.",
            [
                "Day 1 beach arrival: light linen, easy sandals.",
                "Day 2 resort dinner: same tote, sharper dress.",
                "Day 3 market morning: repeat sandals, breezier top.",
            ],
            ["Day 1", "Day 2", "Day 3"],
        ),
        (
            "WOFs: black loafers + trench repeat; work pieces carry Spokane weather.",
            [
                "Day 1 meetings: structured but walkable.",
                "Day 2 dinner: same trench, softer base.",
                "Day 3 travel: repeat loafers, relaxed knit.",
            ],
            ["Day 1", "Day 2", "Day 3"],
        ),
    ],
)
def test_packing_sms_sequence_defers_and_labels_visualizations(mock_redis, capsule, outfit_texts, expected_labels):
    from agent.output import StatefulSMSOutput
    from services.conversation_state import ConversationState, ConversationStateManager

    phone = "+15551234567"
    manager = ConversationStateManager(phone)
    manager.save_state(ConversationState(user_id="test", phone=phone))

    sent = []

    def fake_sms(to, body):
        sent.append(("sms", body))

    def fake_mms(to, body, images):
        sent.append(("mms", body, images))

    day1_names = ["Grey cashmere sweater", "Straight jeans", "White and Red Leather Sneakers", "Denim jacket"]
    day2_names = ["Black tee", "Straight jeans", "White and Red Leather Sneakers", "Denim jacket"]
    dinner_names = ["Burgundy floral dress", "Taupe ankle boots", "Brown suede crossbody", "Gold swirl earrings"]

    with patch("services.twilio_service.send_sms", side_effect=fake_sms), \
         patch("services.twilio_service.send_mms", side_effect=fake_mms), \
         patch("services.collage.generate_outfit_collage", side_effect=lambda user_id, images, **_: f"https://collage/{images[0]}"), \
         patch("time.sleep"), \
         patch.object(StatefulSMSOutput, "_trigger_background_visualization") as trigger:
        output = StatefulSMSOutput(phone=phone, user_id="test", state_manager=manager)
        output.send(capsule, [])
        output.present_outfit(
            outfit_texts[0],
            ["d1-top", "d1-jeans", "d1-shoes", "d1-jacket"],
            visualize=True,
            item_names=day1_names,
        )
        output.present_outfit(
            outfit_texts[1],
            ["d2-top", "d2-jeans", "d2-shoes", "d2-jacket"],
            visualize=True,
            item_names=day2_names,
        )
        output.present_outfit(
            outfit_texts[2],
            ["d3-dress", "d3-boots", "d3-bag", "d3-earrings"],
            visualize=True,
            item_names=dinner_names,
        )

        assert trigger.call_count == 0
        output.flush_pending_visualizations()

    sms_bodies = [body for kind, body, *_ in sent if kind == "sms"]
    assert sms_bodies[0] == capsule
    assert sms_bodies[1] == outfit_texts[0]
    assert sms_bodies[2] == outfit_texts[1]
    assert sms_bodies[3] == outfit_texts[2]
    assert sms_bodies[4] == "I'll send the on-person views as they're ready."
    assert not any("Generating a styled version" in body for body in sms_bodies)

    labels = [call.kwargs["label"] for call in trigger.call_args_list]
    assert labels == expected_labels

    state = manager.get_state()
    outfits = state.active_pack["outfits"]
    assert [outfit["label"] for outfit in outfits] == expected_labels
    assert outfits[0]["item_names"] == day1_names
    assert outfits[1]["item_names"] == day2_names
    assert outfits[2]["item_names"] == dinner_names


def test_constrained_jacket_edit_locks_rest_and_replaces_day(mock_redis):
    from agent.edit_intent import build_constrained_edit_hint
    from agent.output import StatefulSMSOutput
    from services.conversation_state import ConversationState, ConversationStateManager

    phone = "+15551234567"
    manager = ConversationStateManager(phone)
    manager.save_state(ConversationState(user_id="test", phone=phone))

    original = ["Grey cashmere sweater", "Straight jeans", "White and Red Leather Sneakers", "Denim jacket"]
    replacement = ["Grey cashmere sweater", "Straight jeans", "White and Red Leather Sneakers", "Blue trench coat"]

    with patch("services.twilio_service.send_sms"), \
         patch("services.twilio_service.send_mms"), \
         patch("services.collage.generate_outfit_collage", return_value="https://collage/day1"), \
         patch("time.sleep"):
        output = StatefulSMSOutput(phone=phone, user_id="test", state_manager=manager)
        output.present_outfit(
            "Day 1 travel: first version.",
            ["top", "jeans", "shoes", "jacket"],
            visualize=True,
            item_names=original,
        )

    active_pack = manager.get_state().active_pack
    hint = build_constrained_edit_hint(
        "I only asked to change the jacket on day 1, the rest looks good.",
        active_pack,
    )
    assert "Only replace: Denim jacket" in hint
    assert "Grey cashmere sweater, Straight jeans, White and Red Leather Sneakers" in hint
    assert "Do not rewrite other days" in hint

    with patch("services.twilio_service.send_sms"), \
         patch("services.twilio_service.send_mms"), \
         patch("services.collage.generate_outfit_collage", return_value="https://collage/day1b"), \
         patch("time.sleep"):
        output = StatefulSMSOutput(phone=phone, user_id="test", state_manager=manager)
        output.present_outfit(
            "Day 1 travel: only the jacket changes.",
            ["top", "jeans", "shoes", "trench"],
            visualize=True,
            item_names=replacement,
        )

    outfits = manager.get_state().active_pack["outfits"]
    assert len(outfits) == 1
    assert outfits[0]["label"] == "Day 1"
    assert outfits[0]["item_names"] == replacement


def test_new_capsule_message_starts_fresh_active_pack(mock_redis):
    from agent.output import StatefulSMSOutput
    from services.conversation_state import ConversationState, ConversationStateManager

    phone = "+15551234567"
    manager = ConversationStateManager(phone)
    manager.save_state(ConversationState(user_id="test", phone=phone))

    with patch("services.twilio_service.send_sms"), \
         patch("services.twilio_service.send_mms"), \
         patch("services.collage.generate_outfit_collage", return_value="https://collage"), \
         patch("time.sleep"):
        output = StatefulSMSOutput(phone=phone, user_id="test", state_manager=manager)
        output.send("WOFs: sneakers repeat.", [])
        output.present_outfit("Day 1 travel", ["a", "b"], visualize=True, item_names=["Tee", "Sneakers"])
        output.present_outfit("Day 4 final dinner", ["c", "d"], visualize=True, item_names=["Dress", "Sneakers"])

        assert [o["label"] for o in manager.get_state().active_pack["outfits"]] == ["Day 1", "Day 4"]

        next_output = StatefulSMSOutput(phone=phone, user_id="test", state_manager=manager)
        next_output.send("WOFs: loafers repeat.", [])
        next_output.present_outfit("Day 1 meetings", ["e", "f"], visualize=True, item_names=["Blazer", "Loafers"])

    outfits = manager.get_state().active_pack["outfits"]
    assert [o["label"] for o in outfits] == ["Day 1"]
    assert outfits[0]["item_names"] == ["Blazer", "Loafers"]
