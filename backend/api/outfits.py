"""
Outfit generation API endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import asyncio
import json
import logging
import datetime

from models.schemas import OutfitRequest, OutfitGenerationResponse, SaveOutfitRequest, DislikeOutfitRequest, OutfitContext
from workers.outfit_worker import generate_outfits_job
from services.saved_outfits_manager import SavedOutfitsManager
from services.disliked_outfits_manager import DislikedOutfitsManager
from services.prompts.library import PromptLibrary
from core.redis import get_redis_connection
from core.config import get_settings
from rq import Queue

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy initialization of RQ queue (only when needed)
def get_outfit_queue():
    """Get or create outfit queue"""
    redis_conn = get_redis_connection()
    return Queue('outfits', connection=redis_conn)


@router.get("/outfits/generate/stream")
async def generate_outfits_stream(
    user_id: str = Query(..., description="User ID"),
    mode: str = Query("occasion", description="Generation mode: 'occasion' or 'complete'"),
    occasions: str = Query(None, description="Comma-separated list of occasions"),
    anchor_items: str = Query(None, description="Comma-separated list of anchor item IDs (for complete mode)"),
    weather_condition: str = Query(None, description="Weather condition"),
    temperature_range: str = Query(None, description="Temperature range"),
    include_reasoning: bool = Query(False, description="Include chain-of-thought reasoning in response")
):
    """
    Stream outfit generation via SSE.
    Returns outfits one-by-one as they're generated (~7s, ~14s, ~21s).
    """
    async def event_generator():
        try:
            # Import here to avoid circular imports
            from services.style_engine import StyleGenerationEngine
            from services.wardrobe_manager import WardrobeManager
            from services.user_profile_manager import UserProfileManager
            from core.config import get_settings

            # Setup - similar to workers/outfit_worker.py
            wardrobe_manager = WardrobeManager(user_id=user_id)
            profile_manager = UserProfileManager(user_id=user_id)

            # Get profile (create default if needed)
            raw_profile = profile_manager.get_profile(user_id)
            if not raw_profile or not raw_profile.get("style_words"):
                raw_profile = {"style_words": ["versatile", "confident", "comfortable"]}

            user_profile = {
                "three_words": {
                    "current": raw_profile["style_words"][0] if len(raw_profile["style_words"]) > 0 else "versatile",
                    "aspirational": raw_profile["style_words"][1] if len(raw_profile["style_words"]) > 1 else "confident",
                    "feeling": raw_profile["style_words"][2] if len(raw_profile["style_words"]) > 2 else "comfortable"
                }
            }

            # Load wardrobe
            all_items = wardrobe_manager.get_wardrobe_items("all")

            # Determine available items and anchor items based on mode
            if mode == "complete" and anchor_items:
                anchor_item_ids = [id.strip() for id in anchor_items.split(",")]
                anchor_item_objects = []
                
                # Get anchor items (can be from wardrobe OR considering items)
                for item_id in anchor_item_ids:
                    # First try to find in wardrobe
                    found = False
                    for item in all_items:
                        if item.get("id") == item_id:
                            anchor_item_objects.append(item)
                            found = True
                            break
                    
                    # If not found and it's a considering item, fetch from ConsiderBuyingManager
                    if not found and item_id.startswith('consider_'):
                        from services.consider_buying_manager import ConsiderBuyingManager
                        cb_manager = ConsiderBuyingManager(user_id=user_id)
                        considering_items = cb_manager.get_items(status='considering')
                        for considering_item in considering_items:
                            if considering_item.get("id") == item_id:
                                anchor_item_objects.append(considering_item)
                                found = True
                                break
                    
                    if not found:
                        logger.warning(f"Anchor item {item_id} not found in wardrobe or considering items")
                
                if not anchor_item_objects:
                    raise ValueError("Anchor items not found in wardrobe or considering items")
                
                # Get all other items (only from wardrobe, NOT considering)
                available_items = [item for item in all_items if item.get("id") not in anchor_item_ids]
                styling_challenges = anchor_item_objects
            else:
                available_items = all_items
                styling_challenges = []

            # Parse occasions
            occasion_str = ", ".join([o.strip() for o in occasions.split(",")]) if occasions else None

            # Create context
            context = OutfitContext(
                occasions=[o.strip() for o in occasions.split(",")] if occasions else [],
                weather_condition=weather_condition,
                temperature_range=temperature_range
            )

            # Create engine with streaming prompt
            engine = StyleGenerationEngine(
                model="gpt-4o",
                temperature=0.7,
                max_tokens=6000,
                prompt_version="chain_of_thought_streaming_v1"
            )

            # Stream outfits
            outfit_num = 0
            cumulative_reasoning = ""  # Track reasoning text for debug mode
            
            # Also check consider-buying items for matching (needed for complete mode with consider-buying anchors)
            considering_items_for_match = []
            if mode == "complete" and anchor_items:
                from services.consider_buying_manager import ConsiderBuyingManager
                cb_manager = ConsiderBuyingManager(user_id=user_id)
                considering_items_for_match = cb_manager.get_items(status='considering')
            
            # We need to capture the raw streaming response for reasoning extraction
            # Since generate_outfit_combinations_stream doesn't expose the raw text,
            # we'll need to modify the approach or extract reasoning differently
            # For now, we'll note that streaming prompt includes reasoning inline
            
            reasoning_text = ""  # Accumulate reasoning if requested
            for result in engine.generate_outfit_combinations_stream(
                user_profile=user_profile,
                available_items=available_items,
                styling_challenges=styling_challenges,
                occasion=occasion_str,
                weather_condition=weather_condition,
                temperature_range=temperature_range,
                include_reasoning=include_reasoning
            ):
                # Handle both formats: (outfit, reasoning) tuple or just outfit
                if include_reasoning and isinstance(result, tuple):
                    outfit, reasoning_text = result
                else:
                    outfit = result
                
                outfit_num += 1

                # Enrich outfit with full item data (images, etc.)
                enriched_items = []
                
                for item_name in outfit.get("items", []):
                    # Find matching item in wardrobe first
                    matched = None
                    for item in all_items:
                        item_display_name = item.get("styling_details", {}).get("name", "")
                        if item_display_name.lower() == item_name.lower():
                            matched = item
                            break
                    
                    # If not found in wardrobe, check consider-buying items
                    if not matched:
                        for item in considering_items_for_match:
                            item_display_name = item.get("styling_details", {}).get("name", "")
                            if item_display_name.lower() == item_name.lower():
                                matched = item
                                break

                    if matched:
                        # Handle image_path - wardrobe items have it in system_metadata, consider-buying items have it at top level
                        image_path = matched.get("system_metadata", {}).get("image_path") or matched.get("image_path")
                        
                        enriched_items.append({
                            "id": matched.get("id"),
                            "name": matched.get("styling_details", {}).get("name", item_name),
                            "category": matched.get("styling_details", {}).get("category", "unknown"),
                            "image_path": image_path
                        })
                    else:
                        enriched_items.append({"name": item_name, "category": "unknown"})

                enriched_outfit = {
                    "items": enriched_items,
                    "styling_notes": outfit.get("styling_notes", ""),
                    "why_it_works": outfit.get("why_it_works", ""),
                    "confidence_level": outfit.get("confidence_level", "medium"),
                    "vibe_keywords": outfit.get("vibe_keywords", []),
                    "constitution_principles": outfit.get("constitution_principles", {}),
                    "context": context.model_dump()
                }

                yield f"event: outfit\ndata: {json.dumps({'outfit_number': outfit_num, 'outfit': enriched_outfit})}\n\n"
                await asyncio.sleep(0)  # Allow event loop to process

            # For reasoning, we need to get it from the streaming response
            # The streaming prompt includes reasoning, but we'd need to modify the engine to expose it
            # For now, if include_reasoning is True, we'll need to make a note that it's not available in streaming mode
            # OR we could make a separate call to get reasoning, but that defeats the purpose of streaming
            
            complete_data = {"total": outfit_num}
            if include_reasoning and reasoning_text:
                complete_data["reasoning"] = reasoning_text
            
            yield f"event: complete\ndata: {json.dumps(complete_data)}\n\n"

        except Exception as e:
            logger.error(f"Streaming error for {user_id}: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/outfits/generate", response_model=OutfitGenerationResponse)
async def generate_outfits(request: OutfitRequest):
    """Generate outfits (background job)"""
    try:
        # Get prompt version (request override or env default)
        prompt_version = request.prompt_version or get_settings().PROMPT_VERSION
        
        # Validate prompt version exists
        try:
            PromptLibrary.get_prompt(prompt_version)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Enqueue outfit generation job
        outfit_queue = get_outfit_queue()
        job = outfit_queue.enqueue(
            generate_outfits_job,
            user_id=request.user_id,
            occasions=request.occasions,
            weather_condition=request.weather_condition,
            temperature_range=request.temperature_range,
            mode=request.mode,
            anchor_items=request.anchor_items,
            mock=request.mock,
            prompt_version=prompt_version,
            include_reasoning=request.include_reasoning,
            job_timeout=120  # 2 minutes max
        )
        
        return {
            "job_id": job.id,
            "status": "queued",
            "estimated_time": 30,  # seconds
            "prompt_version": prompt_version
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enqueueing outfit generation for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class OutfitDictWrapper:
    """Simple wrapper to convert dict to object-like structure for managers"""
    def __init__(self, outfit_dict: dict):
        self.items = outfit_dict.get("items", [])
        self.styling_notes = outfit_dict.get("styling_notes", "")
        self.why_it_works = outfit_dict.get("why_it_works", "")
        self.confidence_level = outfit_dict.get("confidence_level", "medium")
        self.vibe_keywords = outfit_dict.get("vibe_keywords", [])
        self.context = outfit_dict.get("context")


@router.post("/outfits/save")
async def save_outfit(request: SaveOutfitRequest):
    """Save outfit to favorites"""
    try:
        manager = SavedOutfitsManager(user_id=request.user_id)
        outfit_wrapper = OutfitDictWrapper(request.outfit)
        success = manager.save_outfit(
            outfit_combo=outfit_wrapper,
            reason=", ".join(request.feedback) if request.feedback else "",
            context=outfit_wrapper.context
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save outfit")
        
        return {"success": True, "message": "Outfit saved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving outfit for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outfits/dislike")
async def dislike_outfit(request: DislikeOutfitRequest):
    """Dislike outfit with feedback"""
    try:
        manager = DislikedOutfitsManager(user_id=request.user_id)
        outfit_wrapper = OutfitDictWrapper(request.outfit)
        success = manager.dislike_outfit(
            outfit_combo=outfit_wrapper,
            reason=request.reason or "",
            context=outfit_wrapper.context
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to record dislike")
        
        return {"success": True, "message": "Feedback recorded"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disliking outfit for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outfits/{user_id}/saved")
async def get_saved_outfits(user_id: str):
    """Get all saved outfits for a user"""
    try:
        manager = SavedOutfitsManager(user_id=user_id)
        saved_outfits = manager.get_saved_outfits()
        return {"outfits": saved_outfits, "count": len(saved_outfits)}
    except Exception as e:
        logger.error(f"Error fetching saved outfits for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outfits/{user_id}/disliked")
async def get_disliked_outfits(user_id: str):
    """Get all disliked outfits for a user"""
    try:
        manager = DislikedOutfitsManager(user_id=user_id)
        disliked_outfits = manager.get_disliked_outfits()
        return {"outfits": disliked_outfits, "count": len(disliked_outfits)}
    except Exception as e:
        logger.error(f"Error fetching disliked outfits for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


