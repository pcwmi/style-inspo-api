"""
Considering Primitives - Consider-buying item operations.

Primitives:
- add_considering_item(user_id, image, price?, source_url?) -> Item
- get_considering_items(user_id, status?) -> List[Item]
- get_considering_stats(user_id) -> Stats
- update_considering_item(user_id, item_id, updates) -> Item
- rotate_considering_image(user_id, item_id, degrees) -> str
- decide_considering_item(user_id, item_id, decision, reason?) -> Decision
- delete_considering_item(user_id, item_id) -> bool
- delete_all_considering_items(user_id) -> bool
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging

from services.consider_buying_manager import ConsiderBuyingManager
from services.image_analyzer import create_image_analyzer
from services.wardrobe_manager import WardrobeManager

logger = logging.getLogger(__name__)
router = APIRouter()


class ItemUpdate(BaseModel):
    """Fields that can be updated on a considering item"""
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
    price: Optional[float] = None
    source_url: Optional[str] = None


class DecisionRequest(BaseModel):
    """Request body for making a decision on an item"""
    decision: str  # "bought" | "passed" | "later"
    reason: Optional[str] = None


class RotateRequest(BaseModel):
    """Request body for image rotation"""
    degrees: int = 90


# --- READ PRIMITIVES ---

@router.get("/{user_id}")
async def get_considering_items(user_id: str, status: Optional[str] = None) -> Dict[str, Any]:
    """
    Get considering items for a user.

    Args:
        user_id: User identifier
        status: Filter by status ("considering" | "bought" | "passed")

    Returns:
        {"items": [...], "count": int}
    """
    manager = ConsiderBuyingManager(user_id=user_id)
    items = manager.get_items(status=status)
    return {"items": items, "count": len(items)}


@router.get("/{user_id}/stats")
async def get_considering_stats(user_id: str) -> Dict[str, Any]:
    """
    Get buying decision statistics.

    Args:
        user_id: User identifier

    Returns:
        {
            "total_considered": int,
            "total_bought": int,
            "total_passed": int,
            "total_saved": float
        }
    """
    manager = ConsiderBuyingManager(user_id=user_id)
    stats = manager.get_stats()
    return {"stats": stats}


@router.get("/{user_id}/{item_id}")
async def get_considering_item(user_id: str, item_id: str) -> Dict[str, Any]:
    """
    Get a specific considering item by ID.

    Args:
        user_id: User identifier
        item_id: Item identifier

    Returns:
        {"item": {...}} or 404
    """
    manager = ConsiderBuyingManager(user_id=user_id)
    items = manager.get_items()

    for item in items:
        if item.get("id") == item_id:
            return {"item": item}

    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")


@router.get("/{user_id}/{item_id}/similar")
async def get_similar_items(user_id: str, item_id: str) -> Dict[str, Any]:
    """
    Find similar items in wardrobe to a considering item.

    Args:
        user_id: User identifier
        item_id: Considering item identifier

    Returns:
        {"similar_items": [...]}
    """
    manager = ConsiderBuyingManager(user_id=user_id)
    wardrobe = WardrobeManager(user_id=user_id)

    # Find the considering item
    consider_item = None
    for item in manager.get_items():
        if item.get("id") == item_id:
            consider_item = item
            break

    if not consider_item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    # Find similar wardrobe items
    wardrobe_items = wardrobe.get_wardrobe_items("all")
    similar = manager.find_similar_items(consider_item, wardrobe_items)

    return {"similar_items": similar}


# --- WRITE PRIMITIVES ---

@router.post("/{user_id}")
async def add_considering_item(
    user_id: str,
    image: UploadFile = File(...),
    price: Optional[float] = Form(None),
    source_url: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    Add an item to consider buying.

    Analyzes the image to extract styling details.

    Args:
        user_id: User identifier
        image: Product image file
        price: Optional price
        source_url: Optional source URL

    Returns:
        {"item": created_item}
    """
    manager = ConsiderBuyingManager(user_id=user_id)

    # Analyze image
    analyzer = create_image_analyzer()
    analysis_data = await analyzer.analyze_image(image)

    # Reset file position for saving
    await image.seek(0)

    # Add to considering
    item = manager.add_item(
        analysis_data=analysis_data,
        image=image.file,
        price=price,
        source_url=source_url
    )

    return {"item": item}


@router.put("/{user_id}/{item_id}")
async def update_considering_item(user_id: str, item_id: str, updates: ItemUpdate) -> Dict[str, Any]:
    """
    Update a considering item.

    Args:
        user_id: User identifier
        item_id: Item identifier
        updates: Fields to update

    Returns:
        {"item": updated_item}
    """
    manager = ConsiderBuyingManager(user_id=user_id)

    # Convert to dict, excluding None values
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}

    if not update_dict:
        raise HTTPException(status_code=400, detail="No updates provided")

    item = manager.update_considering_item(item_id, update_dict)

    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    return {"item": item}


@router.post("/{user_id}/{item_id}/rotate")
async def rotate_considering_image(user_id: str, item_id: str, request: RotateRequest) -> Dict[str, Any]:
    """
    Rotate a considering item's image clockwise.

    Args:
        user_id: User identifier
        item_id: Item identifier
        request: Contains degrees (default 90)

    Returns:
        {"image_path": new_path}
    """
    manager = ConsiderBuyingManager(user_id=user_id)

    new_path = manager.rotate_considering_item_image(item_id, degrees=request.degrees)

    if not new_path:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found or rotation failed")

    return {"image_path": new_path}


@router.post("/{user_id}/{item_id}/decide")
async def decide_considering_item(user_id: str, item_id: str, request: DecisionRequest) -> Dict[str, Any]:
    """
    Record a buying decision for an item.

    Args:
        user_id: User identifier
        item_id: Item identifier
        request: Decision ("bought" | "passed" | "later") and optional reason

    Returns:
        {"decision": decision_record}
    """
    valid_decisions = ["bought", "passed", "later"]
    if request.decision not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision. Must be one of: {valid_decisions}"
        )

    manager = ConsiderBuyingManager(user_id=user_id)

    try:
        decision_record = manager.record_decision(
            item_id=item_id,
            decision=request.decision,
            reason=request.reason
        )
        return {"decision": decision_record}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{user_id}/{item_id}")
async def delete_considering_item(user_id: str, item_id: str) -> Dict[str, Any]:
    """
    Delete a considering item.

    Args:
        user_id: User identifier
        item_id: Item identifier

    Returns:
        {"deleted": bool}
    """
    manager = ConsiderBuyingManager(user_id=user_id)

    # Verify item exists
    items = manager.get_items()
    item_exists = any(item.get("id") == item_id for item in items)

    if not item_exists:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    manager.delete_item(item_id)
    return {"deleted": True}


@router.delete("/{user_id}")
async def delete_all_considering_items(user_id: str) -> Dict[str, Any]:
    """
    Delete all considering items for a user.

    Args:
        user_id: User identifier

    Returns:
        {"deleted_count": int}
    """
    manager = ConsiderBuyingManager(user_id=user_id)
    items = manager.get_items()
    count = len(items)

    for item in items:
        manager.delete_item(item.get("id"))

    return {"deleted_count": count}
