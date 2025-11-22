"""
Outfit generation API endpoints
"""

from fastapi import APIRouter, HTTPException
import logging

from models.schemas import OutfitRequest, OutfitGenerationResponse, SaveOutfitRequest, DislikeOutfitRequest
from workers.outfit_worker import generate_outfits_job
from services.saved_outfits_manager import SavedOutfitsManager
from services.disliked_outfits_manager import DislikedOutfitsManager
from core.redis import get_redis_connection
from rq import Queue

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy initialization of RQ queue (only when needed)
def get_outfit_queue():
    """Get or create outfit queue"""
    redis_conn = get_redis_connection()
    return Queue('outfits', connection=redis_conn)


@router.post("/outfits/generate", response_model=OutfitGenerationResponse)
async def generate_outfits(request: OutfitRequest):
    """Generate outfits (background job)"""
    try:
        # Enqueue outfit generation job
        outfit_queue = get_outfit_queue()
        job = outfit_queue.enqueue(
            generate_outfits_job,
            user_id=request.user_id,
            occasions=request.occasions,
            weather_condition=request.weather_condition,
            temperature_range=request.temperature_range,
            mode=request.mode,
            anchor_items=request.anchor_items,
            mock=request.mock,
            job_timeout=120  # 2 minutes max
        )
        
        return {
            "job_id": job.id,
            "status": "queued",
            "estimated_time": 30  # seconds
        }
    except Exception as e:
        logger.error(f"Error enqueueing outfit generation for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        success = manager.save_outfit(
            outfit_combo=outfit_wrapper,
            reason=", ".join(request.feedback) if request.feedback else "",
            context=outfit_wrapper.context
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save outfit")
        
        return {"success": True, "message": "Outfit saved"}
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
        
        return {"success": True, "message": "Feedback recorded"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disliking outfit for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


