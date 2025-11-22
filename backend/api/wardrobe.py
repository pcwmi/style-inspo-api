"""
Wardrobe API endpoints
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List
import logging

from services.wardrobe_manager import WardrobeManager
from services.image_analyzer import create_image_analyzer
from models.schemas import WardrobeResponse, WardrobeItemResponse
from workers.outfit_worker import analyze_item_job
from core.redis import get_redis_connection
from rq import Queue

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy initialization of RQ queue (only when needed)
def get_analysis_queue():
    """Get or create analysis queue"""
    redis_conn = get_redis_connection()
    return Queue('analysis', connection=redis_conn)


@router.get("/wardrobe/{user_id}", response_model=WardrobeResponse)
async def get_wardrobe(user_id: str):
    """Get user's wardrobe items"""
    try:
        manager = WardrobeManager(user_id=user_id)
        items = manager.get_wardrobe_items("all")
        
        return {
            "items": items,
            "count": len(items)
        }
    except Exception as e:
        logger.error(f"Error getting wardrobe for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wardrobe/{user_id}/upload")
async def upload_item(
    user_id: str,
    file: UploadFile = File(...),
    use_real_ai: bool = Form(True)
):
    """Upload new wardrobe item - returns job_id for analysis"""
    try:
        # Save file to staging storage (accessible by worker)
        from services.storage_manager import StorageManager
        storage = StorageManager(user_id=user_id)
        
        # Create a file-like object from the upload
        content = await file.read()
        from io import BytesIO
        file_obj = BytesIO(content)
        
        # Save to staging area
        staging_filename = f"staging/{file.filename}"
        file_path = storage.save_file(file_obj, staging_filename)
        
        # Enqueue analysis job
        analysis_queue = get_analysis_queue()
        job = analysis_queue.enqueue(
            analyze_item_job,
            user_id=user_id,
            file_path=file_path,
            filename=file.filename,
            use_real_ai=use_real_ai,
            job_timeout=120  # 2 minutes max
        )
        
        return {
            "job_id": job.id,
            "status": "processing",
            "message": "Image uploaded, analysis in progress"
        }
    except Exception as e:
        logger.error(f"Error uploading item for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/wardrobe/{user_id}/items/{item_id}")
async def delete_item(user_id: str, item_id: str):
    """Delete wardrobe item"""
    try:
        manager = WardrobeManager(user_id=user_id)
        success = manager.delete_wardrobe_item(item_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return {"success": True, "message": "Item deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting item {item_id} for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wardrobe/{user_id}/items/{item_id}")
async def get_item(user_id: str, item_id: str):
    """Get single wardrobe item"""
    try:
        manager = WardrobeManager(user_id=user_id)
        items = manager.get_wardrobe_items("all")
        
        for item in items:
            if item.get("id") == item_id:
                return item
        
        raise HTTPException(status_code=404, detail="Item not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting item {item_id} for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


