"""
Smoke test: Verify the FastAPI app starts without import errors.
This catches broken imports, syntax errors, and circular dependencies.
"""

import pytest


def test_fastapi_app_loads():
    """App module loads without import errors."""
    # This will fail if there are import errors, circular imports, or syntax errors
    from main import app
    assert app is not None
    assert app.title == "Style Inspo API"


def test_all_routers_registered():
    """All API routers are registered on the app."""
    from main import app

    # Get all registered routes
    routes = [route.path for route in app.routes]

    # Verify critical routes exist
    assert "/" in routes, "Root health check missing"
    assert "/health" in routes, "Health endpoint missing"

    # Check API route prefixes are registered
    route_str = str(routes)
    assert "/api/wardrobe" in route_str, "Wardrobe router not registered"
    assert "/api/outfits" in route_str, "Outfits router not registered"
    assert "/api/jobs" in route_str, "Jobs router not registered"


def test_health_endpoint(client):
    """Health endpoint responds correctly."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint(client):
    """Root endpoint responds correctly."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
