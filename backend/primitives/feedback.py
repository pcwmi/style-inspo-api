"""
Feedback Primitives - Disliked outfit/feedback operations.

Primitives:
- save_feedback(user_id, outfit_data, reason) -> Feedback
- get_feedback(user_id) -> List[Feedback]
- get_feedback_patterns(user_id) -> FeedbackPatterns
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging

from services.disliked_outfits_manager import DislikedOutfitsManager

logger = logging.getLogger(__name__)
router = APIRouter()


class OutfitItem(BaseModel):
    """Item in an outfit"""
    id: Optional[str] = None
    name: str
    category: Optional[str] = None
    image_path: Optional[str] = None


class OutfitData(BaseModel):
    """Outfit structure for feedback"""
    items: List[OutfitItem]
    styling_notes: Optional[str] = None
    why_it_works: Optional[str] = None
    confidence_level: Optional[str] = None
    vibe_keywords: Optional[List[str]] = None


class FeedbackRequest(BaseModel):
    """Request body for saving feedback"""
    outfit_data: OutfitData
    reason: str = ""
    occasion: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class OutfitCombo:
    """Simple adapter for DislikedOutfitsManager.dislike_outfit()"""

    def __init__(self, outfit_data: OutfitData):
        self.items = [item.model_dump() for item in outfit_data.items]
        self.styling_notes = outfit_data.styling_notes or ""
        self.why_it_works = outfit_data.why_it_works or ""
        self.confidence_level = outfit_data.confidence_level or ""
        self.vibe_keywords = outfit_data.vibe_keywords or []


# --- READ PRIMITIVES ---

@router.get("/{user_id}")
async def get_feedback(user_id: str) -> Dict[str, Any]:
    """
    Get all feedback (disliked outfits) for a user.

    Args:
        user_id: User identifier

    Returns:
        {"feedback": [...], "count": int}
    """
    manager = DislikedOutfitsManager(user_id=user_id)
    feedback = manager.get_disliked_outfits(enrich_with_current_images=True)
    return {"feedback": feedback, "count": len(feedback)}


@router.get("/{user_id}/patterns")
async def get_feedback_patterns(user_id: str) -> Dict[str, Any]:
    """
    Get feedback with full context for agent to reason about.

    No pre-processing or categorization - just the raw data.
    Agent is smart enough to understand "plaid on plaid" means
    don't pair the two plaid items.

    Args:
        user_id: User identifier

    Returns:
        {
            "total_feedback": int,
            "feedback": [{"items": [...], "reason": str, "date": str}]
        }
    """
    manager = DislikedOutfitsManager(user_id=user_id)
    feedback_list = manager.get_disliked_outfits(enrich_with_current_images=False)

    feedback = []
    for f in feedback_list:
        outfit_data = f.get("outfit_data", {})
        items = outfit_data.get("items", [])
        item_names = [item.get("name", "Unknown") for item in items]

        feedback.append({
            "items": item_names,
            "reason": f.get("user_reason", "").strip(),
            "date": f.get("disliked_at", "")[:10]
        })

    return {
        "total_feedback": len(feedback_list),
        "feedback": feedback
    }


# --- WRITE PRIMITIVES ---

@router.post("/{user_id}")
async def save_feedback(user_id: str, request: FeedbackRequest) -> Dict[str, Any]:
    """
    Save feedback (dislike) for an outfit.

    Args:
        user_id: User identifier
        request: Outfit data and reason

    Returns:
        {"saved": bool}
    """
    manager = DislikedOutfitsManager(user_id=user_id)

    # Convert to format expected by manager
    outfit_combo = OutfitCombo(request.outfit_data)

    success = manager.dislike_outfit(
        outfit_combo=outfit_combo,
        reason=request.reason,
        occasion=request.occasion,
        context=request.context
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save feedback")

    return {"saved": True}
