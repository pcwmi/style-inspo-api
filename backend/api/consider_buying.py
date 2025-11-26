"""
Consider Buying API Endpoints
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import logging

from services.consider_buying_manager import ConsiderBuyingManager
from services.product_extractor import ProductExtractor
from services.wardrobe_manager import WardrobeManager
from services.image_analyzer import create_image_analyzer
from services.style_engine import StyleGenerationEngine
from fastapi import Query, Body
from io import BytesIO
from starlette.datastructures import UploadFile as StarletteUploadFile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/consider-buying", tags=["consider-buying"])


class ExtractRequest(BaseModel):
    url: str


class DecisionRequest(BaseModel):
    item_id: str
    decision: str  # bought | passed | later
    reason: Optional[str] = None


@router.post("/extract-url")
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


@router.post("/add-item")
async def add_item(
    image_file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    category: Optional[str] = Form(None),  # Added category parameter
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


@router.post("/generate-outfits")
async def generate_outfits(
    item_id: str = Form(...),
    use_existing_similar: bool = Form(False),
    user_id: str = Form(...)
):
    """
    Generate outfits with consider_buying item

    If use_existing_similar=True, use similar items from wardrobe instead
    """
    try:
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        wardrobe_manager = WardrobeManager(user_id=user_id)

        # Get consider_buying item
        consider_item = next((i for i in cb_manager.get_items() if i["id"] == item_id), None)
        if not consider_item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Get wardrobe items
        wardrobe_items = wardrobe_manager.get_wardrobe_items("all")

        # Get user profile
        # Hardcoded for testing as requested
        user_profile = {
            "three_words": {
                "current": "classic",
                "aspirational": "relaxed",
                "feeling": "playful"
            }
        }

        # Determine anchor items
        if use_existing_similar:
            # Use similar items from wardrobe
            similar_item_ids = consider_item.get("similar_items_in_wardrobe", [])
            anchor_items = [item for item in wardrobe_items if item["id"] in similar_item_ids]
        else:
            # Use consider_buying item as anchor
            anchor_items = [consider_item]

        # Generate outfits
        engine = StyleGenerationEngine()
        combinations = engine.generate_outfit_combinations(
            user_profile=user_profile,
            available_items=wardrobe_items,
            styling_challenges=anchor_items,
            occasion=None,
            weather_condition=None,
            temperature_range=None
        )

        return {
            "outfits": combinations,
            "anchor_items": anchor_items
        }

    except Exception as e:
        logger.error(f"Error generating outfits: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating outfits: {str(e)}")


@router.post("/decide")
async def record_decision(request: DecisionRequest, user_id: str = Query(...)):
    """
    Record user's buying decision

    decision: "bought" | "passed" | "later"
    """
    try:
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        decision_record = cb_manager.record_decision(
            item_id=request.item_id,
            decision=request.decision,
            reason=request.reason
        )

        # If bought, move to wardrobe
        if request.decision == "bought":
            # TODO: Move item from consider_buying to wardrobe
            pass

        return {
            "success": True,
            "decision": decision_record,
            "stats": cb_manager.get_stats()
        }

    except Exception as e:
        logger.error(f"Error recording decision: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_items(user_id: str = Query(...), status: Optional[str] = None):
    """
    List items in consider_buying bucket

    Optional filter by status: "considering" | "bought" | "passed"
    """
    cb_manager = ConsiderBuyingManager(user_id=user_id)
    items = cb_manager.get_items(status=status)
    return {"items": items}


@router.get("/stats")
async def get_stats(user_id: str = Query(...)):
    """Get buying decision stats"""
    cb_manager = ConsiderBuyingManager(user_id=user_id)
    return cb_manager.get_stats()
