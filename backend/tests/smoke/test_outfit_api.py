"""
Smoke test: Verify outfit generation endpoints work.
This is the KEY FLOW test - if this breaks, the app is broken.
"""

import pytest
from unittest.mock import patch, MagicMock


def test_generate_outfit_endpoint_accepts_request(client, mock_rq_queue):
    """
    POST /api/outfits/generate accepts a valid request and returns job_id.
    This catches: endpoint registration, schema validation, queue setup.
    """
    response = client.post("/api/outfits/generate", json={
        "user_id": "test_user",
        "mode": "occasion",
        "occasions": ["casual weekend"]
    })

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert "job_id" in data, "Response should include job_id"
    assert "status" in data, "Response should include status"
    assert data["status"] == "queued", "Status should be 'queued'"
    assert "prompt_version" in data, "Response should include prompt_version"


def test_generate_outfit_complete_mode(client, mock_rq_queue):
    """
    POST /api/outfits/generate works in 'complete' mode with anchor items.
    """
    response = client.post("/api/outfits/generate", json={
        "user_id": "test_user",
        "mode": "complete",
        "anchor_items": ["item_001", "item_002"]
    })

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data


def test_generate_outfit_validates_mode(client, mock_rq_queue):
    """
    POST /api/outfits/generate validates the mode parameter.
    """
    response = client.post("/api/outfits/generate", json={
        "user_id": "test_user",
        "mode": "invalid_mode"
    })

    # Pydantic should reject invalid mode
    assert response.status_code == 422, "Invalid mode should return 422"


def test_generate_outfit_requires_user_id(client, mock_rq_queue):
    """
    POST /api/outfits/generate requires user_id.
    """
    response = client.post("/api/outfits/generate", json={
        "mode": "occasion",
        "occasions": ["casual"]
    })

    assert response.status_code == 422, "Missing user_id should return 422"


def test_outfit_stream_endpoint_exists(client):
    """
    GET /api/outfits/generate/stream endpoint is registered.
    This is a quick check - full streaming test would be more complex.
    """
    # Just check the endpoint exists (will fail without required params)
    response = client.get("/api/outfits/generate/stream")

    # Should return 422 (missing required params), not 404
    assert response.status_code == 422, f"Expected 422 for missing params, got {response.status_code}"


def test_save_outfit_endpoint_exists(client):
    """
    POST /api/outfits/save endpoint is registered.
    """
    response = client.post("/api/outfits/save", json={
        "user_id": "test_user",
        "outfit": {
            "items": [{"name": "Test Item", "category": "tops"}],
            "styling_notes": "Test notes",
            "why_it_works": "Test reason",
            "confidence_level": "medium",
            "vibe_keywords": ["test"]
        }
    })

    # May fail due to storage, but should not be 404 or 422
    assert response.status_code != 404, "Save endpoint should exist"


def test_dislike_outfit_endpoint_exists(client):
    """
    POST /api/outfits/dislike endpoint is registered.
    """
    response = client.post("/api/outfits/dislike", json={
        "user_id": "test_user",
        "outfit": {
            "items": [{"name": "Test Item", "category": "tops"}],
            "styling_notes": "Test notes",
            "why_it_works": "Test reason",
            "confidence_level": "medium",
            "vibe_keywords": ["test"]
        },
        "reasons": ["not my style"]
    })

    # May fail due to storage, but should not be 404 or 422
    assert response.status_code != 404, "Dislike endpoint should exist"
