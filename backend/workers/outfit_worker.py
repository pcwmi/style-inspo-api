"""
Background workers for outfit generation and image analysis
"""

import os
import sys
import logging
import datetime
import traceback
import json
from rq import get_current_job

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

logger = logging.getLogger(__name__)

# Helper function for safe debug logging (works in both local and production)
DEBUG_LOG_PATH = '/Users/peichin/Projects/style-inspo/.cursor/debug.log'
def _debug_log(location, message, data, hypothesis_id="A", run_id="run1", level="error"):
    """Safely log debug info to file (if available) and logger
    
    Args:
        level: "error" (always visible in Railway) or "debug" (may be filtered)
    """
    log_entry = {
        "sessionId": "debug-session",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(datetime.datetime.now().timestamp() * 1000)
    }
    # Always log to logger - use ERROR level so it shows up in Railway logs
    log_msg = f"[DEBUG-{hypothesis_id}] {location}: {message} | {json.dumps(data)}"
    if level == "error":
        logger.error(log_msg)
    else:
        logger.debug(log_msg)
    # Also print to stderr (Railway captures this)
    print(f"[DEBUG-{hypothesis_id}] {location}: {message} | {json.dumps(data)}", file=sys.stderr)
    # Try to write to file (only works locally)
    try:
        if os.path.exists(os.path.dirname(DEBUG_LOG_PATH)):
            with open(DEBUG_LOG_PATH, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
    except Exception:
        pass  # Silently fail if file write doesn't work

# #region agent log
_debug_log("outfit_worker.py:15", "Before import - checking sys.path", {"backend_dir": backend_dir, "sys_path": sys.path[:3]})
# #endregion

# #region agent log
try:
    from services.prompts.library import PromptLibrary
    _debug_log("outfit_worker.py:20", "PromptLibrary import successful", {})
except Exception as e:
    _debug_log("outfit_worker.py:22", "PromptLibrary import FAILED", {"error": str(e), "traceback": traceback.format_exc()})
    logger.error(f"Failed to import PromptLibrary: {e}")
# #endregion

# #region agent log
try:
    from services.style_engine import StyleGenerationEngine
    _debug_log("outfit_worker.py:30", "StyleGenerationEngine import successful", {})
except Exception as e:
    _debug_log("outfit_worker.py:32", "StyleGenerationEngine import FAILED", {"error": str(e), "traceback": traceback.format_exc()})
    logger.error(f"Failed to import StyleGenerationEngine: {e}")
    raise
# #endregion

from services.wardrobe_manager import WardrobeManager
from services.user_profile_manager import UserProfileManager
from services.image_analyzer import create_image_analyzer
from core.config import get_settings
import time


from models.schemas import OutfitContext

def generate_outfits_job(user_id, occasions, weather_condition, temperature_range, mode, anchor_items=None, mock=False, prompt_version=None):
    """Background job for outfit generation"""
    
    job = get_current_job()
    start_time = time.time()
    
    try:
        # Get prompt version (provided or env default)
        # #region agent log
        _debug_log("outfit_worker.py:83", "Before getting prompt_version", {"prompt_version_param": prompt_version}, "C")
        # #endregion
        
        if prompt_version is None:
            prompt_version = get_settings().PROMPT_VERSION
        
        # #region agent log
        _debug_log("outfit_worker.py:91", "After getting prompt_version", {"prompt_version": prompt_version, "type": type(prompt_version).__name__}, "C")
        # #endregion
        
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
        
        # #region agent log
        _debug_log("outfit_worker.py:186", "Before creating StyleGenerationEngine", {"prompt_version": prompt_version, "max_tokens": max_tokens, "sys_path_exists": os.path.exists(backend_dir)}, "B,C,D", "error")
        # #endregion
        
        # #region agent log
        try:
            _debug_log("outfit_worker.py:189", "Calling PromptLibrary.get_prompt", {"prompt_version": prompt_version}, "C", "error")
            prompt_obj = PromptLibrary.get_prompt(prompt_version)
            _debug_log("outfit_worker.py:191", "PromptLibrary.get_prompt successful", {"prompt_version": prompt_version, "prompt_type": type(prompt_obj).__name__}, "C", "error")
        except Exception as e:
            _debug_log("outfit_worker.py:193", "PromptLibrary.get_prompt FAILED", {"prompt_version": prompt_version, "error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}, "C", "error")
            logger.error(f"PromptLibrary.get_prompt failed for version '{prompt_version}': {e}", exc_info=True)
            raise
        # #endregion
        
        # Initialize services
        # #region agent log
        _debug_log("outfit_worker.py:200", "About to create StyleGenerationEngine", {"prompt_version": prompt_version, "max_tokens": max_tokens, "model": "gpt-4o"}, "B,C,D", "error")
        try:
            engine = StyleGenerationEngine(
                model="gpt-4o",
                temperature=0.7,
                max_tokens=max_tokens,
                prompt_version=prompt_version
            )
            _debug_log("outfit_worker.py:209", "StyleGenerationEngine created successfully", {"prompt_version": prompt_version, "engine_prompt_version": getattr(engine, 'prompt_version', 'N/A')}, "B,C,D", "error")
        except Exception as e:
            _debug_log("outfit_worker.py:211", "StyleGenerationEngine creation FAILED", {"prompt_version": prompt_version, "error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}, "B,C,D", "error")
            logger.error(f"Failed to create StyleGenerationEngine with prompt_version '{prompt_version}': {e}", exc_info=True)
            print(f"ERROR: StyleGenerationEngine creation failed: {e}", file=sys.stderr)
            print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
            raise
        # #endregion
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
            job.save_meta()
        
        # Generate outfits based on mode
        if mode == "occasion":
            # Occasion-based generation - use entire wardrobe, no anchor requirements
            available_items = wardrobe_manager.get_wardrobe_items("all")

            combinations = engine.generate_outfit_combinations(
                user_profile=user_profile,
                available_items=available_items,
                styling_challenges=[],  # No anchor requirements for occasion mode
                occasion=", ".join(occasions) if occasions else None,
                weather_condition=weather_condition,
                temperature_range=temperature_range
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
            
            combinations = engine.generate_outfit_combinations(
                user_profile=user_profile,
                available_items=available_items,
                styling_challenges=anchor_item_objects,
                weather_condition=weather_condition,
                temperature_range=temperature_range
            )
        
        if job:
            job.meta['progress'] = 90
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
        
        if job:
            job.meta['progress'] = 100
            job.save_meta()
        
        return result
        
    except Exception as e:
        # #region agent log
        _debug_log("outfit_worker.py:368", "Exception caught in generate_outfits_job", {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc(), "user_id": user_id}, "ALL")
        # #endregion
        logger.error(f"Error in generate_outfits_job for {user_id}: {e}", exc_info=True)
        if job:
            job.meta['error'] = str(e)
            job.save_meta()
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


