"""
Visualization trigger functions - spawn background threads to generate outfit visualizations.

Extracted from api/outfits.py to be shared across agent channels (web, SMS, API).
"""

import hashlib
import logging
import threading

logger = logging.getLogger(__name__)


def trigger_background_visualization(user_id: str, outfit_id: str, items: list):
    """Spawn background thread to generate visualization for saved outfit."""
    from services.saved_outfits_manager import SavedOutfitsManager

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


def trigger_visualization_by_key(user_id: str, viz_key: str, garment_images: list):
    """
    Spawn background thread to generate visualization, store by viz_key.

    Used by streaming endpoint (web flow) - triggers on GENERATE, not save.
    Results stored in Redis by viz_key for frontend polling.
    """
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
                persist_viz_to_saved_outfit(user_id, viz_key, result["visualization_url"])
            else:
                error = result.get("error", "Unknown error") if result else "No result"
                set_viz_failed(viz_key, error)
                clear_viz_pending_for_key(user_id, viz_key, error)
                logger.warning(f"Viz failed for key {viz_key}: {error}")

        except Exception as e:
            from services.visualization.viz_cache import set_viz_failed
            set_viz_failed(viz_key, str(e))
            clear_viz_pending_for_key(user_id, viz_key, str(e))
            logger.error(f"Viz error for key {viz_key}: {e}")

    thread = threading.Thread(target=run_visualization, daemon=True)
    thread.start()
    logger.info(f"Spawned viz thread for key {viz_key}")


def clear_viz_pending_for_key(user_id: str, viz_key: str, error: str):
    """If a saved outfit has this viz_key, clear its pending flag."""
    try:
        from services.saved_outfits_manager import SavedOutfitsManager
        manager = SavedOutfitsManager(user_id=user_id)
        saved_outfits = manager.get_saved_outfits(enrich_with_current_images=False)
        for outfit in saved_outfits:
            if outfit.get("viz_key") == viz_key and outfit.get("visualization_pending"):
                manager.clear_visualization_pending(outfit["id"], error=error)
                logger.info(f"Cleared pending flag for outfit {outfit['id']} (viz_key={viz_key})")
                break
    except Exception as e:
        logger.error(f"Failed to clear viz pending for key {viz_key}: {e}")


def persist_viz_to_saved_outfit(user_id: str, viz_key: str, viz_url: str):
    """If a saved outfit matches this viz_key, persist the URL to S3."""
    try:
        from services.saved_outfits_manager import SavedOutfitsManager
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
