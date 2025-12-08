import json
import os
import uuid
import threading
import sys
from datetime import datetime
from typing import Dict, List, Optional
from services.storage_manager import StorageManager
from services.wardrobe_manager import WardrobeManager


_WRITE_LOCK = threading.Lock()
_MIGRATION_FLAG = {}  # Track which users have been migrated


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _safe_stderr_write(message: str):
    """Safely write to stderr without causing encoding errors"""
    try:
        sys.stderr.write(message + "\n")
        sys.stderr.flush()
    except:
        pass


class DislikedOutfitsManager:
    """Persist and retrieve disliked outfits per user.

    Storage format (S3 or local):
    - S3: {user_id}/disliked_outfits.json
    - Local: data/{user_id}/disliked_outfits.json

    Data structure (per user):
    {
      "disliked": [
        {
          "id": "uuid",
          "outfit_data": {...},
          "user_reason": "Doesn't match my style",
          "challenge_item_id": "...",
          "disliked_at": "iso"
        }
      ],
      "last_updated": "iso"
    }
    """

    def __init__(self, user_id: str = "default", data_path: str = "data/disliked_outfits.json") -> None:
        self.user_id = user_id
        self.legacy_data_path = data_path  # Keep for migration from old multi-user format

        # Initialize storage manager (local or S3 based on env var)
        storage_type = os.getenv("STORAGE_TYPE", "local")
        self.storage = StorageManager(storage_type=storage_type, user_id=user_id)

        # Warn if S3 was requested but fell back to local
        if storage_type == "s3" and self.storage.storage_type == "local":
            _safe_stderr_write(f"⚠️ DislikedOutfitsManager: S3 requested but unavailable, using local storage for user '{user_id}'")

        # Perform one-time migration from old multi-user local file to S3
        if self.storage.storage_type == "s3" and user_id not in _MIGRATION_FLAG:
            self._migrate_from_local_if_needed()
            _MIGRATION_FLAG[user_id] = True

    def dislike_outfit(self, outfit_combo, reason: str = "", occasion: Optional[str] = None, context: Optional[Dict] = None) -> bool:
        """Dislike an outfit combination for the current user.

        Args:
            outfit_combo: OutfitCombination object with items, styling_notes, etc.
            reason: Optional user feedback on where it fell short
            occasion: Optional occasion context (deprecated)
            context: Optional context dict
        """
        try:
            data = self._read_json()
            disliked_list = data.setdefault("disliked", [])

            # Convert outfit_combo to dict for JSON serialization
            outfit_data = {
                "items": [
                    {
                        "id": item.get("id"),
                        "name": item.get("name") or item.get("styling_details", {}).get("name", "Unknown"),
                        "category": item.get("category") or item.get("styling_details", {}).get("category"),
                        "image_path": item.get("image_path") or item.get("system_metadata", {}).get("image_path")
                    }
                    for item in outfit_combo.items
                ],
                "styling_notes": outfit_combo.styling_notes,
                "why_it_works": outfit_combo.why_it_works,
                "confidence_level": outfit_combo.confidence_level,
                "vibe_keywords": outfit_combo.vibe_keywords
            }

            # Get challenge item ID if available
            challenge_item_id = None
            if outfit_combo.items and len(outfit_combo.items) > 0:
                # First item is typically the challenge item
                challenge_item_id = outfit_combo.items[0].get("id")

            disliked_outfit = {
                "id": str(uuid.uuid4()),
                "outfit_data": outfit_data,
                "user_reason": reason.strip(),
                "challenge_item_id": challenge_item_id,
                "occasion": occasion.strip() if occasion and occasion.strip() else None,
                "context": context,
                "disliked_at": _now_iso()
            }

            # Add to beginning of list (newest first)
            disliked_list.insert(0, disliked_outfit)
            data["last_updated"] = _now_iso()

            self._atomic_write(data)
            return True

        except Exception as e:
            print(f"Error disliking outfit: {e}")
            return False

    def get_disliked_outfits(self, enrich_with_current_images: bool = True) -> List[Dict]:
        """Get all disliked outfits for the current user (newest first).

        Args:
            enrich_with_current_images: If True, enrich items with current image_paths from wardrobe
        
        Returns:
            List of disliked outfit dicts
        """
        data = self._read_json()
        disliked_outfits = data.get("disliked", [])
        
        if enrich_with_current_images:
            disliked_outfits = self._enrich_with_current_images(disliked_outfits)
        
        return disliked_outfits
    
    def _enrich_with_current_images(self, disliked_outfits: List[Dict]) -> List[Dict]:
        """Enrich disliked outfit items with current image_paths from wardrobe.
        
        Same logic as SavedOutfitsManager - ensures disliked outfits show current images.
        """
        try:
            wardrobe_manager = WardrobeManager(user_id=self.user_id)
            all_wardrobe_items = wardrobe_manager.get_wardrobe_items("all")
            
            # Create lookup maps
            items_by_id = {item.get("id"): item for item in all_wardrobe_items if item.get("id")}
            items_by_name = {}
            for item in all_wardrobe_items:
                name = item.get("styling_details", {}).get("name") or item.get("name")
                if name:
                    if name not in items_by_name:
                        items_by_name[name] = item
            
            # Enrich each disliked outfit
            enriched_outfits = []
            for disliked_outfit in disliked_outfits:
                outfit_data = disliked_outfit.get("outfit_data", {})
                items = outfit_data.get("items", [])
                
                enriched_items = []
                for item in items:
                    enriched_item = item.copy()
                    item_id = item.get("id")
                    item_name = item.get("name")
                    
                    # Try to find current item from wardrobe
                    current_item = None
                    
                    if item_id and item_id in items_by_id:
                        current_item = items_by_id[item_id]
                    elif item_name and item_name in items_by_name:
                        current_item = items_by_name[item_name]
                    
                    # If found, use current image_path
                    if current_item:
                        current_image_path = (
                            current_item.get("system_metadata", {}).get("image_path") or
                            current_item.get("image_path")
                        )
                        if current_image_path:
                            enriched_item["image_path"] = current_image_path
                            # Also update ID if it was missing
                            if not enriched_item.get("id") and current_item.get("id"):
                                enriched_item["id"] = current_item.get("id")
                    
                    enriched_items.append(enriched_item)
                
                # Create enriched outfit copy
                enriched_outfit = disliked_outfit.copy()
                enriched_outfit["outfit_data"] = outfit_data.copy()
                enriched_outfit["outfit_data"]["items"] = enriched_items
                enriched_outfits.append(enriched_outfit)
            
            return enriched_outfits
            
        except Exception as e:
            # If enrichment fails, return original outfits
            print(f"Warning: Failed to enrich disliked outfits with current images: {e}")
            return disliked_outfits

    def _read_json(self) -> Dict:
        """Read disliked outfits data from storage"""
        try:
            data = self.storage.load_json("disliked_outfits.json")
            # StorageManager returns default structure for missing files
            # Convert to disliked outfits structure if needed
            if "disliked" in data:
                return data
            # Return empty structure for new users
            return {"disliked": [], "last_updated": None}
        except Exception as e:
            print(f"Error reading disliked outfits: {e}")
            return {"disliked": [], "last_updated": None}

    def _atomic_write(self, data: Dict) -> None:
        """Write disliked outfits data to storage"""
        try:
            with _WRITE_LOCK:
                self.storage.save_json(data, "disliked_outfits.json")
        except Exception as e:
            print(f"Error writing disliked outfits: {e}")
            raise

    def _migrate_from_local_if_needed(self) -> None:
        """One-time migration from old multi-user local file to new single-user S3 format"""
        try:
            # Check if S3 already has data for this user
            s3_data = self.storage.load_json("disliked_outfits.json")
            if s3_data.get("disliked"):
                # Already migrated
                return

            # Check if old local file exists
            if not os.path.exists(self.legacy_data_path):
                # No local data to migrate
                return

            # Read old multi-user format
            with open(self.legacy_data_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)

            # Extract this user's data
            user_disliked = old_data.get("users", {}).get(self.user_id, {}).get("disliked", [])

            if user_disliked:
                # Migrate to new single-user format
                new_data = {
                    "disliked": user_disliked,
                    "last_updated": _now_iso()
                }
                self.storage.save_json(new_data, "disliked_outfits.json")
                print(f"✅ Migrated {len(user_disliked)} disliked outfit(s) for user '{self.user_id}' to S3")

        except Exception as e:
            print(f"⚠️ Error during disliked outfits migration for user '{self.user_id}': {e}")
            # Don't raise - allow app to continue with empty disliked outfits
