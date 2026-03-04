"""
Outfit generation API endpoints
"""

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from PIL import Image, ImageOps
from io import BytesIO

from models.schemas import SaveOutfitRequest, DislikeOutfitRequest, OutfitContext, MarkWornRequest, MarkWornResponse
from services.saved_outfits_manager import SavedOutfitsManager
from services.disliked_outfits_manager import DislikedOutfitsManager
from services.activity_logger import log_activity
from services.storage_manager import StorageManager

router = APIRouter()
logger = logging.getLogger(__name__)


def _trigger_background_visualization(user_id: str, outfit_id: str, items: list):
    """Spawn background thread to generate visualization for saved outfit."""
    import threading

    # Skip if outfit already has a visualization
    try:
        manager = SavedOutfitsManager(user_id=user_id)
        outfit = manager.get_outfit(outfit_id)
        if outfit and outfit.get("visualization_url"):
            logger.info(f"Outfit {outfit_id} already has viz, skipping")
            return
    except Exception:
        pass  # If check fails, proceed with generation

    def run_visualization():
        try:
            from services.visualization.visualization_manager import VisualizationManager

            logger.info(f"Starting background visualization for outfit {outfit_id}")

            # Extract image URLs from items
            garment_images = []
            for item in items:
                image_path = item.get("image_path") or item.get("system_metadata", {}).get("image_path")
                if image_path:
                    garment_images.append(image_path)

            if not garment_images:
                logger.warning(f"No images for outfit {outfit_id}, skipping visualization")
                return

            viz_manager = VisualizationManager(user_id)
            result = viz_manager.visualize_outfit(outfit_id)

            if result and result.get("success"):
                logger.info(f"Background visualization complete for outfit {outfit_id}")
            else:
                logger.warning(f"Background visualization failed for outfit {outfit_id}")

        except Exception as e:
            logger.error(f"Background visualization error for outfit {outfit_id}: {e}")
            try:
                manager = SavedOutfitsManager(user_id=user_id)
                manager.clear_visualization_pending(outfit_id, error=str(e))
            except Exception:
                pass

    # Run in background thread
    thread = threading.Thread(target=run_visualization, daemon=True)
    thread.start()
    logger.info(f"Spawned background visualization thread for outfit {outfit_id}")


def _trigger_visualization_by_key(user_id: str, viz_key: str, garment_images: list):
    """
    Spawn background thread to generate visualization, store by viz_key.

    Used by streaming endpoint (web flow) - triggers on GENERATE, not save.
    Results stored in Redis by viz_key for frontend polling.
    """
    import threading
    from services.visualization.viz_cache import get_viz_status

    # Skip if already generating or done
    existing = get_viz_status(viz_key)
    if existing.get("status") in ["pending", "complete"]:
        logger.info(f"Viz already {existing['status']} for key {viz_key}, skipping")
        return

    def run_visualization():
        try:
            from services.visualization.visualization_manager import VisualizationManager
            from services.visualization.viz_cache import set_viz_pending, set_viz_complete, set_viz_failed

            logger.info(f"Starting background viz for key {viz_key}")
            set_viz_pending(viz_key)

            viz_manager = VisualizationManager(user_id)
            result = viz_manager.visualize_from_images(garment_images)

            if result and result.get("visualization_url"):
                set_viz_complete(viz_key, result["visualization_url"])
                logger.info(f"Viz complete for key {viz_key}: {result['visualization_url'][:50]}...")

                # Persist to saved outfit if it exists (handles race: viz completes after save)
                _persist_viz_to_saved_outfit(user_id, viz_key, result["visualization_url"])
            else:
                error = result.get("error", "Unknown error") if result else "No result"
                set_viz_failed(viz_key, error)
                _clear_viz_pending_for_key(user_id, viz_key, error)
                logger.warning(f"Viz failed for key {viz_key}: {error}")

        except Exception as e:
            from services.visualization.viz_cache import set_viz_failed
            set_viz_failed(viz_key, str(e))
            _clear_viz_pending_for_key(user_id, viz_key, str(e))
            logger.error(f"Viz error for key {viz_key}: {e}")

    thread = threading.Thread(target=run_visualization, daemon=True)
    thread.start()
    logger.info(f"Spawned viz thread for key {viz_key}")


def _clear_viz_pending_for_key(user_id: str, viz_key: str, error: str):
    """If a saved outfit has this viz_key, clear its pending flag."""
    try:
        manager = SavedOutfitsManager(user_id=user_id)
        saved_outfits = manager.get_saved_outfits(enrich_with_current_images=False)
        for outfit in saved_outfits:
            if outfit.get("viz_key") == viz_key and outfit.get("visualization_pending"):
                manager.clear_visualization_pending(outfit["id"], error=error)
                logger.info(f"Cleared pending flag for outfit {outfit['id']} (viz_key={viz_key})")
                break
    except Exception as e:
        logger.error(f"Failed to clear viz pending for key {viz_key}: {e}")


def _persist_viz_to_saved_outfit(user_id: str, viz_key: str, viz_url: str):
    """If a saved outfit matches this viz_key, persist the URL to S3."""
    try:
        manager = SavedOutfitsManager(user_id=user_id)
        saved_outfits = manager.get_saved_outfits(enrich_with_current_images=False)
        for outfit in saved_outfits:
            outfit_data = outfit.get("outfit_data", {})
            items = outfit_data.get("items", [])
            garment_images = sorted([i.get("image_path", "") for i in items if i.get("image_path")])
            candidate_key = hashlib.md5('|'.join(garment_images).encode()).hexdigest()[:12]
            if candidate_key == viz_key and not outfit.get("visualization_url"):
                manager.update_outfit_visualization(outfit["id"], viz_url)
                logger.info(f"Persisted viz URL to saved outfit {outfit['id']}")
                break
    except Exception as e:
        logger.error(f"Failed to persist viz to saved outfit: {e}")


def log_generation_to_s3(
    user_id: str,
    mode: str,
    outfits: list,
    occasion: str = None,
    anchor_items: list = None,
    anchor_item_names: list = None,
    device_id: str = None
):
    """
    Log outfit generation to S3 for analytics/daily digest.
    Appends to daily log file: {user_id}/generations/{YYYY-MM-DD}.json
    """
    try:
        storage_type = os.getenv("STORAGE_TYPE", "local")
        storage = StorageManager(storage_type=storage_type, user_id=user_id)

        # Get today's date for the log file
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_filename = f"generations/{today}.json"

        # Load existing log for today (or empty list)
        try:
            existing_data = storage.load_json(log_filename)
            generations = existing_data.get("generations", [])
        except Exception:
            generations = []

        # Create generation log entry
        generation_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "outfits": outfits
        }

        # Add device_id for analytics filtering (to separate real users from admin testing)
        if device_id:
            generation_entry["device_id"] = device_id

        # Add mode-specific context
        if mode == "occasion" and occasion:
            generation_entry["occasion"] = occasion
        elif mode == "complete" and anchor_items:
            generation_entry["anchor_item_ids"] = anchor_items
            if anchor_item_names:
                generation_entry["anchor_item_names"] = anchor_item_names

        # Append to today's log
        generations.append(generation_entry)

        # Save back to S3
        storage.save_json({"generations": generations}, log_filename)
        logger.info(f"Logged generation for {user_id}: {mode} mode, {len(outfits)} outfits")

        # Also log to unified activity log
        log_activity(user_id, "outfit_generated", {
            "mode": mode,
            "outfit_count": len(outfits),
            "occasion": occasion if mode == "occasion" else None,
            "anchor_items": anchor_item_names if mode == "complete" else None
        })

    except Exception as e:
        # Don't fail the request if logging fails
        logger.error(f"Failed to log generation for {user_id}: {e}")


@router.get("/outfits/generate/stream")
async def generate_outfits_stream(
    user_id: str = Query(..., description="User ID"),
    mode: str = Query("occasion", description="Generation mode: 'occasion' or 'complete'"),
    occasions: str = Query(None, description="Comma-separated list of occasions"),
    anchor_items: str = Query(None, description="Comma-separated list of anchor item IDs (for complete mode)"),
    weather_condition: str = Query(None, description="Weather condition"),
    temperature_range: str = Query(None, description="Temperature range"),
    include_reasoning: bool = Query(False, description="Include chain-of-thought reasoning in response"),
    device_id: str = Query(None, description="PostHog device ID for analytics filtering")
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
            anchor_item_objects = []  # Initialize for both modes
            if mode == "complete" and anchor_items:
                anchor_item_ids = [id.strip() for id in anchor_items.split(",")]
                
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
            # gpt-5.2 for better reasoning (~$0.024/outfit) - 9% faster than 5.1, same quality
            outfit_model = os.getenv("OUTFIT_GENERATION_MODEL", "gpt-5.2")
            engine = StyleGenerationEngine(
                model=outfit_model,
                temperature=0.7,
                max_tokens=6000,
                prompt_version="chain_of_thought_streaming_v1"
            )

            # Stream outfits
            outfit_num = 0
            cumulative_reasoning = ""  # Track reasoning text for debug mode
            generated_outfits = []  # Collect for logging
            
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

                # Enrich outfit with full item data (images, etc.)
                enriched_items = []

                # Build anchor item lookup for priority matching (anchor items MUST show images)
                anchor_lookup = {item.get("id"): item for item in anchor_item_objects} if mode == "complete" else {}

                for item_name in outfit.get("items", []):
                    matched = None
                    item_name_lower = item_name.lower()

                    # FIRST: Try to match anchor items with fuzzy matching
                    # This ensures user-selected items always show their images
                    for anchor_id, anchor_item in anchor_lookup.items():
                        anchor_name = anchor_item.get("styling_details", {}).get("name", "").lower()
                        # Fuzzy match: check if anchor name contains AI name or vice versa
                        if anchor_name and (anchor_name in item_name_lower or item_name_lower in anchor_name):
                            matched = anchor_item
                            logger.info(f"Anchor match: '{item_name}' -> '{anchor_name}' (ID: {anchor_id})")
                            break

                    # SECOND: Try fuzzy name match in wardrobe (substring matching)
                    if not matched:
                        for item in all_items:
                            item_display_name = item.get("styling_details", {}).get("name", "").lower()
                            if item_display_name and (item_display_name in item_name_lower or item_name_lower in item_display_name):
                                matched = item
                                logger.info(f"Fuzzy wardrobe match: '{item_name}' -> '{item_display_name}'")
                                break

                    # THIRD: Try fuzzy name match in consider-buying items
                    if not matched:
                        for item in considering_items_for_match:
                            item_display_name = item.get("styling_details", {}).get("name", "").lower()
                            if item_display_name and (item_display_name in item_name_lower or item_name_lower in item_display_name):
                                matched = item
                                logger.info(f"Fuzzy consider-buying match: '{item_name}' -> '{item_display_name}'")
                                break

                    if matched:
                        # Handle image_path - wardrobe items have it in system_metadata, consider-buying items have it at top level
                        image_path = matched.get("system_metadata", {}).get("image_path") or matched.get("image_path")

                        enriched_items.append({
                            "id": matched.get("id"),
                            "name": matched.get("styling_details", {}).get("name", item_name),
                            "category": matched.get("styling_details", {}).get("category", "unknown"),
                            "sub_category": matched.get("styling_details", {}).get("sub_category", ""),
                            "image_path": image_path
                        })
                    else:
                        enriched_items.append({"name": item_name, "category": "unknown", "sub_category": ""})

                # Validate outfit physical plausibility (slot-based check)
                from services.outfit_validator import validate_outfit
                is_valid, rejection_reason = validate_outfit(enriched_items)
                if not is_valid:
                    logger.warning(
                        f"Outfit {outfit_num} filtered: {rejection_reason} | "
                        f"Items: {[i.get('name') for i in enriched_items]}"
                    )
                    try:
                        from services.activity_logger import log_activity
                        log_activity(user_id, "outfit_filtered", {
                            "reason": rejection_reason,
                            "channel": "web",
                            "items": [{"name": i.get("name"), "category": i.get("category"), "sub_category": i.get("sub_category")} for i in enriched_items],
                        })
                    except Exception:
                        pass
                    continue  # Skip this outfit

                outfit_num += 1

                enriched_outfit = {
                    "items": enriched_items,
                    "styling_notes": outfit.get("styling_notes", ""),
                    "why_it_works": outfit.get("why_it_works", ""),
                    "confidence_level": outfit.get("confidence_level", "medium"),
                    "vibe_keywords": outfit.get("vibe_keywords", []),
                    "constitution_principles": outfit.get("constitution_principles", {}),
                    "context": context.model_dump()
                }

                # Collect for logging (exclude context to keep logs lean)
                generated_outfits.append({
                    "items": enriched_items,
                    "styling_notes": outfit.get("styling_notes", ""),
                    "why_it_works": outfit.get("why_it_works", ""),
                    "confidence_level": outfit.get("confidence_level", "medium"),
                    "vibe_keywords": outfit.get("vibe_keywords", [])
                })

                # Generate viz_key and trigger background visualization
                garment_images = [
                    item.get('image_path') for item in enriched_items
                    if item.get('image_path')
                ]
                if garment_images:
                    # Create stable hash from sorted image URLs
                    viz_key = hashlib.md5('|'.join(sorted(garment_images)).encode()).hexdigest()[:12]
                    enriched_outfit['viz_key'] = viz_key
                    enriched_outfit['viz_pending'] = True

                    # Trigger background visualization
                    _trigger_visualization_by_key(user_id, viz_key, garment_images)

                yield f"event: outfit\ndata: {json.dumps({'outfit_number': outfit_num, 'outfit': enriched_outfit})}\n\n"
                await asyncio.sleep(0)  # Allow event loop to process

            # Log generation to S3 for analytics/daily digest
            anchor_item_ids_list = [id.strip() for id in anchor_items.split(",")] if anchor_items else None
            anchor_item_names_list = [
                item.get("styling_details", {}).get("name", "Unknown")
                for item in anchor_item_objects
            ] if mode == "complete" and anchor_item_objects else None

            log_generation_to_s3(
                user_id=user_id,
                mode=mode,
                outfits=generated_outfits,
                occasion=occasion_str,
                anchor_items=anchor_item_ids_list,
                anchor_item_names=anchor_item_names_list,
                device_id=device_id
            )

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
        outfit_id = manager.save_outfit(
            outfit_combo=outfit_wrapper,
            reason=", ".join(request.feedback) if request.feedback else "",
            context=outfit_wrapper.context
        )

        if not outfit_id:
            raise HTTPException(status_code=500, detail="Failed to save outfit")

        # Log activity
        log_activity(request.user_id, "outfit_saved", {
            "outfit_id": outfit_id,
            "reason": ", ".join(request.feedback) if request.feedback else "",
            "item_count": len(outfit_wrapper.items)
        })

        # Persist visualization URL if already generated, or mark pending if still running
        viz_key = request.outfit.get("viz_key")
        if viz_key and outfit_id:
            from services.visualization.viz_cache import get_viz_status
            viz_status = get_viz_status(viz_key)
            if viz_status.get("status") == "complete" and viz_status.get("url"):
                manager.update_outfit_visualization(outfit_id, viz_status["url"])
                logger.info(f"Persisted viz URL from Redis to saved outfit {outfit_id}")
            elif viz_status.get("status") == "pending":
                # Viz is actually running — set pending so frontend polls
                manager.set_visualization_pending(outfit_id, viz_key=viz_key)
                logger.info(f"Viz still pending for saved outfit {outfit_id}")
            # If failed or unknown, leave pending=false (default)

        return {"success": True, "message": "Outfit saved", "outfit_id": outfit_id}
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

        # Log activity
        log_activity(request.user_id, "outfit_disliked", {
            "reason": request.reason or "",
            "item_count": len(outfit_wrapper.items)
        })

        return {"success": True, "message": "Feedback recorded"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disliking outfit for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outfits/{outfit_id}/viz-status")
async def get_visualization_status(outfit_id: str, user: str = Query(..., description="User ID")):
    """Get visualization status for an outfit (for web polling)"""
    try:
        manager = SavedOutfitsManager(user_id=user)
        outfit = manager.get_outfit_by_id(outfit_id)

        if not outfit:
            raise HTTPException(status_code=404, detail="Outfit not found")

        pending = outfit.get("visualization_pending", False)
        url = outfit.get("visualization_url")

        # If DB says pending but no URL, check Redis for the actual viz status
        if pending and not url:
            viz_key = outfit.get("viz_key")
            if viz_key:
                from services.visualization.viz_cache import get_viz_status as get_redis_viz_status
                redis_status = get_redis_viz_status(viz_key)
                if redis_status.get("status") == "complete" and redis_status.get("url"):
                    # Viz completed but DB wasn't updated — fix it now
                    url = redis_status["url"]
                    pending = False
                    try:
                        manager.update_outfit_visualization(outfit_id, url)
                        logger.info(f"Recovered viz URL from Redis for outfit {outfit_id}")
                    except Exception:
                        pass
                elif redis_status.get("status") == "failed":
                    # Viz failed — clear DB pending flag
                    pending = False
                    try:
                        manager.clear_visualization_pending(
                            outfit_id, error=redis_status.get("error", "Visualization failed")
                        )
                        logger.info(f"Cleared pending flag for failed viz on outfit {outfit_id}")
                    except Exception:
                        pass

            # Fallback: stale timeout (90s safety net)
            if pending and not url:
                saved_at = outfit.get("saved_at", "")
                if saved_at:
                    from datetime import datetime, timezone
                    try:
                        saved_time = datetime.fromisoformat(saved_at.replace("Z", "+00:00"))
                        if (datetime.now(timezone.utc) - saved_time).total_seconds() > 90:
                            pending = False
                            try:
                                manager.clear_visualization_pending(
                                    outfit_id, error="Visualization timed out"
                                )
                            except Exception:
                                pass
                    except (ValueError, TypeError):
                        pending = False

        return {
            "pending": pending,
            "url": url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching viz status for outfit {outfit_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/visualization/status/{viz_key}")
async def get_visualization_status_by_key(viz_key: str):
    """
    Get visualization status by viz_key (for reveal page polling).

    This endpoint is used by the web flow when outfits are generated but not yet saved.
    The viz_key is a hash of the garment image URLs, returned with each outfit during streaming.
    """
    from services.visualization.viz_cache import get_viz_status
    return get_viz_status(viz_key)


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


@router.post("/outfits/{outfit_id}/mark-worn", response_model=MarkWornResponse)
async def mark_outfit_worn(outfit_id: str, request: MarkWornRequest):
    """Mark an outfit as worn"""
    try:
        manager = SavedOutfitsManager(user_id=request.user_id)
        updated = manager.mark_outfit_worn(outfit_id)

        if not updated:
            raise HTTPException(status_code=404, detail="Outfit not found")

        # Log activity
        log_activity(request.user_id, "outfit_marked_worn", {
            "outfit_id": outfit_id
        })

        return MarkWornResponse(
            success=True,
            outfit_id=outfit_id,
            worn_at=updated.get("worn_at", ""),
            worn_photo_url=updated.get("worn_photo_url")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking outfit worn for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outfits/{user_id}/not-worn")
async def get_not_worn_outfits(user_id: str, limit: int = None):
    """Get saved outfits that haven't been worn yet"""
    try:
        manager = SavedOutfitsManager(user_id=user_id)
        not_worn = manager.get_not_worn_outfits(limit=limit)
        return {"outfits": not_worn, "count": len(not_worn)}
    except Exception as e:
        logger.error(f"Error fetching not-worn outfits for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outfits/{user_id}/worn")
async def get_worn_outfits(user_id: str):
    """Get saved outfits that have been worn"""
    try:
        manager = SavedOutfitsManager(user_id=user_id)
        worn = manager.get_worn_outfits()
        return {"outfits": worn, "count": len(worn)}
    except Exception as e:
        logger.error(f"Error fetching worn outfits for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outfits/{outfit_id}/worn-photo")
async def upload_worn_photo(
    outfit_id: str,
    user_id: str = Query(..., description="User ID"),
    file: UploadFile = File(..., description="Photo of user wearing the outfit")
):
    """Upload a photo of the user wearing an outfit and mark it as worn"""
    try:
        # Read and process image
        contents = await file.read()
        image = Image.open(BytesIO(contents))

        # Apply EXIF orientation to ensure correct display
        image = ImageOps.exif_transpose(image)

        # Convert RGBA to RGB if needed (for JPEG compatibility)
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')

        # Save to storage with unique filename
        storage_type = os.getenv("STORAGE_TYPE", "local")
        storage = StorageManager(storage_type=storage_type, user_id=user_id)

        filename = f"worn_{outfit_id}_{uuid.uuid4().hex[:8]}.jpg"
        photo_url = storage.save_image(image, filename, subfolder="worn_photos")

        # Mark outfit as worn with the photo URL
        manager = SavedOutfitsManager(user_id=user_id)
        updated = manager.mark_outfit_worn(outfit_id, worn_photo_url=photo_url)

        if not updated:
            raise HTTPException(status_code=404, detail="Outfit not found")

        # Log activity
        log_activity(user_id, "worn_photo_uploaded", {
            "outfit_id": outfit_id,
            "photo_url": photo_url
        })

        return {
            "success": True,
            "outfit_id": outfit_id,
            "worn_at": updated.get("worn_at", ""),
            "worn_photo_url": photo_url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading worn photo for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


