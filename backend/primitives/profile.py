"""
Profile Primitives - User profile CRUD operations.

Primitives:
- get_profile(user_id) -> Profile
- update_profile(user_id, profile_data) -> Profile
- update_descriptor(user_id, descriptor) -> Profile
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging

from services.user_profile_manager import UserProfileManager

logger = logging.getLogger(__name__)
router = APIRouter()


class ThreeWords(BaseModel):
    """Three-word style identity"""
    current: str
    aspirational: str
    feeling: str


class ProfileUpdate(BaseModel):
    """Profile update fields"""
    three_words: Optional[ThreeWords] = None
    daily_emotion: Optional[Dict[str, str]] = None


class DescriptorUpdate(BaseModel):
    """Model descriptor update"""
    descriptor: str


# --- READ PRIMITIVES ---

@router.get("/{user_id}")
async def get_profile(user_id: str) -> Dict[str, Any]:
    """
    Get user profile.

    Args:
        user_id: User identifier

    Returns:
        {"profile": {...}} or {"profile": null} if not found
    """
    manager = UserProfileManager(user_id=user_id)
    profile = manager.get_profile(user_id)

    # Convert style_words array to three_words dict for consistency
    if profile and "style_words" in profile:
        words = profile.get("style_words", [])
        if len(words) >= 3:
            profile["three_words"] = {
                "current": words[0],
                "aspirational": words[1],
                "feeling": words[2]
            }

    return {"profile": profile}


# --- WRITE PRIMITIVES ---

@router.put("/{user_id}")
async def update_profile(user_id: str, updates: ProfileUpdate) -> Dict[str, Any]:
    """
    Update user profile.

    Args:
        user_id: User identifier
        updates: Profile fields to update

    Returns:
        {"profile": updated_profile}
    """
    manager = UserProfileManager(user_id=user_id)

    # Convert to dict, excluding None values
    update_dict = {}

    if updates.three_words:
        update_dict["three_words"] = updates.three_words.model_dump()

    if updates.daily_emotion:
        update_dict["daily_emotion"] = updates.daily_emotion

    if not update_dict:
        raise HTTPException(status_code=400, detail="No updates provided")

    success = manager.save_profile(update_dict)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update profile")

    # Fetch updated profile
    profile = manager.get_profile(user_id)

    # Convert style_words to three_words
    if profile and "style_words" in profile:
        words = profile.get("style_words", [])
        if len(words) >= 3:
            profile["three_words"] = {
                "current": words[0],
                "aspirational": words[1],
                "feeling": words[2]
            }

    return {"profile": profile}


@router.put("/{user_id}/descriptor")
async def update_descriptor(user_id: str, update: DescriptorUpdate) -> Dict[str, Any]:
    """
    Update model descriptor for visualization.

    Args:
        user_id: User identifier
        update: Descriptor text

    Returns:
        {"profile": updated_profile}
    """
    manager = UserProfileManager(user_id=user_id)

    success = manager.save_profile({"model_descriptor": update.descriptor})

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update descriptor")

    profile = manager.get_profile(user_id)
    return {"profile": profile}
