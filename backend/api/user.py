"""
User profile API endpoints
"""

from fastapi import APIRouter, HTTPException
import logging

from models.schemas import ProfileUpdate, ProfileResponse
from services.user_profile_manager import UserProfileManager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/users/{user_id}/profile", response_model=ProfileResponse)
async def get_profile(user_id: str):
    """Get user style profile"""
    try:
        profile_manager = UserProfileManager(user_id=user_id)
        profile = profile_manager.get_profile(user_id)
        
        if not profile:
            return {
                "user_id": user_id,
                "three_words": None,
                "daily_emotion": None,
                "created_at": None,
                "updated_at": None
            }
        
        return {
            "user_id": user_id,
            "three_words": profile.get("three_words"),
            "daily_emotion": profile.get("daily_emotion"),
            "created_at": profile.get("created_at"),
            "updated_at": profile.get("updated_at")
        }
    except Exception as e:
        logger.error(f"Error getting profile for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/profile")
async def update_profile(user_id: str, profile: ProfileUpdate):
    """Update user style profile"""
    try:
        profile_manager = UserProfileManager(user_id=user_id)
        
        # Build profile dict
        profile_data = {}
        if profile.three_words:
            profile_data["three_words"] = profile.three_words
        if profile.daily_emotion:
            profile_data["daily_emotion"] = profile.daily_emotion
        
        success = profile_manager.save_profile(profile_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save profile")
        
        return {"success": True, "message": "Profile updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


