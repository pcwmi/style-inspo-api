"""
Background workers for outfit generation and image analysis
"""

import os
import sys
import logging
import datetime
import time
from rq import get_current_job

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

logger = logging.getLogger(__name__)

try:
    from services.prompts.library import PromptLibrary
except Exception as e:
    logger.error(f"Failed to import PromptLibrary: {e}")
    raise

try:
    from services.style_engine import StyleGenerationEngine
except Exception as e:
    logger.error(f"Failed to import StyleGenerationEngine: {e}")
    raise

from services.wardrobe_manager import WardrobeManager
from services.user_profile_manager import UserProfileManager
from services.image_analyzer import create_image_analyzer
from services.consider_buying_manager import ConsiderBuyingManager
from core.config import get_settings
from models.schemas import OutfitContext

def generate_outfits_job(user_id, occasions, weather_condition, temperature_range, mode, anchor_items=None, mock=False, prompt_version=None, include_reasoning=False):
    """Background job for outfit generation"""
    
    logger.info(f"Starting outfit generation: user_id={user_id}, mode={mode}, prompt_version={prompt_version or 'default'}")
    
    job = get_current_job()
    start_time = time.time()
    
    try:
        # Get prompt version (provided or env default)
        if prompt_version is None:
            prompt_version = get_settings().PROMPT_VERSION
        
        # Update progress
        if job:
            job.meta['progress'] = 10
            job.save_meta()
            
        if mock:
            # Simulate some processing time
            time.sleep(2)
            if job:
                job.meta['progress'] = 50
                job.save_meta()
            time.sleep(1)
            
            # Return mock result
            result = {
                "outfits": [
                    {
                        "items": [
                            {
                                "name": "Mock Shirt",
                                "category": "top",
                                "image_path": "https://placehold.co/400x400/png?text=Mock+Shirt"
                            },
                            {
                                "name": "Mock Jeans",
                                "category": "bottom",
                                "image_path": "https://placehold.co/400x400/png?text=Mock+Jeans"
                            },
                            {
                                "name": "Mock Shoes",
                                "category": "shoes",
                                "image_path": "https://placehold.co/400x400/png?text=Mock+Shoes"
                            }
                        ],
                        "styling_notes": "This is a mock outfit for testing purposes.",
                        "why_it_works": "It's hardcoded to work perfectly!",
                        "confidence_level": "high",
                        "vibe_keywords": ["mock", "test", "fast"],
                        "constitution_principles": {},
                        "context": {
                            "occasions": occasions or ["test"],
                            "weather_condition": weather_condition,
                            "temperature_range": temperature_range
                        }
                    },
                    {
                        "items": [
                            {
                                "name": "Mock Dress",
                                "category": "one-piece",
                                "image_path": "https://placehold.co/400x400/png?text=Mock+Dress"
                            },
                            {
                                "name": "Mock Jacket",
                                "category": "outerwear",
                                "image_path": "https://placehold.co/400x400/png?text=Mock+Jacket"
                            }
                        ],
                        "styling_notes": "Another mock outfit.",
                        "why_it_works": "Testing multiple outfits.",
                        "confidence_level": "medium",
                        "vibe_keywords": ["mock", "alternative"],
                        "constitution_principles": {},
                        "context": {
                            "occasions": occasions or ["test"],
                            "weather_condition": weather_condition,
                            "temperature_range": temperature_range
                        }
                    }
                ],
                "count": 2,
                "metadata": {
                    "prompt_version": prompt_version,
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "latency_ms": int((time.time() - start_time) * 1000)
                }
            }
            
            if job:
                job.meta['progress'] = 100
                job.save_meta()
                
            return result
        
        # Adjust max_tokens based on prompt version
        max_tokens = 3000 if "chain_of_thought" in prompt_version else 2000
        
        # Validate prompt version exists
        try:
            PromptLibrary.get_prompt(prompt_version)
        except ValueError as e:
            logger.error(f"Invalid prompt version '{prompt_version}': {e}", exc_info=True)
            raise
        
        # Initialize StyleGenerationEngine
        try:
            engine = StyleGenerationEngine(
                model="gpt-4o",
                temperature=0.7,
                max_tokens=max_tokens,
                prompt_version=prompt_version
            )
        except Exception as e:
            logger.error(f"Failed to create StyleGenerationEngine with prompt_version '{prompt_version}': {e}", exc_info=True)
            raise
        wardrobe_manager = WardrobeManager(user_id=user_id)
        profile_manager = UserProfileManager(user_id=user_id)
        
        # Create context object
        context = OutfitContext(
            occasions=occasions if occasions else [],
            weather_condition=weather_condition,
            temperature_range=temperature_range
        )
        
        # Get user profile, create default if none exists
        raw_profile = profile_manager.get_profile(user_id)
        if not raw_profile:
            # Create a default profile so outfit generation can proceed
            logger.warning(f"No profile found for user {user_id}, creating default profile")
            try:
                profile_manager.set_style_words(user_id, ["versatile", "confident", "comfortable"])
                raw_profile = profile_manager.get_profile(user_id)
            except Exception as e:
                logger.error(f"Failed to create default profile: {e}")
                # Use in-memory default profile if save fails
                raw_profile = {
                    "style_words": ["versatile", "confident", "comfortable"],
                    "created_at": datetime.datetime.now().isoformat(),
                    "updated_at": datetime.datetime.now().isoformat()
                }
        
        # Convert profile format: style_words array -> three_words dict
        # UserProfileManager returns style_words as array, but style engine expects three_words as dict
        user_profile = {}
        if raw_profile.get("style_words") and len(raw_profile["style_words"]) >= 3:
            # Convert style_words array to three_words dict format
            user_profile["three_words"] = {
                "current": raw_profile["style_words"][0],
                "aspirational": raw_profile["style_words"][1],
                "feeling": raw_profile["style_words"][2]
            }
        else:
            # Default fallback if conversion fails
            user_profile["three_words"] = {
                "current": "versatile",
                "aspirational": "confident",
                "feeling": "comfortable"
            }
        
        # Preserve other profile fields
        user_profile["daily_emotion"] = raw_profile.get("daily_emotion", {})
        
        if job:
            job.meta['progress'] = 20
            job.save_meta()
        
        # Load wardrobe
        all_items = wardrobe_manager.get_wardrobe_items("all")

        if job:
            job.meta['progress'] = 30
            job.meta['status_message'] = "Wardrobe loaded, starting generation..."
            job.save_meta()
        
        # Generate outfits based on mode
        raw_reasoning = None
        
        # Update progress before starting generation
        if job:
            job.meta['progress'] = 40
            job.meta['status_message'] = "Creating outfit 1 of 3..."
            job.meta['current_outfit'] = 1
            job.meta['total_outfits'] = 3
            job.save_meta()
        
        if mode == "occasion":
            # Occasion-based generation - use entire wardrobe, no anchor requirements
            available_items = wardrobe_manager.get_wardrobe_items("all")

            if include_reasoning:
                combinations, raw_reasoning = engine.generate_outfit_combinations(
                    user_profile=user_profile,
                    available_items=available_items,
                    styling_challenges=[],  # No anchor requirements for occasion mode
                    occasion=", ".join(occasions) if occasions else None,
                    weather_condition=weather_condition,
                    temperature_range=temperature_range,
                    include_raw_response=True
                )
            else:
                combinations = engine.generate_outfit_combinations(
                    user_profile=user_profile,
                    available_items=available_items,
                    styling_challenges=[],  # No anchor requirements for occasion mode
                    occasion=", ".join(occasions) if occasions else None,
                    weather_condition=weather_condition,
                    temperature_range=temperature_range,
                    include_raw_response=False
                )
        else:  # mode == "complete"
            # Complete my look - use anchor items
            if not anchor_items:
                raise ValueError("anchor_items required for 'complete' mode")

            # Get anchor items (can be from wardrobe OR considering items)
            anchor_item_objects = []
            for item_id in anchor_items:
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
            available_items = [item for item in all_items if item.get("id") not in anchor_items]

            if include_reasoning:
                combinations, raw_reasoning = engine.generate_outfit_combinations(
                    user_profile=user_profile,
                    available_items=available_items,
                    styling_challenges=anchor_item_objects,
                    weather_condition=weather_condition,
                    temperature_range=temperature_range,
                    include_raw_response=True
                )
            else:
                combinations = engine.generate_outfit_combinations(
                    user_profile=user_profile,
                    available_items=available_items,
                    styling_challenges=anchor_item_objects,
                    weather_condition=weather_condition,
                    temperature_range=temperature_range,
                    include_raw_response=False
                )
        
        if job:
            job.meta['progress'] = 90
            job.meta['status_message'] = "Finalizing outfits..."
            job.meta['current_outfit'] = 3
            job.save_meta()
        
        # Convert to serializable format
        result = {
            "outfits": [
                {
                    "items": [
                        {
                            "id": item.get("id"),  # Preserve ID for future lookups
                            "name": item.get("styling_details", {}).get("name", item.get("name", "Unknown")),
                            "category": item.get("styling_details", {}).get("category", item.get("category", "unknown")),
                            "image_path": item.get("system_metadata", {}).get("image_path", item.get("image_path"))
                        }
                        for item in combo.items
                    ],
                    "styling_notes": combo.styling_notes,
                    "why_it_works": combo.why_it_works,
                    "confidence_level": combo.confidence_level,
                    "vibe_keywords": combo.vibe_keywords,
                    "constitution_principles": combo.constitution_principles or {},
                    "context": context.model_dump()
                }
                for combo in combinations
            ],
            "count": len(combinations),
            "metadata": {
                "prompt_version": prompt_version,
                "model": engine.model,
                "temperature": engine.temperature,
                "latency_ms": int((time.time() - start_time) * 1000)
            }
        }
        
        # Add reasoning if requested
        if include_reasoning and raw_reasoning:
            result["reasoning"] = raw_reasoning
        
        if job:
            job.meta['progress'] = 100
            job.meta['status_message'] = "Complete!"
            job.save_meta()
        
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_outfits_job for {user_id}: {e}", exc_info=True)
        if job:
            job.meta['error'] = str(e)
            job.save_meta()
        raise


def generate_consider_buying_job(
    user_id: str,
    item_id: str,
    use_existing_similar: bool = False,
    include_reasoning: bool = False
):
    """
    Background job for consider-buying outfit generation.
    
    This is a thin wrapper around generate_outfits_job that:
    1. Gets the consider_buying item
    2. Converts it to anchor_items format
    3. Calls generate_outfits_job with mode="complete"
    4. Adds anchor_items to the response

    Args:
        user_id: User identifier
        item_id: ID of the item being considered for purchase
        use_existing_similar: If True, use similar items from wardrobe instead of consider_buying item
        include_reasoning: If True, include chain-of-thought reasoning in response

    Returns:
        Dict with outfits, anchor_items, and optionally reasoning
    """
    job = get_current_job()
    
    try:
        logger.info(f"Starting consider-buying job for user {user_id}, item {item_id}")
        
        # Initial progress
        if job:
            job.meta['progress'] = 10
            job.meta['status_message'] = "Loading item details..."
            job.meta['current_outfit'] = 0
            job.meta['total_outfits'] = 3
            job.save_meta()

        # Initialize managers
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        wardrobe_manager = WardrobeManager(user_id=user_id)

        # Get consider_buying item
        consider_item = next((i for i in cb_manager.get_items() if i["id"] == item_id), None)
        if not consider_item:
            raise ValueError(f"Item {item_id} not found in consider_buying")

        # Determine anchor items
        if use_existing_similar:
            # Use similar items from wardrobe
            similar_item_ids = consider_item.get("similar_items_in_wardrobe", [])
            wardrobe_items = wardrobe_manager.get_wardrobe_items("all")
            anchor_items = [item for item in wardrobe_items if item.get("id") in similar_item_ids]
            anchor_item_ids = similar_item_ids
        else:
            # Use consider_buying item as anchor
            anchor_items = [consider_item]
            anchor_item_ids = [item_id]

        logger.info(f"Anchor items: {len(anchor_items)}")

        # Update progress before generation
        if job:
            job.meta['progress'] = 20
            job.meta['status_message'] = "Preparing to generate outfits..."
            job.save_meta()

        # Call existing generate_outfits_job with mode="complete"
        # This reuses all the existing logic (prompt version, engine setup, user profile, etc.)
        logger.info(f"Calling generate_outfits_job with include_reasoning={include_reasoning}")
        result = generate_outfits_job(
            user_id=user_id,
            occasions=None,
            weather_condition=None,
            temperature_range=None,
            mode="complete",
            anchor_items=anchor_item_ids,
            mock=False,
            prompt_version=None,  # Use default from settings
            include_reasoning=include_reasoning
        )

        # Add anchor_items to response (for consider-buying specific use case)
        result["anchor_items"] = anchor_items

        logger.info(f"Consider-buying job completed: {result.get('count', 0)} outfits generated, has_reasoning={('reasoning' in result)}, reasoning_length={len(result.get('reasoning', '')) if result.get('reasoning') else 0}")
        return result

    except Exception as e:
        logger.error(f"Error in consider-buying job: {str(e)}", exc_info=True)
        raise


def analyze_item_job(user_id, file_path, filename, use_real_ai=True):
    """Background job for image analysis"""
    
    job = get_current_job()
    
    try:
        if job:
            job.meta['progress'] = 10
            job.save_meta()
        
        # Analyze image
        analyzer = create_image_analyzer(use_real_ai=use_real_ai)
        
        # Load file from storage (staging)
        from services.storage_manager import StorageManager
        storage_type = os.getenv("STORAGE_TYPE", "local")
        storage = StorageManager(storage_type=storage_type, user_id=user_id)
        
        image_data = storage.load_file(file_path)
        if not image_data:
            raise FileNotFoundError(f"Could not load file from {file_path}")
        
        from io import BytesIO
        buffer = BytesIO(image_data)
        buffer.name = filename
        
        if job:
            job.meta['progress'] = 50
            job.save_meta()
        
        analysis = analyzer.analyze_clothing_item(buffer)
        
        if job:
            job.meta['progress'] = 80
            job.save_meta()
        
        # Add item to wardrobe
        wardrobe_manager = WardrobeManager(user_id=user_id)
        
        buffer.seek(0)
        item_data = wardrobe_manager.add_wardrobe_item(
            uploaded_file=buffer,
            analysis_data=analysis,
            is_styling_challenge=False
        )
        
        if job:
            job.meta['progress'] = 100
            job.save_meta()
        
        # Clean up staged file
        try:
            storage.delete_file(file_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup staged file {file_path}: {e}") 
        
        return {
            "item_id": item_data["id"] if item_data else None,
            "analysis": analysis,
            "item": item_data
        }
        
    except Exception as e:
        logger.error(f"Error in analyze_item_job for {user_id}: {e}")
        if job:
            job.meta['error'] = str(e)
            job.save_meta()
        raise


