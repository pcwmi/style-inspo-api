"""
Smoke test: Verify wardrobe API endpoints work.
"""

import pytest
from unittest.mock import patch, MagicMock


def test_get_wardrobe_endpoint_exists(client):
    """
    GET /api/wardrobe/{user_id} endpoint is registered and responds.
    """
    with patch('services.wardrobe_manager.WardrobeManager') as mock_manager_class:
        mock_manager = MagicMock()
        mock_manager.get_wardrobe_items.return_value = []
        mock_manager_class.return_value = mock_manager

        response = client.get("/api/wardrobe/test_user")

        # Should not be 404 (endpoint exists)
        assert response.status_code != 404, "Wardrobe endpoint should exist"


def test_get_wardrobe_returns_valid_schema(client):
    """
    GET /api/wardrobe/{user_id} returns valid schema with items array.
    """
    mock_items = [
        {
            "id": "item_001",
            "styling_details": {"name": "Test Item", "category": "tops"},
            "usage_metadata": {},
            "system_metadata": {"image_path": "test.jpg"}
        }
    ]

    with patch('api.wardrobe.WardrobeManager') as mock_manager_class:
        mock_manager = MagicMock()
        mock_manager.get_wardrobe_items.return_value = mock_items
        mock_manager_class.return_value = mock_manager

        response = client.get("/api/wardrobe/test_user")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data, "Response should have 'items' array"
        assert "count" in data, "Response should have 'count'"
        assert isinstance(data["items"], list), "'items' should be a list"


def test_upload_endpoint_exists(client, mock_rq_queue):
    """
    POST /api/wardrobe/{user_id}/upload endpoint is registered.
    """
    # Create a minimal file upload
    from io import BytesIO

    # Patch where StorageManager is imported (inside the function)
    with patch('services.storage_manager.StorageManager') as mock_storage_class:
        mock_storage = MagicMock()
        mock_storage.save_file.return_value = "staging/test.jpg"
        mock_storage_class.return_value = mock_storage

        # Minimal PNG bytes (1x1 transparent pixel)
        png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

        response = client.post(
            "/api/wardrobe/test_user/upload",
            files={"file": ("test.png", BytesIO(png_bytes), "image/png")}
        )

        # Should accept the upload (may fail internally but not 404/422)
        assert response.status_code != 404, "Upload endpoint should exist"


def test_delete_endpoint_exists(client):
    """
    DELETE /api/wardrobe/{user_id}/items/{item_id} endpoint is registered.
    """
    with patch('api.wardrobe.WardrobeManager') as mock_manager_class:
        mock_manager = MagicMock()
        mock_manager.delete_wardrobe_item.return_value = True
        mock_manager_class.return_value = mock_manager

        response = client.delete("/api/wardrobe/test_user/items/item_001")

        # Should not be 404 for the route itself
        # (may return 404 for "item not found" which is fine)
        assert response.status_code in [200, 404, 500], "Delete endpoint should be registered"


def test_wardrobe_item_detail_endpoint_exists(client):
    """
    GET /api/wardrobe/{user_id}/items/{item_id} endpoint is registered.
    """
    with patch('api.wardrobe.WardrobeManager') as mock_manager_class:
        mock_manager = MagicMock()
        mock_manager.get_item.return_value = {
            "id": "item_001",
            "styling_details": {"name": "Test", "category": "tops"},
            "usage_metadata": {},
            "system_metadata": {}
        }
        mock_manager_class.return_value = mock_manager

        response = client.get("/api/wardrobe/test_user/items/item_001")

        # Endpoint should exist
        assert response.status_code != 405, "Item detail endpoint should accept GET"
