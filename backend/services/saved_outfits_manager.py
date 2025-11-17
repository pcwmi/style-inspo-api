import json
import os
import uuid
import threading
import sys
from datetime import datetime
from typing import Dict, List, Optional
from services.storage_manager import StorageManager


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


class SavedOutfitsManager:
    """Persist and retrieve saved outfits per user.

    Storage format (S3 or local):
    - S3: {user_id}/saved_outfits.json
    - Local: data/{user_id}/saved_outfits.json

    Data structure (per user):
    {
      "saved": [
        {
          "id": "uuid",
          "outfit_data": {...},
          "user_reason": "Love this!",
          "challenge_item_id": "...",
          "saved_at": "iso"
        }
      ],
      "last_updated": "iso"
    }
    """

    def __init__(self, user_id: str = "default", data_path: str = "data/saved_outfits.json") -> None:
        self.user_id = user_id
        self.legacy_data_path = data_path  # Keep for migration from old multi-user format

        # Initialize storage manager (local or S3 based on env var)
        storage_type = os.getenv("STORAGE_TYPE", "local")
        self.storage = StorageManager(storage_type=storage_type, user_id=user_id)

        # Warn if S3 was requested but fell back to local
        if storage_type == "s3" and self.storage.storage_type == "local":
            _safe_stderr_write(f"⚠️ SavedOutfitsManager: S3 requested but unavailable, using local storage for user '{user_id}'")

        # Perform one-time migration from old multi-user local file to S3
        if self.storage.storage_type == "s3" and user_id not in _MIGRATION_FLAG:
            self._migrate_from_local_if_needed()
            _MIGRATION_FLAG[user_id] = True

    def save_outfit(self, outfit_combo, reason: str = "", occasion: Optional[str] = None) -> bool:
        """Save an outfit combination for the current user.

        Args:
            outfit_combo: OutfitCombination object with items, styling_notes, etc.
            reason: Optional user feedback on why they like it
            occasion: Optional occasion context (e.g., "Business meeting + Coffee")

        Returns:
            True if saved successfully
        """
        try:
            data = self._read_json()
            saved_list = data.setdefault("saved", [])

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

            saved_outfit = {
                "id": str(uuid.uuid4()),
                "outfit_data": outfit_data,
                "user_reason": reason.strip(),
                "challenge_item_id": challenge_item_id,
                "occasion": occasion.strip() if occasion and occasion.strip() else None,
                "saved_at": _now_iso()
            }

            # Add to beginning of list (newest first)
            saved_list.insert(0, saved_outfit)
            data["last_updated"] = _now_iso()

            self._atomic_write(data)
            return True

        except Exception as e:
            print(f"Error saving outfit: {e}")
            return False

    def get_saved_outfits(self) -> List[Dict]:
        """Get all saved outfits for the current user (newest first).

        Returns:
            List of saved outfit dicts
        """
        data = self._read_json()
        return data.get("saved", [])

    def _read_json(self) -> Dict:
        """Read saved outfits data from storage"""
        try:
            data = self.storage.load_json("saved_outfits.json")
            # StorageManager returns default structure for missing files
            # Convert to saved outfits structure if needed
            if "saved" in data:
                return data
            # Return empty structure for new users
            return {"saved": [], "last_updated": None}
        except Exception as e:
            print(f"Error reading saved outfits: {e}")
            return {"saved": [], "last_updated": None}

    def _atomic_write(self, data: Dict) -> None:
        """Write saved outfits data to storage"""
        try:
            with _WRITE_LOCK:
                self.storage.save_json(data, "saved_outfits.json")
        except Exception as e:
            print(f"Error writing saved outfits: {e}")
            raise

    def _migrate_from_local_if_needed(self) -> None:
        """One-time migration from old multi-user local file to new single-user S3 format"""
        try:
            # Check if S3 already has data for this user
            s3_data = self.storage.load_json("saved_outfits.json")
            if s3_data.get("saved"):
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
            user_saved = old_data.get("users", {}).get(self.user_id, {}).get("saved", [])

            if user_saved:
                # Migrate to new single-user format
                new_data = {
                    "saved": user_saved,
                    "last_updated": _now_iso()
                }
                self.storage.save_json(new_data, "saved_outfits.json")
                print(f"✅ Migrated {len(user_saved)} saved outfit(s) for user '{self.user_id}' to S3")

        except Exception as e:
            print(f"⚠️ Error during saved outfits migration for user '{self.user_id}': {e}")
            # Don't raise - allow app to continue with empty saved outfits
