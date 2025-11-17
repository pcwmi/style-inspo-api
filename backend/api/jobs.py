"""
Job status API endpoints
"""

from fastapi import APIRouter, HTTPException
import logging

from models.schemas import JobStatusResponse
from core.redis import get_redis_connection
from rq.job import Job

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Poll job status"""
    try:
        redis_conn = get_redis_connection()
        job = Job.fetch(job_id, connection=redis_conn)
        
        if job.is_finished:
            return {
                "status": "complete",
                "progress": 100,
                "result": job.result
            }
        elif job.is_failed:
            return {
                "status": "failed",
                "progress": 0,
                "error": str(job.exc_info) if job.exc_info else "Job failed"
            }
        else:
            # Job is still processing
            progress = job.meta.get("progress", 0) if hasattr(job, "meta") else 0
            return {
                "status": "processing",
                "progress": progress
            }
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}")
        raise HTTPException(status_code=404, detail="Job not found")


