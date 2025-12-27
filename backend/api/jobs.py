"""
Job status API endpoints
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
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


@router.get("/jobs/{job_id}/stream")
async def stream_job_updates(job_id: str):
    """
    Stream job updates via Server-Sent Events (SSE).

    Sends events:
    - progress: {progress: number, message: string, current_outfit: number}
    - outfit: {outfit_number: number} (when outfit generation phase changes)
    - complete: {result: object} (when job finishes)
    - error: {error: string} (if job fails)
    """

    async def event_generator():
        redis_conn = get_redis_connection()

        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except Exception as e:
            logger.error(f"SSE: Job {job_id} not found: {e}")
            yield f"event: error\ndata: {json.dumps({'error': 'Job not found'})}\n\n"
            return

        last_progress = -1
        last_outfit = 0

        # Poll job status every 500ms
        while True:
            try:
                job.refresh()
                status = job.get_status()

                # Send progress updates
                meta = job.meta or {}
                current_progress = meta.get('progress', 0)
                current_outfit = meta.get('current_outfit', 0)
                status_message = meta.get('status_message', '')

                # Emit progress event if changed
                if current_progress > last_progress:
                    progress_data = {
                        'progress': current_progress,
                        'message': status_message,
                        'current_outfit': current_outfit
                    }
                    yield f"event: progress\ndata: {json.dumps(progress_data)}\n\n"
                    last_progress = current_progress

                # Emit outfit event if we moved to next outfit
                if current_outfit > last_outfit and current_outfit <= 3:
                    outfit_data = {'outfit_number': current_outfit}
                    yield f"event: outfit\ndata: {json.dumps(outfit_data)}\n\n"
                    last_outfit = current_outfit

                # Check if job is complete
                if status == 'finished':
                    result = job.result
                    yield f"event: complete\ndata: {json.dumps(result)}\n\n"
                    break

                elif status == 'failed':
                    error_message = "Job failed"
                    if job.exc_info:
                        if isinstance(job.exc_info, tuple) and len(job.exc_info) >= 2:
                            error_message = str(job.exc_info[1])
                        else:
                            error_message = str(job.exc_info)
                    elif meta.get('error'):
                        error_message = meta.get('error')
                    yield f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
                    break

                # Wait before next poll
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"SSE: Error polling job {job_id}: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


