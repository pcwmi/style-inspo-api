"""
Background worker for outfit visualization generation.

Wraps VisualizationManager to run in RQ background queue.
"""

import os
import sys
import logging
import time
from rq import get_current_job

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

logger = logging.getLogger(__name__)


def visualize_outfit_job(user_id: str, outfit_id: str, provider_name: str = "runway") -> dict:
    """
    Background job for outfit visualization generation.

    This is a thin wrapper around VisualizationManager.visualize_outfit()
    that adds RQ job progress tracking.

    Args:
        user_id: User identifier
        outfit_id: ID of the saved outfit to visualize
        provider_name: Visualization provider (default: "runway")

    Returns:
        Dict with:
            - success: bool
            - image_url: str (permanent S3 URL)
            - generation_time: float
            - provider: str
            - metadata: dict

    Raises:
        ValueError: If outfit not found or no descriptor
        Exception: If visualization generation fails
    """
    job = get_current_job()
    start_time = time.time()

    try:
        logger.info(f"Starting visualization job: user={user_id}, outfit={outfit_id}")

        # Update progress: starting
        if job:
            job.meta['progress'] = 10
            job.meta['status_message'] = "Loading outfit data..."
            job.save_meta()

        # Import here to avoid circular imports
        from services.visualization.visualization_manager import VisualizationManager
        from services.user_profile_manager import UserProfileManager

        # Check if user has model descriptor
        profile_manager = UserProfileManager(user_id=user_id)
        profile = profile_manager.get_profile(user_id)
        model_descriptor = profile.get('model_descriptor', '') if profile else ''

        if not model_descriptor:
            raise ValueError("Please add your description first to generate visualizations")

        if job:
            job.meta['progress'] = 20
            job.meta['status_message'] = "Preparing visualization request..."
            job.save_meta()

        # Initialize manager and generate
        manager = VisualizationManager(user_id)

        if job:
            job.meta['progress'] = 30
            job.meta['status_message'] = "Generating visualization with AI..."
            job.save_meta()

        # This is the long-running part (~30-40s)
        result = manager.visualize_outfit(outfit_id, provider_name)

        if job:
            job.meta['progress'] = 90
            job.meta['status_message'] = "Saving visualization..."
            job.save_meta()

        # Add latency to result
        result['latency_ms'] = int((time.time() - start_time) * 1000)

        if job:
            job.meta['progress'] = 100
            job.meta['status_message'] = "Complete!"
            job.save_meta()

        logger.info(f"Visualization job completed: outfit={outfit_id}, latency={result['latency_ms']}ms")
        return result

    except Exception as e:
        logger.error(f"Error in visualize_outfit_job: {e}", exc_info=True)
        if job:
            job.meta['error'] = str(e)
            job.meta['status_message'] = f"Failed: {str(e)}"
            job.save_meta()
        raise
