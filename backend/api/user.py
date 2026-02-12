"""
User profile API endpoints
"""

from fastapi import APIRouter, HTTPException
import logging

from models.schemas import ProfileUpdate, ProfileResponse, DescriptorRequest, DescriptorResponse
from services.user_profile_manager import UserProfileManager
from services.activity_logger import log_activity

router = APIRouter()
logger = logging.getLogger(__name__)

# Reserved usernames that cannot be used
RESERVED_USERNAMES = {
    "admin", "api", "system", "root", "default", "user", "test",
    "null", "undefined", "anonymous", "guest", "support", "help",
    "style", "inspo", "styleinspo", "wardrobe", "outfit", "profile"
}


@router.get("/users/check-username/{username}")
async def check_username(username: str):
    """
    Check if a username is available for registration.

    Validates:
    - Length: 3-20 characters
    - Format: lowercase alphanumeric and underscores only
    - Not reserved
    - Not already taken (no existing profile in S3)
    """
    import re

    # Normalize to lowercase
    username = username.lower().strip()

    # Validate length
    if len(username) < 3:
        return {"available": False, "reason": "Username must be at least 3 characters"}
    if len(username) > 20:
        return {"available": False, "reason": "Username must be 20 characters or less"}

    # Validate format (lowercase alphanumeric + underscores)
    if not re.match(r'^[a-z0-9_]+$', username):
        return {"available": False, "reason": "Only lowercase letters, numbers, and underscores allowed"}

    # Check reserved usernames
    if username in RESERVED_USERNAMES:
        return {"available": False, "reason": "This username is reserved"}

    # Check if profile already exists
    try:
        profile_manager = UserProfileManager(user_id=username)
        existing_profile = profile_manager.get_profile(username)

        if existing_profile:
            # Suggest alternative
            suggestion = f"{username}_{hash(username) % 1000:03d}"
            return {"available": False, "reason": "Username already taken", "suggestion": suggestion}

        return {"available": True}
    except Exception as e:
        logger.error(f"Error checking username {username}: {e}")
        # If we can't check, assume available (will fail at creation if taken)
        return {"available": True}


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
            "display_name": profile.get("display_name"),
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
        if profile.display_name:
            profile_data["display_name"] = profile.display_name

        success = profile_manager.save_profile(profile_data)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save profile")

        # Log activity
        if profile.three_words:
            log_activity(user_id, "style_words_updated", {
                "current": profile.three_words.get("current"),
                "aspirational": profile.three_words.get("aspirational"),
                "feeling": profile.three_words.get("feeling")
            })

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

        # Log activity
        log_activity(request.user_id, "descriptor_saved", {
            "descriptor_length": len(request.descriptor.strip())
        })

        return DescriptorResponse(
            status="saved",
            descriptor=request.descriptor.strip()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving descriptor for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


