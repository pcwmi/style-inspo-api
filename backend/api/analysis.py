"""
Analysis API endpoints.

Provides endpoints for triggering and managing daily usage analysis.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import HTMLResponse

from services.daily_analysis import run_daily_analysis, run_daily_analysis_preview

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple auth token for cron job protection
ANALYSIS_API_TOKEN = os.getenv("ANALYSIS_API_TOKEN", "")


def verify_token(token: str) -> bool:
    """Verify the API token for cron endpoints."""
    if not ANALYSIS_API_TOKEN:
        # If no token configured, allow in development
        logger.warning("ANALYSIS_API_TOKEN not configured - endpoint unprotected")
        return True
    return token == ANALYSIS_API_TOKEN


@router.post("/analysis/daily")
async def trigger_daily_analysis(
    background_tasks: BackgroundTasks,
    date: Optional[str] = Query(None, description="Date to analyze (YYYY-MM-DD). Defaults to yesterday."),
    token: Optional[str] = Query(None, description="API token for authentication")
):
    """
    Trigger daily usage analysis.

    This endpoint is designed to be called by a cron job (GitHub Actions).
    It runs analysis in the background and sends results via email.

    Args:
        date: Optional date to analyze (YYYY-MM-DD format). Defaults to yesterday.
        token: API token for authentication (required in production)

    Returns:
        Status indicating analysis was started
    """
    # Verify token in production
    if ANALYSIS_API_TOKEN and not verify_token(token or ""):
        raise HTTPException(status_code=401, detail="Invalid or missing API token")

    logger.info(f"Daily analysis triggered for date: {date or 'yesterday'}")

    # Run in background to avoid timeout
    background_tasks.add_task(_run_analysis_task, date)

    return {
        "status": "started",
        "date": date or "yesterday",
        "message": "Analysis running in background. Results will be emailed."
    }


@router.get("/analysis/daily")
async def run_daily_analysis_sync(
    date: Optional[str] = Query(None, description="Date to analyze (YYYY-MM-DD). Defaults to yesterday."),
    token: Optional[str] = Query(None, description="API token for authentication"),
    preview: bool = Query(False, description="Return HTML preview instead of JSON stats")
):
    """
    Run daily analysis synchronously and return results.

    Useful for testing and debugging. For production cron jobs, use POST endpoint.

    Args:
        date: Optional date to analyze (YYYY-MM-DD format). Defaults to yesterday.
        token: API token for authentication (required in production)
        preview: If true, returns HTML email content for preview

    Returns:
        Analysis results (JSON) or HTML preview
    """
    # Verify token in production
    if ANALYSIS_API_TOKEN and not verify_token(token or ""):
        raise HTTPException(status_code=401, detail="Invalid or missing API token")

    logger.info(f"Daily analysis (sync) triggered for date: {date or 'yesterday'}, preview={preview}")

    try:
        if preview:
            html_content = await run_daily_analysis_preview(date)
            return HTMLResponse(content=html_content)
        else:
            result = await run_daily_analysis(date)
            return result
    except Exception as e:
        logger.error(f"Error running daily analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _run_analysis_task(date: Optional[str] = None):
    """Background task wrapper for analysis."""
    try:
        result = await run_daily_analysis(date)
        logger.info(f"Daily analysis completed: {result}")
    except Exception as e:
        logger.error(f"Error in daily analysis background task: {e}")
