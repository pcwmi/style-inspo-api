"""
Background workers for outfit generation and image analysis
"""

import os
import sys
import logging
import datetime
from rq import get_current_job

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.style_engine import StyleGenerationEngine
from services.wardrobe_manager import WardrobeManager
from services.user_profile_manager import UserProfileManager
from services.image_analyzer import create_image_analyzer

logger = logging.getLogger(__name__)


from models.schemas import OutfitContext

def generate_outfits_job(user_id, occasions, weather_condition, temperature_range, mode, anchor_items=None):
    """Background job for outfit generation"""
    
    job = get_current_job()
    
    try:
        # Update progress
        if job:
            job.meta['progress'] = 10
            job.save_meta()
        
        # Initialize services
        engine = StyleGenerationEngine()
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
            # Occasion-based generation
            available_items = wardrobe_manager.get_wardrobe_items("regular_wear")
            styling_challenges = wardrobe_manager.get_wardrobe_items("styling_challenges")
            
            combinations = engine.generate_outfit_combinations(
                user_profile=user_profile,
                available_items=available_items,
                styling_challenges=styling_challenges,
                occasion=", ".join(occasions) if occasions else None,
                weather_condition=weather_condition,
                temperature_range=temperature_range
            )
        else:  # mode == "complete"
            # Complete my look - use anchor items
            if not anchor_items:
                raise ValueError("anchor_items required for 'complete' mode")
            
            # Get anchor items
            anchor_item_objects = []
            for item_id in anchor_items:
                for item in all_items:
                    if item.get("id") == item_id:
                        anchor_item_objects.append(item)
                        break
            
            if not anchor_item_objects:
                raise ValueError("Anchor items not found in wardrobe")
            
            # Get all other items
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
            "count": len(combinations)
        }
        
        if job:
            job.meta['progress'] = 100
            job.save_meta()
        
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_outfits_job for {user_id}: {e}")
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
        storage = StorageManager(user_id=user_id)
        
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


