"""
Items Primitives - Wardrobe item CRUD operations.

Primitives:
- get_items(user_id) -> List[Item]
- get_item(user_id, item_id) -> Item
- add_item(user_id, item_data, image) -> Item
- update_item(user_id, item_id, updates) -> Item
- rotate_item_image(user_id, item_id, degrees) -> str (new image path)
- delete_item(user_id, item_id) -> bool
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging

from services.wardrobe_manager import WardrobeManager
from services.image_analyzer import create_image_analyzer

logger = logging.getLogger(__name__)
router = APIRouter()


class ItemUpdate(BaseModel):
    """Fields that can be updated on an item"""
    name: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    colors: Optional[List[str]] = None
    cut: Optional[str] = None
    texture: Optional[str] = None
    style: Optional[str] = None
    fit: Optional[str] = None
    brand: Optional[str] = None
    fabric: Optional[str] = None
    trend_status: Optional[str] = None
    styling_notes: Optional[str] = None
    design_details: Optional[str] = None


class RotateRequest(BaseModel):
    """Request body for image rotation"""
    degrees: int = 90


# --- READ PRIMITIVES ---

@router.get("/{user_id}")
async def get_items(user_id: str, filter_type: str = "all", compact: bool = False) -> Dict[str, Any]:
    """
    Get all wardrobe items for a user.

    Args:
        user_id: User identifier
        filter_type: "all" | "styling_challenges" | "regular_wear"
        compact: If True, return only essential styling fields (reduces tokens by ~80%)

    Returns:
        {"items": [...], "count": int}
    """
    manager = WardrobeManager(user_id=user_id)
    items = manager.get_wardrobe_items(filter_type=filter_type)

    if compact:
        # Return only fields needed for styling decisions
        # Keeps: texture, brand, trend_status (all matter for styling)
        # Drops: styling_notes (generic AI filler), timestamps, paths
        items = [
            {
                "id": item["id"],
                "name": item.get("styling_details", {}).get("name", ""),
                "category": item.get("styling_details", {}).get("category", ""),
                "colors": item.get("styling_details", {}).get("colors", []),
                "cut": item.get("styling_details", {}).get("cut", ""),
                "texture": item.get("styling_details", {}).get("texture", ""),
                "style": item.get("styling_details", {}).get("style", ""),
                "fit": item.get("styling_details", {}).get("fit", ""),
                "brand": item.get("styling_details", {}).get("brand", ""),
                "trend_status": item.get("styling_details", {}).get("trend_status", ""),
                "is_challenge": item.get("usage_metadata", {}).get("is_styling_challenge", False),
            }
            for item in items
        ]

    return {"items": items, "count": len(items)}


@router.get("/{user_id}/{item_id}")
async def get_item(user_id: str, item_id: str) -> Dict[str, Any]:
    """
    Get a specific wardrobe item by ID.

    Args:
        user_id: User identifier
        item_id: Item identifier

    Returns:
        Item dict or 404
    """
    manager = WardrobeManager(user_id=user_id)
    items = manager.get_wardrobe_items(filter_type="all")

    for item in items:
        if item.get("id") == item_id:
            return {"item": item}

    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")


# --- WRITE PRIMITIVES ---

@router.post("/{user_id}")
async def add_item(
    user_id: str,
    image: UploadFile = File(...),
    is_styling_challenge: bool = Form(False),
    challenge_reason: str = Form("")
) -> Dict[str, Any]:
    """
    Add a new wardrobe item.

    Analyzes the image to extract styling details, then saves.

    Args:
        user_id: User identifier
        image: Clothing image file
        is_styling_challenge: Whether this is a styling challenge item
        challenge_reason: Reason for challenge (if applicable)

    Returns:
        {"item": created_item}
    """
    manager = WardrobeManager(user_id=user_id)

    # Analyze image
    analyzer = create_image_analyzer()
    analysis_data = await analyzer.analyze_image(image)

    # Reset file position for saving
    await image.seek(0)

    # Add to wardrobe
    item = manager.add_wardrobe_item(
        uploaded_file=image.file,
        analysis_data=analysis_data,
        is_styling_challenge=is_styling_challenge,
        challenge_reason=challenge_reason
    )

    if not item:
        raise HTTPException(status_code=500, detail="Failed to add item")

    return {"item": item}


@router.put("/{user_id}/{item_id}")
async def update_item(user_id: str, item_id: str, updates: ItemUpdate) -> Dict[str, Any]:
    """
    Update an existing wardrobe item.

    Args:
        user_id: User identifier
        item_id: Item identifier
        updates: Fields to update

    Returns:
        {"item": updated_item}
    """
    manager = WardrobeManager(user_id=user_id)

    # Convert to dict, excluding None values
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}

    if not update_dict:
        raise HTTPException(status_code=400, detail="No updates provided")

    item = manager.update_wardrobe_item(item_id, update_dict)

    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    return {"item": item}


@router.post("/{user_id}/{item_id}/rotate")
async def rotate_item_image(user_id: str, item_id: str, request: RotateRequest) -> Dict[str, Any]:
    """
    Rotate an item's image clockwise.

    Args:
        user_id: User identifier
        item_id: Item identifier
        request: Contains degrees (default 90)

    Returns:
        {"image_path": new_path}
    """
    manager = WardrobeManager(user_id=user_id)

    new_path = manager.rotate_item_image(item_id, degrees=request.degrees)

    if not new_path:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found or rotation failed")

    return {"image_path": new_path}


@router.delete("/{user_id}/{item_id}")
async def delete_item(user_id: str, item_id: str) -> Dict[str, Any]:
    """
    Delete a wardrobe item.

    Args:
        user_id: User identifier
        item_id: Item identifier

    Returns:
        {"deleted": bool}
    """
    manager = WardrobeManager(user_id=user_id)

    deleted = manager.delete_wardrobe_item(item_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    return {"deleted": True}


@router.post("/{user_id}/{item_id}/toggle-challenge")
async def toggle_styling_challenge(
    user_id: str,
    item_id: str,
    is_challenge: Optional[bool] = None,
    challenge_reason: str = ""
) -> Dict[str, Any]:
    """
    Toggle or set styling challenge status for an item.

    Args:
        user_id: User identifier
        item_id: Item identifier
        is_challenge: If None, toggles current state
        challenge_reason: Reason for challenge

    Returns:
        {"success": bool}
    """
    manager = WardrobeManager(user_id=user_id)

    success = manager.toggle_styling_challenge(
        item_id,
        is_challenge=is_challenge,
        challenge_reason=challenge_reason
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    return {"success": True}
