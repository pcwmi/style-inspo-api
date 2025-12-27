"""
Consider Buying API Endpoints
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import logging
import os

from services.consider_buying_manager import ConsiderBuyingManager
from services.product_extractor import ProductExtractor
from services.wardrobe_manager import WardrobeManager
from services.image_analyzer import create_image_analyzer
from services.storage_manager import StorageManager
from workers.outfit_worker import generate_consider_buying_job
from core.redis import get_redis_connection
from rq import Queue
from fastapi import Query, Body
from io import BytesIO
from starlette.datastructures import UploadFile as StarletteUploadFile

logger = logging.getLogger(__name__)

router = APIRouter(tags=["consider-buying"])

# Lazy initialization of RQ queue (only when needed)
def get_outfit_queue():
    """Get or create outfit queue"""
    redis_conn = get_redis_connection()
    return Queue('outfits', connection=redis_conn)


class ExtractRequest(BaseModel):
    url: str


class DecisionRequest(BaseModel):
    item_id: str
    decision: str  # bought | passed | later
    reason: Optional[str] = None


class ConsideringItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    colors: Optional[List[str]] = None
    cut: Optional[str] = None
    texture: Optional[str] = None
    style: Optional[str] = None
    fit: Optional[str] = None
    brand: Optional[str] = None
    trend_status: Optional[str] = None
    styling_notes: Optional[str] = None
    fabric: Optional[str] = None
    price: Optional[float] = None
    source_url: Optional[str] = None


@router.post("/consider-buying/extract-url")
async def extract_from_url(request: ExtractRequest, user_id: str = Query(...)):
    """
    Extract product information from URL

    Returns: {
        success: bool,
        data: {image_url, title, price, brand} or None,
        error: str or None
    }
    """
    extractor = ProductExtractor()
    success, data, error = extractor.extract_from_url(request.url)

    if success:
        return {"success": True, "data": data, "error": None}
    else:
        return {"success": False, "data": None, "error": error}


@router.post("/consider-buying/add-item")
async def add_item(
    image_file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    category: Optional[str] = Form(None),  # Added category parameter
    brand: Optional[str] = Form(None),  # Added brand parameter
    price: Optional[float] = Form(None),
    source_url: Optional[str] = Form(None),
    user_id: str = Form(...),
    item_id: Optional[str] = Form(None)
):
    """Add an item to consider buying list (from file or URL)"""
    try:
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        
        # Validate that we have either a file or a URL
        if not image_file and not image_url:
            raise HTTPException(status_code=400, detail="Either image_file or image_url must be provided")

        # If we have a URL but no file, download the image
        if image_url and not image_file:
            extractor = ProductExtractor()
            success, image, error = extractor.download_image(image_url)
            
            if not success:
                raise HTTPException(status_code=400, detail=f"Failed to download image: {error}")
            
            # Convert PIL Image to bytes for add_item
            img_byte_arr = BytesIO()
            # Determine format based on original image or default to JPEG
            image_format = image.format if image.format else 'JPEG'
            
            # Handle RGBA to JPEG conversion
            if image.mode in ('RGBA', 'LA') and image_format == 'JPEG':
                image = image.convert('RGB')
                
            image.save(img_byte_arr, format=image_format)
            img_byte_arr.seek(0)
            
            # Create a file-like object that behaves like UploadFile
            # Pass headers to set content-type
            headers = {"content-type": f"image/{image_format.lower()}"}
            image_file = StarletteUploadFile(
                file=img_byte_arr,
                filename=f"downloaded_image.{image_format.lower()}",
                headers=headers
            )

        # Analyze image
        analyzer = create_image_analyzer(use_real_ai=True)
        # Ensure the file pointer is at the beginning for analysis
        if hasattr(image_file.file, 'seek'):
            image_file.file.seek(0)
            
        # Pass name as product_title to help AI identify the correct item
        analysis_data = analyzer.analyze_clothing_item(image_file.file, product_title=name)
        
        # Override name if provided (ensure it's set even if AI returns something else)
        if name:
            analysis_data['name'] = name
            
        # Override category if provided
        if category:
            analysis_data['category'] = category
            
        # Override brand if provided (from URL extraction)
        if brand:
            analysis_data['brand'] = brand

        # Add to consider_buying
        # Ensure the file pointer is at the beginning for saving
        if hasattr(image_file.file, 'seek'):
            image_file.file.seek(0)
        item_data = cb_manager.add_item(
            analysis_data=analysis_data,
            image=image_file.file,
            price=price,
            source_url=source_url
        )

        # Find similar items in wardrobe
        wardrobe_manager = WardrobeManager(user_id=user_id)
        wardrobe_items = wardrobe_manager.get_wardrobe_items("all")

        similar_items = cb_manager.find_similar_items(item_data, wardrobe_items)

        # Store similar item IDs in item data
        item_data["similar_items_in_wardrobe"] = [s["item"]["id"] for s in similar_items]
        cb_manager._save_consider_buying_data()

        return {
            "item": item_data,
            "similar_items": similar_items
        }

    except Exception as e:
        logger.error(f"Error adding item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consider-buying/generate-outfits")
async def generate_outfits(
    item_id: str = Form(...),
    use_existing_similar: bool = Form(False),
    user_id: str = Form(...),
    include_reasoning: bool = Form(False)
):
    """
    Generate outfits with consider_buying item (background job).

    Returns job_id immediately. Client should poll /api/jobs/{job_id} for results.
    """
    try:
        # Enqueue outfit generation job
        outfit_queue = get_outfit_queue()
        job = outfit_queue.enqueue(
            generate_consider_buying_job,
            user_id=user_id,
            item_id=item_id,
            use_existing_similar=use_existing_similar,
            include_reasoning=include_reasoning,
            job_timeout=120  # 2 minutes max
        )

        logger.info(f"Enqueued consider-buying job {job.id} for user {user_id}")

        return {
            "job_id": job.id,
            "status": "queued",
            "estimated_time": 30  # seconds
        }

    except Exception as e:
        logger.error(f"Error enqueueing consider-buying job: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consider-buying/decide")
async def record_decision(request: DecisionRequest, user_id: str = Query(...)):
    """
    Record user's buying decision

    decision: "bought" | "passed" | "later"
    """
    try:
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        
        # Get item info before recording decision (item might be removed after decision)
        consider_item = next((i for i in cb_manager.get_items() if i["id"] == request.item_id), None)
        if not consider_item:
            raise HTTPException(status_code=404, detail="Item not found in consider_buying")
        
        item_name = consider_item.get('styling_details', {}).get('name', 'Item')
        item_price = consider_item.get('price', 0)
        
        decision_record = cb_manager.record_decision(
            item_id=request.item_id,
            decision=request.decision,
            reason=request.reason
        )

        # If bought, move to wardrobe
        if request.decision == "bought":
            from services.wardrobe_manager import WardrobeManager
            from services.image_analyzer import create_image_analyzer
            from io import BytesIO
            import requests
            from PIL import Image
            
            # Download the image from storage (consider_item already fetched above)
            image_path = consider_item.get("image_path")
            if not image_path:
                raise HTTPException(status_code=400, detail="Item has no image path")
            
            # Download image (works for both S3 URLs and local paths)
            if image_path.startswith("http"):
                # S3 URL - download it
                import requests
                img_response = requests.get(image_path)
                img_response.raise_for_status()
                image_file = BytesIO(img_response.content)
            else:
                # Local path - open it
                storage = StorageManager(storage_type=os.getenv("STORAGE_TYPE", "local"), user_id=user_id)
                # For local storage, construct the full path
                if hasattr(storage, 'base_path'):
                    full_path = os.path.join(storage.base_path, "consider_buying", os.path.basename(image_path))
                else:
                    full_path = os.path.join("wardrobe_photos", user_id, "consider_buying", os.path.basename(image_path))
                image_file = open(full_path, 'rb')
            
            # Convert to analysis_data format
            analysis_data = {
                'name': consider_item.get('styling_details', {}).get('name', 'Unnamed Item'),
                'category': consider_item.get('styling_details', {}).get('category', 'tops'),
                'sub_category': consider_item.get('styling_details', {}).get('sub_category', 'Unknown'),
                'colors': consider_item.get('styling_details', {}).get('colors', []),
                'cut': consider_item.get('styling_details', {}).get('cut', 'Unknown'),
                'texture': consider_item.get('styling_details', {}).get('texture', 'Unknown'),
                'style': consider_item.get('styling_details', {}).get('style', 'casual'),
                'fit': consider_item.get('styling_details', {}).get('fit', 'Unknown'),
                'brand': consider_item.get('styling_details', {}).get('brand'),
                'trend_status': consider_item.get('styling_details', {}).get('trend_status', 'Unknown'),
                'styling_notes': consider_item.get('styling_details', {}).get('styling_notes', ''),
                'fabric': consider_item.get('structured_attrs', {}).get('fabric', 'unknown'),
                'sleeve_length': consider_item.get('structured_attrs', {}).get('sleeve_length'),
                'waist_level': consider_item.get('structured_attrs', {}).get('waist_level'),
            }
            
            # Add to wardrobe (as regular wear, not styling challenge)
            wardrobe_manager = WardrobeManager(user_id=user_id)
            wardrobe_item = wardrobe_manager.add_wardrobe_item(
                uploaded_file=image_file,
                analysis_data=analysis_data,
                is_styling_challenge=False
            )
            
            if not wardrobe_item:
                raise HTTPException(status_code=500, detail="Failed to add item to wardrobe")
            
            # Remove from consider_buying (or mark as moved)
            items = cb_manager.consider_buying_data.get("items", [])
            items.remove(consider_item)
            cb_manager._save_consider_buying_data()
            
            logger.info(f"Moved item {request.item_id} from consider_buying to wardrobe as {wardrobe_item['id']}")

        # Return decision with item info for all decisions
        return {
            "success": True,
            "decision": decision_record,
            "stats": cb_manager.get_stats(),
            "item": {
                "name": item_name,
                "price": item_price
            }
        }

    except Exception as e:
        logger.error(f"Error recording decision: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consider-buying/list")
async def list_items(user_id: str = Query(...), status: Optional[str] = None):
    """
    List items in consider_buying bucket

    Optional filter by status: "considering" | "bought" | "passed"
    """
    cb_manager = ConsiderBuyingManager(user_id=user_id)
    items = cb_manager.get_items(status=status)
    return {"items": items}


@router.get("/consider-buying/stats")
async def get_stats(user_id: str = Query(...)):
    """Get buying decision stats"""
    cb_manager = ConsiderBuyingManager(user_id=user_id)
    return cb_manager.get_stats()


@router.delete("/consider-buying/item/{item_id}")
async def delete_item(item_id: str, user_id: str = Query(...)):
    """
    Delete an item from consider_buying
    """
    try:
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        cb_manager.delete_item(item_id)
        
        return {
            "success": True,
            "message": "Item deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/consider-buying/all")
async def delete_all_items(user_id: str = Query(...)):
    """
    Delete all items from consider_buying for a user
    """
    try:
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        items = cb_manager.get_items()
        deleted_count = len(items)

        # Clear all items
        cb_manager.consider_buying_data["items"] = []
        cb_manager._save_consider_buying_data()

        return {
            "success": True,
            "message": f"Deleted {deleted_count} items successfully",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error deleting all items: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/consider-buying/item/{item_id}")
async def update_considering_item(item_id: str, user_id: str = Query(...), updates: ConsideringItemUpdate = Body(...)):
    """
    Update considering item details
    """
    try:
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        # Convert Pydantic model to dict, excluding None values
        update_data = {k: v for k, v in updates.dict().items() if v is not None}

        updated_item = cb_manager.update_considering_item(item_id, update_data)

        if not updated_item:
            raise HTTPException(status_code=404, detail="Item not found")

        return updated_item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating considering item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consider-buying/item/{item_id}/rotate")
async def rotate_considering_item(item_id: str, user_id: str = Query(...), degrees: int = 90):
    """
    Rotate considering item image by specified degrees (default 90 clockwise)
    """
    try:
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        new_path = cb_manager.rotate_considering_item_image(item_id, degrees)

        if not new_path:
            raise HTTPException(status_code=404, detail="Item not found or rotation failed")

        return {"success": True, "new_image_path": new_path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating considering item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
