"""
Outfits Primitives - Saved outfit CRUD operations.

Primitives:
- save_outfit(user_id, outfit_data, reason) -> Outfit
- get_saved_outfits(user_id) -> List[Outfit]
- get_outfit(user_id, outfit_id) -> Outfit
- delete_outfit(user_id, outfit_id) -> bool
- mark_worn(user_id, outfit_id, photo_url?) -> Outfit
- upload_worn_photo(user_id, outfit_id, photo) -> Outfit
- get_not_worn_outfits(user_id) -> List[Outfit]
- get_worn_outfits(user_id) -> List[Outfit]
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging

from services.saved_outfits_manager import SavedOutfitsManager
from services.storage_manager import StorageManager
import os
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()


class OutfitItem(BaseModel):
    """Item in an outfit"""
    id: Optional[str] = None
    name: str
    category: Optional[str] = None
    image_path: Optional[str] = None


class OutfitData(BaseModel):
    """Outfit structure"""
    items: List[OutfitItem]
    styling_notes: Optional[str] = None
    why_it_works: Optional[str] = None
    confidence_level: Optional[str] = None
    vibe_keywords: Optional[List[str]] = None


class SaveOutfitRequest(BaseModel):
    """Request body for saving an outfit"""
    outfit_data: OutfitData
    reason: str = ""
    occasion: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class MarkWornRequest(BaseModel):
    """Request body for marking outfit as worn"""
    worn_photo_url: Optional[str] = None


class OutfitCombo:
    """Simple adapter for SavedOutfitsManager.save_outfit()"""

    def __init__(self, outfit_data: OutfitData):
        self.items = [item.model_dump() for item in outfit_data.items]
        self.styling_notes = outfit_data.styling_notes or ""
        self.why_it_works = outfit_data.why_it_works or ""
        self.confidence_level = outfit_data.confidence_level or ""
        self.vibe_keywords = outfit_data.vibe_keywords or []


# --- READ PRIMITIVES ---

@router.get("/{user_id}")
async def get_saved_outfits(user_id: str) -> Dict[str, Any]:
    """
    Get all saved outfits for a user.

    Args:
        user_id: User identifier

    Returns:
        {"outfits": [...], "count": int}
    """
    manager = SavedOutfitsManager(user_id=user_id)
    outfits = manager.get_saved_outfits(enrich_with_current_images=True)
    return {"outfits": outfits, "count": len(outfits)}


@router.get("/{user_id}/not-worn")
async def get_not_worn_outfits(user_id: str, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Get saved outfits that haven't been worn yet (Ready to Wear).

    Args:
        user_id: User identifier
        limit: Max number to return

    Returns:
        {"outfits": [...], "count": int}
    """
    manager = SavedOutfitsManager(user_id=user_id)
    outfits = manager.get_not_worn_outfits(limit=limit, enrich_with_current_images=True)
    return {"outfits": outfits, "count": len(outfits)}


@router.get("/{user_id}/worn")
async def get_worn_outfits(user_id: str) -> Dict[str, Any]:
    """
    Get outfits that have been worn.

    Args:
        user_id: User identifier

    Returns:
        {"outfits": [...], "count": int}
    """
    manager = SavedOutfitsManager(user_id=user_id)
    outfits = manager.get_worn_outfits(enrich_with_current_images=True)
    return {"outfits": outfits, "count": len(outfits)}


@router.get("/{user_id}/{outfit_id}")
async def get_outfit(user_id: str, outfit_id: str) -> Dict[str, Any]:
    """
    Get a specific saved outfit by ID.

    Args:
        user_id: User identifier
        outfit_id: Outfit identifier

    Returns:
        {"outfit": {...}} or 404
    """
    manager = SavedOutfitsManager(user_id=user_id)
    outfit = manager.get_outfit_by_id(outfit_id)

    if not outfit:
        raise HTTPException(status_code=404, detail=f"Outfit {outfit_id} not found")

    return {"outfit": outfit}


# --- WRITE PRIMITIVES ---

@router.post("/{user_id}")
async def save_outfit(user_id: str, request: SaveOutfitRequest) -> Dict[str, Any]:
    """
    Save an outfit.

    Args:
        user_id: User identifier
        request: Outfit data and reason

    Returns:
        {"outfit_id": str}
    """
    manager = SavedOutfitsManager(user_id=user_id)

    # Convert to format expected by manager
    outfit_combo = OutfitCombo(request.outfit_data)

    outfit_id = manager.save_outfit(
        outfit_combo=outfit_combo,
        reason=request.reason,
        occasion=request.occasion,
        context=request.context
    )

    if not outfit_id:
        raise HTTPException(status_code=500, detail="Failed to save outfit")

    return {"outfit_id": outfit_id}


@router.delete("/{user_id}/{outfit_id}")
async def delete_outfit(user_id: str, outfit_id: str) -> Dict[str, Any]:
    """
    Delete a saved outfit.

    Args:
        user_id: User identifier
        outfit_id: Outfit identifier

    Returns:
        {"deleted": bool}
    """
    manager = SavedOutfitsManager(user_id=user_id)

    deleted = manager.delete_outfit(outfit_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Outfit {outfit_id} not found")

    return {"deleted": True}


@router.post("/{user_id}/{outfit_id}/mark-worn")
async def mark_worn(user_id: str, outfit_id: str, request: MarkWornRequest) -> Dict[str, Any]:
    """
    Mark an outfit as worn.

    Args:
        user_id: User identifier
        outfit_id: Outfit identifier
        request: Optional worn photo URL

    Returns:
        {"outfit": updated_outfit}
    """
    manager = SavedOutfitsManager(user_id=user_id)

    outfit = manager.mark_outfit_worn(
        outfit_id=outfit_id,
        worn_photo_url=request.worn_photo_url
    )

    if not outfit:
        raise HTTPException(status_code=404, detail=f"Outfit {outfit_id} not found")

    return {"outfit": outfit}


@router.post("/{user_id}/{outfit_id}/upload-worn-photo")
async def upload_worn_photo(
    user_id: str,
    outfit_id: str,
    photo: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Upload a photo of user wearing the outfit.

    Args:
        user_id: User identifier
        outfit_id: Outfit identifier
        photo: Photo file

    Returns:
        {"outfit": updated_outfit, "photo_url": str}
    """
    manager = SavedOutfitsManager(user_id=user_id)

    # First verify outfit exists
    outfit = manager.get_outfit_by_id(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail=f"Outfit {outfit_id} not found")

    # Save photo to storage
    storage = StorageManager(
        storage_type=os.getenv("STORAGE_TYPE", "local"),
        user_id=user_id
    )

    from PIL import Image
    import io

    # Process and save image
    await photo.seek(0)
    image_data = await photo.read()
    pil_image = Image.open(io.BytesIO(image_data))

    # Convert RGBA to RGB if needed
    if pil_image.mode in ('RGBA', 'P'):
        pil_image = pil_image.convert('RGB')

    # Generate unique filename
    filename = f"worn_{outfit_id}_{uuid.uuid4().hex[:8]}.jpg"
    photo_url = storage.save_image(pil_image, filename, subfolder="worn_photos")

    # Update outfit with photo
    updated_outfit = manager.mark_outfit_worn(
        outfit_id=outfit_id,
        worn_photo_url=photo_url
    )

    return {"outfit": updated_outfit, "photo_url": photo_url}
