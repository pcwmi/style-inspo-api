"""
Outfit CRUD API endpoints (save, dislike, viz-status, saved, mark-worn, etc.)

Outfit generation is handled by the agent path (agent_web.py, sms.py, agent_api.py).
"""

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from PIL import Image, ImageOps
from io import BytesIO

from models.schemas import SaveOutfitRequest, DislikeOutfitRequest, MarkWornRequest, MarkWornResponse
from services.saved_outfits_manager import SavedOutfitsManager
from services.disliked_outfits_manager import DislikedOutfitsManager
from services.activity_logger import log_activity
from services.storage_manager import StorageManager
from services.visualization.viz_trigger import trigger_background_visualization

router = APIRouter()
logger = logging.getLogger(__name__)


def log_generation_to_s3(
    user_id: str,
    mode: str,
    outfits: list,
    occasion: str = None,
    anchor_items: list = None,
    anchor_item_names: list = None,
    device_id: str = None
):
    """
    Log outfit generation to S3 for analytics/daily digest.
    Appends to daily log file: {user_id}/generations/{YYYY-MM-DD}.json
    """
    try:
        storage_type = os.getenv("STORAGE_TYPE", "local")
        storage = StorageManager(storage_type=storage_type, user_id=user_id)

        # Get today's date for the log file
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_filename = f"generations/{today}.json"

        # Load existing log for today (or empty list)
        try:
            existing_data = storage.load_json(log_filename)
            generations = existing_data.get("generations", [])
        except Exception:
            generations = []

        # Create generation log entry
        generation_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "outfits": outfits
        }

        # Add device_id for analytics filtering (to separate real users from admin testing)
        if device_id:
            generation_entry["device_id"] = device_id

        # Add mode-specific context
        if mode == "occasion" and occasion:
            generation_entry["occasion"] = occasion
        elif mode == "complete" and anchor_items:
            generation_entry["anchor_item_ids"] = anchor_items
            if anchor_item_names:
                generation_entry["anchor_item_names"] = anchor_item_names

        # Append to today's log
        generations.append(generation_entry)

        # Save back to S3
        storage.save_json({"generations": generations}, log_filename)
        logger.info(f"Logged generation for {user_id}: {mode} mode, {len(outfits)} outfits")

        # Also log to unified activity log
        log_activity(user_id, "outfit_generated", {
            "mode": mode,
            "outfit_count": len(outfits),
            "occasion": occasion if mode == "occasion" else None,
            "anchor_items": anchor_item_names if mode == "complete" else None
        })

    except Exception as e:
        # Don't fail the request if logging fails
        logger.error(f"Failed to log generation for {user_id}: {e}")


class OutfitDictWrapper:
    """Simple wrapper to convert dict to object-like structure for managers"""
    def __init__(self, outfit_dict: dict):
        self.items = outfit_dict.get("items", [])
        self.styling_notes = outfit_dict.get("styling_notes", "")
        self.why_it_works = outfit_dict.get("why_it_works", "")
        self.confidence_level = outfit_dict.get("confidence_level", "medium")
        self.vibe_keywords = outfit_dict.get("vibe_keywords", [])
        self.context = outfit_dict.get("context")


@router.post("/outfits/save")
async def save_outfit(request: SaveOutfitRequest):
    """Save outfit to favorites"""
    try:
        manager = SavedOutfitsManager(user_id=request.user_id)
        outfit_wrapper = OutfitDictWrapper(request.outfit)
        outfit_id = manager.save_outfit(
            outfit_combo=outfit_wrapper,
            reason=", ".join(request.feedback) if request.feedback else "",
            context=outfit_wrapper.context
        )

        if not outfit_id:
            raise HTTPException(status_code=500, detail="Failed to save outfit")

        # Log activity
        log_activity(request.user_id, "outfit_saved", {
            "outfit_id": outfit_id,
            "reason": ", ".join(request.feedback) if request.feedback else "",
            "item_count": len(outfit_wrapper.items)
        })

        # Persist visualization URL if already generated, or mark pending if still running
        viz_key = request.outfit.get("viz_key")
        if viz_key and outfit_id:
            from services.visualization.viz_cache import get_viz_status
            viz_status = get_viz_status(viz_key)
            if viz_status.get("status") == "complete" and viz_status.get("url"):
                manager.update_outfit_visualization(outfit_id, viz_status["url"])
                logger.info(f"Persisted viz URL from Redis to saved outfit {outfit_id}")
            elif viz_status.get("status") == "pending":
                # Viz is actually running — set pending so frontend polls
                manager.set_visualization_pending(outfit_id, viz_key=viz_key)
                logger.info(f"Viz still pending for saved outfit {outfit_id}")
            # If failed or unknown, leave pending=false (default)

        return {"success": True, "message": "Outfit saved", "outfit_id": outfit_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving outfit for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outfits/dislike")
async def dislike_outfit(request: DislikeOutfitRequest):
    """Dislike outfit with feedback"""
    try:
        manager = DislikedOutfitsManager(user_id=request.user_id)
        outfit_wrapper = OutfitDictWrapper(request.outfit)
        success = manager.dislike_outfit(
            outfit_combo=outfit_wrapper,
            reason=request.reason or "",
            context=outfit_wrapper.context
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to record dislike")

        # Log activity
        log_activity(request.user_id, "outfit_disliked", {
            "reason": request.reason or "",
            "item_count": len(outfit_wrapper.items)
        })

        return {"success": True, "message": "Feedback recorded"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disliking outfit for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outfits/{outfit_id}/viz-status")
async def get_visualization_status(outfit_id: str, user: str = Query(..., description="User ID")):
    """Get visualization status for an outfit (for web polling)"""
    try:
        manager = SavedOutfitsManager(user_id=user)
        outfit = manager.get_outfit_by_id(outfit_id)

        if not outfit:
            raise HTTPException(status_code=404, detail="Outfit not found")

        pending = outfit.get("visualization_pending", False)
        url = outfit.get("visualization_url")

        # If DB says pending but no URL, check Redis for the actual viz status
        if pending and not url:
            viz_key = outfit.get("viz_key")
            if viz_key:
                from services.visualization.viz_cache import get_viz_status as get_redis_viz_status
                redis_status = get_redis_viz_status(viz_key)
                if redis_status.get("status") == "complete" and redis_status.get("url"):
                    # Viz completed but DB wasn't updated — fix it now
                    url = redis_status["url"]
                    pending = False
                    try:
                        manager.update_outfit_visualization(outfit_id, url)
                        logger.info(f"Recovered viz URL from Redis for outfit {outfit_id}")
                    except Exception:
                        pass
                elif redis_status.get("status") == "failed":
                    # Viz failed — clear DB pending flag
                    pending = False
                    try:
                        manager.clear_visualization_pending(
                            outfit_id, error=redis_status.get("error", "Visualization failed")
                        )
                        logger.info(f"Cleared pending flag for failed viz on outfit {outfit_id}")
                    except Exception:
                        pass

            # Fallback: stale timeout (90s safety net)
            if pending and not url:
                saved_at = outfit.get("saved_at", "")
                if saved_at:
                    from datetime import datetime, timezone
                    try:
                        saved_time = datetime.fromisoformat(saved_at.replace("Z", "+00:00"))
                        if (datetime.now(timezone.utc) - saved_time).total_seconds() > 90:
                            pending = False
                            try:
                                manager.clear_visualization_pending(
                                    outfit_id, error="Visualization timed out"
                                )
                            except Exception:
                                pass
                    except (ValueError, TypeError):
                        pending = False

        return {
            "pending": pending,
            "url": url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching viz status for outfit {outfit_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/visualization/status/{viz_key}")
async def get_visualization_status_by_key(viz_key: str):
    """
    Get visualization status by viz_key (for reveal page polling).

    This endpoint is used by the web flow when outfits are generated but not yet saved.
    The viz_key is a hash of the garment image URLs, returned with each outfit during streaming.
    """
    from services.visualization.viz_cache import get_viz_status
    return get_viz_status(viz_key)


@router.get("/outfits/{user_id}/saved")
async def get_saved_outfits(user_id: str):
    """Get all saved outfits for a user"""
    try:
        manager = SavedOutfitsManager(user_id=user_id)
        saved_outfits = manager.get_saved_outfits()
        return {"outfits": saved_outfits, "count": len(saved_outfits)}
    except Exception as e:
        logger.error(f"Error fetching saved outfits for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outfits/{user_id}/disliked")
async def get_disliked_outfits(user_id: str):
    """Get all disliked outfits for a user"""
    try:
        manager = DislikedOutfitsManager(user_id=user_id)
        disliked_outfits = manager.get_disliked_outfits()
        return {"outfits": disliked_outfits, "count": len(disliked_outfits)}
    except Exception as e:
        logger.error(f"Error fetching disliked outfits for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outfits/{outfit_id}/mark-worn", response_model=MarkWornResponse)
async def mark_outfit_worn(outfit_id: str, request: MarkWornRequest):
    """Mark an outfit as worn"""
    try:
        manager = SavedOutfitsManager(user_id=request.user_id)
        updated = manager.mark_outfit_worn(outfit_id)

        if not updated:
            raise HTTPException(status_code=404, detail="Outfit not found")

        # Log activity
        log_activity(request.user_id, "outfit_marked_worn", {
            "outfit_id": outfit_id
        })

        return MarkWornResponse(
            success=True,
            outfit_id=outfit_id,
            worn_at=updated.get("worn_at", ""),
            worn_photo_url=updated.get("worn_photo_url")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking outfit worn for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outfits/{user_id}/not-worn")
async def get_not_worn_outfits(user_id: str, limit: int = None):
    """Get saved outfits that haven't been worn yet"""
    try:
        manager = SavedOutfitsManager(user_id=user_id)
        not_worn = manager.get_not_worn_outfits(limit=limit)
        return {"outfits": not_worn, "count": len(not_worn)}
    except Exception as e:
        logger.error(f"Error fetching not-worn outfits for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outfits/{user_id}/worn")
async def get_worn_outfits(user_id: str):
    """Get saved outfits that have been worn"""
    try:
        manager = SavedOutfitsManager(user_id=user_id)
        worn = manager.get_worn_outfits()
        return {"outfits": worn, "count": len(worn)}
    except Exception as e:
        logger.error(f"Error fetching worn outfits for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outfits/{outfit_id}/worn-photo")
async def upload_worn_photo(
    outfit_id: str,
    user_id: str = Query(..., description="User ID"),
    file: UploadFile = File(..., description="Photo of user wearing the outfit")
):
    """Upload a photo of the user wearing an outfit and mark it as worn"""
    try:
        # Read and process image
        contents = await file.read()
        image = Image.open(BytesIO(contents))

        # Apply EXIF orientation to ensure correct display
        image = ImageOps.exif_transpose(image)

        # Convert RGBA to RGB if needed (for JPEG compatibility)
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')

        # Save to storage with unique filename
        storage_type = os.getenv("STORAGE_TYPE", "local")
        storage = StorageManager(storage_type=storage_type, user_id=user_id)

        filename = f"worn_{outfit_id}_{uuid.uuid4().hex[:8]}.jpg"
        photo_url = storage.save_image(image, filename, subfolder="worn_photos")

        # Mark outfit as worn with the photo URL
        manager = SavedOutfitsManager(user_id=user_id)
        updated = manager.mark_outfit_worn(outfit_id, worn_photo_url=photo_url)

        if not updated:
            raise HTTPException(status_code=404, detail="Outfit not found")

        # Log activity
        log_activity(user_id, "worn_photo_uploaded", {
            "outfit_id": outfit_id,
            "photo_url": photo_url
        })

        return {
            "success": True,
            "outfit_id": outfit_id,
            "worn_at": updated.get("worn_at", ""),
            "worn_photo_url": photo_url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading worn photo for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


