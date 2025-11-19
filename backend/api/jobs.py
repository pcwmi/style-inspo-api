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
            # Extract error message from exception info
            error_msg = "Job failed"
            if job.exc_info:
                # exc_info is a tuple: (exception_type, exception_value, traceback)
                if isinstance(job.exc_info, tuple) and len(job.exc_info) >= 2:
                    error_msg = str(job.exc_info[1])  # exception_value
                else:
                    error_msg = str(job.exc_info)
            elif hasattr(job, "meta") and job.meta.get("error"):
                error_msg = job.meta.get("error")
            
            return {
                "status": "failed",
                "progress": job.meta.get("progress", 0) if hasattr(job, "meta") else 0,
                "error": error_msg
            }
        else:
            # Job is still processing or queued
            progress = job.meta.get("progress", 0) if hasattr(job, "meta") else 0
            status = "processing" if job.get_status() == "started" else "queued"
            return {
                "status": status,
                "progress": progress
            }
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}")
        # Check if it's a NoSuchJobError specifically
        if "NoSuchJobError" in str(type(e).__name__) or "No such job" in str(e):
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found. It may have expired or never existed.")
        raise HTTPException(status_code=404, detail=f"Job not found: {str(e)}")


