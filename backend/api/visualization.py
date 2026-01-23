"""
Visualization API endpoints for outfit visualization on model.
"""

from fastapi import APIRouter, HTTPException
import logging

from models.schemas import VisualizationRequest, VisualizationResponse, JobStatusResponse
from workers.visualization_worker import visualize_outfit_job
from core.redis import get_redis_connection
from rq import Queue
from services.activity_logger import log_activity

router = APIRouter()
logger = logging.getLogger(__name__)


def get_outfit_queue():
    """Get or create outfit queue (reuse existing queue for visualization)"""
    redis_conn = get_redis_connection()
    return Queue('outfits', connection=redis_conn)


@router.post("/visualization/generate", response_model=VisualizationResponse)
async def generate_visualization(request: VisualizationRequest):
    """
    Start outfit visualization generation.

    Enqueues a background job to generate an AI visualization of the outfit
    on a relatable model matching the user's physical description.

    Prerequisites:
    - User must have a saved model descriptor (POST /user/descriptor first)
    - Outfit must be saved (in user's saved outfits)

    Args:
        request: VisualizationRequest with user_id and outfit_id

    Returns:
        VisualizationResponse with job_id to poll for status

    Cost: ~$0.08 per generation (Runway ML Gen-4 Image API)
    Time: ~30-40 seconds
    """
    try:
        logger.info(f"Visualization request: user={request.user_id}, outfit={request.outfit_id}")

        # Validate user has descriptor
        from services.user_profile_manager import UserProfileManager
        profile_manager = UserProfileManager(user_id=request.user_id)
        profile = profile_manager.get_profile(request.user_id)

        if not profile or not profile.get('model_descriptor'):
            raise HTTPException(
                status_code=400,
                detail="Please add your description first to generate visualizations"
            )

        # Validate outfit exists
        from services.saved_outfits_manager import SavedOutfitsManager
        outfit_manager = SavedOutfitsManager(user_id=request.user_id)
        outfit = outfit_manager.get_outfit_by_id(request.outfit_id)

        if not outfit:
            raise HTTPException(
                status_code=404,
                detail=f"Outfit {request.outfit_id} not found"
            )

        # Check if already visualized (and not force regenerate)
        existing_viz_url = outfit.get('visualization_url')
        if existing_viz_url and not request.force_regenerate:
            logger.info(f"Outfit {request.outfit_id} already visualized, returning existing")
            return VisualizationResponse(
                job_id="cached",
                status="complete",
                estimated_time=0,
                visualization_url=existing_viz_url
            )

        # Enqueue visualization job
        queue = get_outfit_queue()
        job = queue.enqueue(
            visualize_outfit_job,
            request.user_id,
            request.outfit_id,
            request.provider or "runway",
            job_timeout=120  # 2 minute timeout
        )

        logger.info(f"Enqueued visualization job {job.id}")

        # Log activity
        log_activity(request.user_id, "visualization_started", {
            "outfit_id": request.outfit_id,
            "job_id": job.id,
            "provider": request.provider or "runway"
        })

        return VisualizationResponse(
            job_id=job.id,
            status="queued",
            estimated_time=40
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting visualization: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
