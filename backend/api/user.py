"""
User profile API endpoints
"""

from fastapi import APIRouter, HTTPException
import logging

from models.schemas import ProfileUpdate, ProfileResponse, DescriptorRequest, DescriptorResponse
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
        
        # Convert style_words array to three_words dict format
        three_words = None
        style_words = profile.get("style_words")
        if style_words and isinstance(style_words, list) and len(style_words) >= 3:
            three_words = {
                "current": style_words[0],
                "aspirational": style_words[1],
                "feeling": style_words[2]
            }
        
        return {
            "user_id": user_id,
            "three_words": three_words,
            "daily_emotion": profile.get("daily_emotion"),
            "model_descriptor": profile.get("model_descriptor"),
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


@router.post("/user/descriptor", response_model=DescriptorResponse)
async def save_descriptor(request: DescriptorRequest):
    """
    Save user's model descriptor for outfit visualization.

    The descriptor is a free-text description of the user's physical appearance
    used to generate relatable model visualizations.

    Examples:
    - "5'4\", Asian, shoulder-length black hair, not skinny but not fat either"
    - "5'8\", Black woman, natural curls, curvy with hips"
    - "5'6\", medium skin, athletic build, short brown hair"
    """
    try:
        logger.info(f"Saving descriptor for user {request.user_id}")

        if not request.descriptor or not request.descriptor.strip():
            raise HTTPException(
                status_code=400,
                detail="Descriptor cannot be empty"
            )

        profile_manager = UserProfileManager(user_id=request.user_id)

        # Save descriptor to profile
        success = profile_manager.save_profile({
            "model_descriptor": request.descriptor.strip()
        })

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save descriptor")

        return DescriptorResponse(
            status="saved",
            descriptor=request.descriptor.strip()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving descriptor for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


