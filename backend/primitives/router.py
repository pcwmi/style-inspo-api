"""
Primitives Router - Aggregates all primitive endpoints.

Mounts at /primitives/* alongside existing /api/* endpoints.
Uses Strangler Fig pattern: new primitives coexist with old API.
"""

from fastapi import APIRouter

from primitives.items import router as items_router
from primitives.profile import router as profile_router
from primitives.feedback import router as feedback_router
from primitives.outfits import router as outfits_router
from primitives.considering import router as considering_router

primitives_router = APIRouter()

# Mount domain-specific routers
primitives_router.include_router(items_router, prefix="/items", tags=["primitives-items"])
primitives_router.include_router(profile_router, prefix="/profile", tags=["primitives-profile"])
primitives_router.include_router(feedback_router, prefix="/feedback", tags=["primitives-feedback"])
primitives_router.include_router(outfits_router, prefix="/outfits", tags=["primitives-outfits"])
primitives_router.include_router(considering_router, prefix="/considering", tags=["primitives-considering"])
