"""
Background workers for image analysis and outfit generation.
"""

import os
import sys
import logging
import time
from rq import get_current_job

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

logger = logging.getLogger(__name__)

from services.wardrobe_manager import WardrobeManager
from services.image_analyzer import create_image_analyzer
from services.consider_buying_manager import ConsiderBuyingManager


def generate_consider_buying_job(
    user_id: str,
    item_id: str,
    use_existing_similar: bool = False,
    include_reasoning: bool = False
):
    """
    Background job for consider-buying outfit generation using the agent path.

    Runs StylingAgent with APIOutput to generate outfits featuring the
    consider-buying item, then returns results in the format the frontend expects.
    """
    job = get_current_job()

    try:
        logger.info(f"Starting consider-buying job for user {user_id}, item {item_id}")

        if job:
            job.meta['progress'] = 10
            job.meta['status_message'] = "Loading item details..."
            job.meta['current_outfit'] = 0
            job.meta['total_outfits'] = 3
            job.save_meta()

        cb_manager = ConsiderBuyingManager(user_id=user_id)
        wardrobe_manager = WardrobeManager(user_id=user_id)

        consider_item = next((i for i in cb_manager.get_items() if i["id"] == item_id), None)
        if not consider_item:
            raise ValueError(f"Item {item_id} not found in consider_buying")

        # Determine anchor items
        if use_existing_similar:
            similar_item_ids = consider_item.get("similar_items_in_wardrobe", [])
            wardrobe_items = wardrobe_manager.get_wardrobe_items("all")
            anchor_items = [item for item in wardrobe_items if item.get("id") in similar_item_ids]
        else:
            anchor_items = [consider_item]

        # Build anchor item names for the agent message
        anchor_names = [
            item.get("styling_details", {}).get("name", "Unknown item")
            for item in anchor_items
        ]

        if job:
            job.meta['progress'] = 20
            job.meta['status_message'] = "Generating outfits..."
            job.meta['current_outfit'] = 1
            job.save_meta()

        # Run agent
        from agent.agent import StylingAgent
        from agent.output import APIOutput
        from agent.context import preload_user_context

        start_time = time.time()
        output = APIOutput(user_id=user_id)
        preloaded = preload_user_context(user_id, max_items=50)

        agent = StylingAgent(
            user_id=user_id,
            provider="openai",
            output=output,
            preloaded_context=preloaded,
        )

        message = f"Create 3 outfits featuring: {', '.join(anchor_names)}"
        response = agent.fast_generate(message)

        if job:
            job.meta['progress'] = 90
            job.meta['status_message'] = "Finalizing outfits..."
            job.meta['current_outfit'] = 3
            job.save_meta()

        result = {
            "outfits": output.outfits,
            "count": len(output.outfits),
            "anchor_items": anchor_items,
            "metadata": {
                "model": agent.model,
                "latency_ms": int((time.time() - start_time) * 1000),
            },
        }

        if job:
            job.meta['progress'] = 100
            job.meta['status_message'] = "Complete!"
            job.save_meta()

        logger.info(f"Consider-buying job completed: {len(output.outfits)} outfits generated")
        return result

    except Exception as e:
        logger.error(f"Error in consider-buying job: {str(e)}", exc_info=True)
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

        # Log activity
        from services.activity_logger import log_activity
        log_activity(user_id, "item_uploaded", {
            "item_id": item_data["id"] if item_data else None,
            "name": analysis.get("name", "Unknown"),
            "category": analysis.get("category", "unknown")
        })

        # Clean up staged file
        try:
            storage.delete_file(file_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup staged file {file_path}: {e}")

        # Post-upload: enhance garment images with fal.ai (studio-ify)
        # Runs in-band so the item image is upgraded before the user sees it.
        # Also caches bg-removed version for fast collage generation.
        ENHANCE_CATS = {"tops", "bottoms", "dresses", "outerwear", "one-pieces", "scarves"}
        item_cat = analysis.get("category", "").lower()
        item_name = analysis.get("name", "")
        if item_data and item_cat in ENHANCE_CATS:
            try:
                from services.bg_removal import _enhance_garment_fal, _url_to_cache_key, remove_background
                from PIL import Image

                image_url = item_data.get("system_metadata", {}).get("image_url", "")
                if image_url:
                    # Download the just-uploaded image
                    img_data = storage.load_file(image_url)
                    if img_data:
                        enhanced_bytes = _enhance_garment_fal(img_data)
                        if enhanced_bytes:
                            # Update wardrobe image (visible in closet)
                            enhanced_buf = BytesIO(enhanced_bytes)
                            enhanced_buf.name = f"{item_name.replace(' ', '_')}_enhanced.jpg"
                            new_path = wardrobe_manager.update_item_image(item_data["id"], enhanced_buf)
                            logger.info(f"Enhanced wardrobe image for '{item_name}' -> {new_path}")

                            # Cache bg-removed version for fast collages
                            enhanced_img = Image.open(BytesIO(enhanced_bytes))
                            bg_removed = remove_background(enhanced_img)
                            bg_buf = BytesIO()
                            bg_removed.save(bg_buf, format="PNG")
                            bg_buf.seek(0)

                            for url in [image_url, new_path]:
                                if url:
                                    cache_key = _url_to_cache_key(url)
                                    s3_key = f"{user_id}/bg_removed/{cache_key}_enhanced.png"
                                    bg_buf.seek(0)
                                    storage.s3_client.upload_fileobj(
                                        bg_buf, storage.bucket_name, s3_key,
                                        ExtraArgs={"ContentType": "image/png"},
                                    )
                            logger.info(f"Cached bg-removed version for '{item_name}'")
            except Exception as e:
                logger.warning(f"Post-upload enhancement failed for '{item_name}': {e}")

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


def extract_outfit_items_job(user_id, file_path, filename):
    """Background job to extract individual items from an outfit photo.

    Phase A (fast, ~5-8s): Identify items with GPT-4o vision, crop raw images
    (no rembg/analysis/reconstruction), save to wardrobe immediately.
    Phase B (background): Auto-enqueue prettify jobs per item for rembg + reconstruction.

    This gives users something to interact with in ~5s instead of waiting 2-3 min.
    """
    from io import BytesIO
    from PIL import Image
    from services.storage_manager import StorageManager
    from services.image_extractor import OutfitItemExtractor
    from services.activity_logger import log_activity

    job = get_current_job()
    storage_type = os.getenv("STORAGE_TYPE", "local")
    storage = StorageManager(storage_type=storage_type, user_id=user_id)

    try:
        # 10% - Load image
        if job:
            job.meta['progress'] = 10
            job.meta['status_message'] = 'Loading image...'
            job.save_meta()

        image_data = storage.load_file(file_path)
        if not image_data:
            raise FileNotFoundError(f"Could not load file from {file_path}")

        # 20% - Identify items with GPT-4o vision
        if job:
            job.meta['progress'] = 20
            job.meta['status_message'] = 'Identifying items in outfit photo...'
            job.save_meta()

        extractor = OutfitItemExtractor()
        items = extractor.identify_items(image_data)

        if not items:
            if job:
                job.meta['progress'] = 100
                job.meta['status_message'] = 'No items detected in photo'
                job.save_meta()
            return {"items": [], "item_count": 0, "source_photo": file_path}

        source_image = Image.open(BytesIO(image_data))
        total_items = len(items)
        extracted_items = []
        wardrobe_manager = WardrobeManager(user_id=user_id)

        # 30-90% - Crop each item (fast - no rembg, no analysis, no reconstruction)
        for i, item_info in enumerate(items):
            item_progress = 30 + int((i / total_items) * 60)
            if job:
                job.meta['progress'] = item_progress
                job.meta['status_message'] = f'Cropping {item_info["name"]}... ({i+1} of {total_items})'
                job.meta['current_item'] = i + 1
                job.meta['total_items'] = total_items
                job.save_meta()

            try:
                # Crop only - NO rembg, NO GPT-4o analysis, NO reconstruction
                item_bytes = extractor.extract_item(
                    source_image,
                    item_info['bbox_pct'],
                    item_info['name'],
                    remove_bg=False
                )

                # Build analysis from identification-stage data only
                analysis = {
                    'name': item_info.get('name', 'Unknown Item'),
                    'category': item_info.get('category', 'tops'),
                    'sub_category': item_info.get('sub_category', ''),
                    'colors': ', '.join(item_info.get('colors', [])) if isinstance(item_info.get('colors'), list) else item_info.get('colors', ''),
                    'cut': item_info.get('description', ''),
                    'texture': '',
                    'style': '',
                    'fit': '',
                    'brand': None,
                    'trend_status': '',
                    'styling_notes': '',
                    'design_details': '',
                    'fabric': '',
                }

                item_buffer = BytesIO(item_bytes)
                item_buffer.name = f"{item_info['name'].replace(' ', '_')}.png"

                # Add to wardrobe immediately with raw crop
                item_buffer.seek(0)
                item_data = wardrobe_manager.add_wardrobe_item(
                    uploaded_file=item_buffer,
                    analysis_data=analysis,
                    is_styling_challenge=False
                )

                extracted_items.append({
                    "item_id": item_data["id"] if item_data else None,
                    "name": item_info.get("name", "Unknown Item"),
                    "category": item_info.get("category", "tops"),
                    "image_path": item_data.get("system_metadata", {}).get("image_path") if item_data else None,
                    "colors": analysis.get("colors", ""),
                    "prettified": False,
                })

                log_activity(user_id, "item_extracted", {
                    "item_id": item_data["id"] if item_data else None,
                    "name": item_info.get("name", "Unknown Item"),
                    "category": item_info.get("category", "unknown"),
                    "source": "outfit_extraction"
                })

            except Exception as e:
                logger.warning(f"Failed to extract item '{item_info['name']}': {e}")
                continue

        # 100% - Complete (user can start reviewing immediately)
        if job:
            job.meta['progress'] = 100
            job.meta['status_message'] = f'Extracted {len(extracted_items)} items'
            job.meta['extracted_items'] = extracted_items
            job.save_meta()

        # Phase B: Auto-enqueue prettify jobs for each item (background, non-blocking)
        try:
            from redis import Redis
            from rq import Queue
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            redis_conn = Redis.from_url(redis_url)
            prettify_queue = Queue("analysis", connection=redis_conn)

            for i, item in enumerate(extracted_items):
                if item.get("item_id"):
                    prettify_queue.enqueue(
                        prettify_extracted_item_job,
                        user_id,
                        item["item_id"],
                        file_path,
                        items[i],  # original item_info with bbox
                        job_timeout=300
                    )
            logger.info(f"Enqueued {len(extracted_items)} prettify jobs for {user_id}")
        except Exception as e:
            logger.warning(f"Failed to enqueue prettify jobs: {e}")

        # Don't clean up staged file yet - prettify jobs need it
        # Cleanup happens after all prettify jobs complete (or on a delay)

        return {
            "items": extracted_items,
            "item_count": len(extracted_items),
            "source_photo": file_path
        }

    except Exception as e:
        logger.error(f"Error in extract_outfit_items_job for {user_id}: {e}", exc_info=True)
        if job:
            job.meta['error'] = str(e)
            job.save_meta()
        raise


def prettify_extracted_item_job(user_id, item_id, source_photo_path, item_info):
    """Background job to prettify an extracted item (rembg + reconstruction).

    Runs after the fast extraction phase. Updates the wardrobe item's image
    with a clean product-style photo.
    """
    from io import BytesIO
    from PIL import Image
    from services.storage_manager import StorageManager
    from services.image_extractor import OutfitItemExtractor

    job = get_current_job()
    storage_type = os.getenv("STORAGE_TYPE", "local")
    storage = StorageManager(storage_type=storage_type, user_id=user_id)

    try:
        item_name = item_info.get("name", "item")
        logger.info(f"Prettifying '{item_name}' (item_id={item_id}) for {user_id}")

        # Load source photo
        image_data = storage.load_file(source_photo_path)
        if not image_data:
            logger.warning(f"Source photo not found at {source_photo_path}, skipping prettify")
            return {"status": "skipped", "reason": "source_photo_missing"}

        source_image = Image.open(BytesIO(image_data))
        extractor = OutfitItemExtractor()

        # Re-crop with background removal
        item_bytes = extractor.extract_item(
            source_image,
            item_info['bbox_pct'],
            item_info['name'],
            remove_bg=True
        )

        # Build analysis from identification-stage data for reconstruction prompt
        analysis = {
            'name': item_info.get('name', 'Unknown Item'),
            'category': item_info.get('category', 'tops'),
            'colors': ', '.join(item_info.get('colors', [])) if isinstance(item_info.get('colors'), list) else item_info.get('colors', ''),
            'description': item_info.get('description', ''),
        }

        # Reconstruct clean product photo
        reconstructed_bytes = extractor.reconstruct_garment(
            item_bytes=item_bytes,
            analysis=analysis,
            item_info=item_info,
        )

        save_bytes = reconstructed_bytes if reconstructed_bytes else item_bytes

        # Update wardrobe item's image
        wardrobe_manager = WardrobeManager(user_id=user_id)
        item_buffer = BytesIO(save_bytes)
        item_buffer.name = f"{item_name.replace(' ', '_')}_prettified.png"
        new_image_path = wardrobe_manager.update_item_image(item_id, item_buffer)

        if new_image_path:
            logger.info(f"Prettified '{item_name}' successfully -> {new_image_path}")
            return {"status": "complete", "item_id": item_id, "image_path": new_image_path}
        else:
            logger.warning(f"Failed to update image for '{item_name}'")
            return {"status": "failed", "item_id": item_id}

    except Exception as e:
        logger.error(f"Error prettifying item {item_id} for {user_id}: {e}", exc_info=True)
        if job:
            job.meta['error'] = str(e)
            job.save_meta()
        raise
