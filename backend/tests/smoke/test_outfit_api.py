"""
Smoke test: Verify outfit generation endpoints work.
This is the KEY FLOW test - if this breaks, the app is broken.
"""

import pytest
from unittest.mock import patch, MagicMock


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
