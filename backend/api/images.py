from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import Response
from services.image_processor import image_processor
import io

router = APIRouter(prefix="/api/images", tags=["images"])

@router.post("/remove-background")
async def remove_background(
    image_file: UploadFile = File(...),
    user_id: str = Query(..., description="User ID for saving the processed image"),
    save: bool = Query(True, description="Whether to save the processed image")
):
    """
    Remove background from an uploaded image.
    Returns the processed image as PNG bytes.
    """
    try:
        # Read image content
        content = await image_file.read()
        
        # Process image
        processed_image_bytes = image_processor.remove_background(content)
        
        if save:
            # Save to storage (optional, depending on workflow)
            # For now, we just return the bytes so the frontend can display it
            # or upload it as a new version.
            pass

        return Response(content=processed_image_bytes, media_type="image/png")

    except Exception as e:
        print(f"Error removing background: {e}")
        raise HTTPException(status_code=500, detail=str(e))
