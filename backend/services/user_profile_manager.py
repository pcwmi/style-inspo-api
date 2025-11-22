import json
import os
import sys
import threading
from datetime import datetime
from typing import Dict, Optional
from services.storage_manager import StorageManager


_WRITE_LOCK = threading.Lock()
_MIGRATION_FLAG = {}  # Track migration per user_id to avoid repeated attempts


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _safe_stderr_write(message: str):
    """Safely write to stderr, handling BrokenPipeError gracefully"""
    try:
        sys.stderr.write(message)
        sys.stderr.flush()
    except BrokenPipeError:
        print(message, end='')
    except Exception:
        pass


class UserProfileManager:
    """Persist and retrieve per-user style profile.

    Uses StorageManager to support both local filesystem and S3 storage.
    Stores JSON at {user_id}/user_profile.json with shape:
    {
      "style_words": [w1, w2, w3],
      "updated_at": iso,
      "created_at": iso
    }
    
    Each user has their own file containing only their profile (no "profiles" wrapper).
    """

    def __init__(self, user_id: str = "default", data_path: str = "data/user_profile.json") -> None:
        self.user_id = user_id
        self.legacy_data_path = data_path  # Keep for migration
        
        # Initialize storage manager (local or S3 based on env var)
        storage_type = os.getenv("STORAGE_TYPE", "local")
        self.storage = StorageManager(storage_type=storage_type, user_id=user_id)
        
        # Check if StorageManager fell back to local (S3 init failed)
        if storage_type == "s3" and self.storage.storage_type == "local":
            warning_msg = f"⚠️ WARNING: S3 storage requested but initialization failed. Using local storage (ephemeral). Profile data will NOT persist across app restarts.\n"
            _safe_stderr_write(warning_msg)
            # Try to show warning in Streamlit UI if available
            try:
                import streamlit as st
                st.warning("⚠️ **Storage Warning**: S3 storage is not available. Your style words will not persist across app restarts. Please check AWS credentials in Streamlit Cloud secrets.")
            except:
                pass
        
        # Ensure legacy local directory exists for backward compatibility
        if self.storage.storage_type == "local":
            os.makedirs(os.path.dirname(self.legacy_data_path), exist_ok=True)
        
        # Perform migration from local to S3 if needed (only once per user_id)
        if self.storage.storage_type == "s3" and user_id not in _MIGRATION_FLAG:
            self._migrate_from_local_if_needed()
            _MIGRATION_FLAG[user_id] = True

    # Public API
    def get_profile(self, user_id: str) -> Optional[Dict]:
        """Get profile for the specified user_id.
        
        Note: user_id parameter is kept for API compatibility but should match self.user_id.
        Returns single profile dict or None if not found.
        """
        if user_id != self.user_id:
            _safe_stderr_write(f"⚠️ WARNING: get_profile called with user_id={user_id} but manager initialized for {self.user_id}\n")
        profile = self._read_json()
        # Return None if profile is empty (no style_words)
        if not profile or "style_words" not in profile:
            return None
        return profile

    def set_style_words(self, user_id: str, words: [str]) -> Dict:
        """Set style words for the specified user_id.
        
        Note: user_id parameter is kept for API compatibility but should match self.user_id.
        Returns the saved profile dict.
        """
        if user_id != self.user_id:
            _safe_stderr_write(f"⚠️ WARNING: set_style_words called with user_id={user_id} but manager initialized for {self.user_id}\n")
        
        words = [w.strip() for w in words if isinstance(w, str)]
        if len(words) != 3:
            raise ValueError("style_words must contain exactly three strings")

        try:
            profile = self._read_json()
            now = _now_iso()
            
            # Update or create profile
            if not profile or "style_words" not in profile:
                # New profile
                profile = {
                    "style_words": words,
                    "created_at": now,
                    "updated_at": now,
                }
            else:
                # Update existing profile
                profile["style_words"] = words
                profile["updated_at"] = now
                # Preserve created_at if it exists
                if "created_at" not in profile:
                    profile["created_at"] = now

            self._atomic_write(profile)
            _safe_stderr_write(f"✅ Profile saved for user: {user_id}\n")
            return profile
        except Exception as e:
            error_msg = f"❌ Failed to save profile for user {user_id}: {e}\n"
            _safe_stderr_write(error_msg)
            raise RuntimeError(f"Failed to save style words: {e}") from e

    def save_profile(self, profile_data: Dict) -> bool:
        """Save profile data (accepts three_words dict format from API).
        
        Args:
            profile_data: Dict with optional keys:
                - three_words: Dict[str, str] with keys "current", "aspirational", "feeling"
                - daily_emotion: Dict[str, str]
        
        Returns:
            True on success, False on failure
        """
        try:
            profile = self._read_json()
            now = _now_iso()
            
            # Convert three_words dict to style_words array if provided
            if "three_words" in profile_data and profile_data["three_words"]:
                three_words = profile_data["three_words"]
                if isinstance(three_words, dict):
                    # Extract words in order: current, aspirational, feeling
                    words = [
                        three_words.get("current", "").strip(),
                        three_words.get("aspirational", "").strip(),
                        three_words.get("feeling", "").strip()
                    ]
                    # Validate all three words are present
                    if not all(words):
                        raise ValueError("three_words must contain 'current', 'aspirational', and 'feeling' keys with non-empty values")
                    profile_data["style_words"] = words
                    # Remove three_words from profile_data since we store as style_words
                    del profile_data["three_words"]
            
            # Update or create profile
            if not profile or "style_words" not in profile:
                # New profile
                profile = {
                    "created_at": now,
                    "updated_at": now,
                }
            else:
                # Update existing profile
                profile["updated_at"] = now
                # Preserve created_at if it exists
                if "created_at" not in profile:
                    profile["created_at"] = now
            
            # Merge new data into profile
            profile.update(profile_data)
            
            self._atomic_write(profile)
            _safe_stderr_write(f"✅ Profile saved for user: {self.user_id}\n")
            return True
        except Exception as e:
            error_msg = f"❌ Failed to save profile for user {self.user_id}: {e}\n"
            _safe_stderr_write(error_msg)
            import traceback
            _safe_stderr_write(f"Traceback: {traceback.format_exc()}\n")
            return False

    # Internal helpers
    def _read_json(self) -> Dict:
        """Read single-user profile JSON from storage (S3 or local) with error handling.
        
        Returns single profile dict: {"style_words": [...], "created_at": ..., "updated_at": ...}
        Handles backward compatibility with old multi-user format.
        """
        try:
            _safe_stderr_write(f"📖 Reading profile JSON for user {self.user_id} (storage: {self.storage.storage_type})\n")
            data = self.storage.load_json("user_profile.json")
            _safe_stderr_write(f"📖 Raw data from storage: {list(data.keys()) if isinstance(data, dict) else type(data)}\n")
            
            # StorageManager returns default wardrobe structure {"items": [], ...} when file doesn't exist
            if "items" in data and "profiles" not in data and "style_words" not in data:
                # This is the default wardrobe structure, meaning file doesn't exist yet
                _safe_stderr_write(f"⚠️ Profile file doesn't exist yet for user {self.user_id}\n")
                return {}
            
            # Backward compatibility: Check if old multi-user format exists
            if "profiles" in data:
                _safe_stderr_write(f"🔄 Detected old multi-user format, migrating to single-user format for user {self.user_id}\n")
                # Extract only current user's profile
                profiles = data.get("profiles", {})
                if self.user_id in profiles:
                    profile = profiles[self.user_id]
                    # Try to migrate to new format by saving single profile
                    # If migration fails, still return the extracted profile
                    try:
                        self._atomic_write(profile)
                        _safe_stderr_write(f"✅ Migrated profile to single-user format for user {self.user_id}\n")
                    except Exception as e:
                        _safe_stderr_write(f"⚠️ Migration write failed for user {self.user_id}: {e}, but returning extracted profile\n")
                    return profile
                else:
                    _safe_stderr_write(f"⚠️ User {self.user_id} not found in old format, returning empty profile\n")
                    return {}
            
            # New single-user format: Check if it's a valid profile structure
            if "style_words" in data:
                _safe_stderr_write(f"✅ Found profile for user {self.user_id}\n")
                return data
            
            # Unexpected structure
            _safe_stderr_write(f"⚠️ Unexpected data structure in profile JSON for user {self.user_id}, returning empty profile\n")
            return {}
        except Exception as e:
            error_msg = f"⚠️ Failed to read profile JSON for user {self.user_id}: {e}\n"
            _safe_stderr_write(error_msg)
            import traceback
            _safe_stderr_write(f"Traceback: {traceback.format_exc()}\n")
            # Return empty structure on error (user can re-enter words)
            return {}

    def _atomic_write(self, profile_data: Dict) -> None:
        """Write single-user profile JSON to storage (S3 or local) with error handling.
        
        Args:
            profile_data: Single profile dict with style_words, created_at, updated_at
        """
        try:
            _safe_stderr_write(f"💾 Writing profile JSON for user {self.user_id} (storage: {self.storage.storage_type})\n")
            # Ensure we're not accidentally writing old multi-user format
            if "profiles" in profile_data:
                _safe_stderr_write(f"⚠️ WARNING: Attempted to write multi-user format, extracting single profile\n")
                profiles = profile_data.get("profiles", {})
                if self.user_id in profiles:
                    profile_data = profiles[self.user_id]
                else:
                    raise ValueError(f"User {self.user_id} not found in multi-user data structure")
            
            with _WRITE_LOCK:
                self.storage.save_json(profile_data, "user_profile.json")
            _safe_stderr_write(f"✅ Profile JSON written for user: {self.user_id}\n")
        except Exception as e:
            error_msg = f"❌ Failed to write profile JSON for user {self.user_id}: {e}\n"
            _safe_stderr_write(error_msg)
            import traceback
            _safe_stderr_write(f"Traceback: {traceback.format_exc()}\n")
            raise RuntimeError(f"Failed to save profile data: {e}") from e

    def _migrate_from_local_if_needed(self) -> None:
        """Migrate single user's profile from local data/user_profile.json to S3.
        
        Only migrates the current user_id's profile, not all profiles.
        """
        if not os.path.exists(self.legacy_data_path):
            return
        
        try:
            # Check if S3 already has data (in new single-user format)
            s3_profile = self._read_json()
            if s3_profile and "style_words" in s3_profile:
                _safe_stderr_write(f"✅ S3 already has profile data for user {self.user_id}, skipping migration\n")
                return
            
            # Read local file (may contain multi-user format)
            with open(self.legacy_data_path, "r", encoding="utf-8") as f:
                local_data = json.load(f)
            
            # Extract current user's profile from local file
            if "profiles" in local_data:
                # Old multi-user format
                profiles = local_data.get("profiles", {})
                if self.user_id in profiles:
                    user_profile = profiles[self.user_id]
                    # Save only this user's profile to S3 (single-user format)
                    self._atomic_write(user_profile)
                    _safe_stderr_write(f"✅ Migrated profile for user {self.user_id} from local to S3 (single-user format)\n")
                else:
                    _safe_stderr_write(f"⚠️ User {self.user_id} not found in local profile file, skipping migration\n")
            elif "style_words" in local_data:
                # Already in single-user format (unlikely but possible)
                self._atomic_write(local_data)
                _safe_stderr_write(f"✅ Migrated single-user profile for user {self.user_id} from local to S3\n")
            else:
                _safe_stderr_write(f"⚠️ Local profile file exists but has no valid profile data, skipping migration\n")
            
            # Optionally keep local file as backup (don't delete)
            _safe_stderr_write(f"ℹ️ Local profile file kept as backup at {self.legacy_data_path}\n")
            
        except Exception as e:
            error_msg = f"⚠️ Migration from local to S3 failed for user {self.user_id}: {e}\n"
            _safe_stderr_write(error_msg)
            import traceback
            _safe_stderr_write(f"Traceback: {traceback.format_exc()}\n")
            # Don't raise - migration failure shouldn't break the app


