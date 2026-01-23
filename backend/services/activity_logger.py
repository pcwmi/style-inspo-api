"""
Activity Logger - Unified activity tracking for daily digest

Logs all user actions to S3 for comprehensive daily digest.
Each user has a daily activity log: {user_id}/activity/{date}.json
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Optional, Any

from services.storage_manager import StorageManager

logger = logging.getLogger(__name__)

# Use Pacific time for day boundaries
PACIFIC = ZoneInfo("America/Los_Angeles")


class ActivityLogger:
    """
    Append-only activity logger for user actions.

    Usage:
        logger = ActivityLogger("peichin")
        logger.log("outfit_saved", {"outfit_id": "xyz", "reason": "love it"})
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.storage = StorageManager(storage_type="s3", user_id=user_id)

    def log(self, action: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Append an activity to today's log file.

        Args:
            action: Action type (e.g., "outfit_saved", "item_uploaded")
            details: Optional details dict

        Returns:
            True if logged successfully, False otherwise
        """
        try:
            now = datetime.now(PACIFIC)
            date_str = now.strftime("%Y-%m-%d")
            timestamp = now.isoformat()

            filename = f"activity/{date_str}.json"

            # Load existing activities for today
            data = self._load_activity_file(filename)

            # Append new activity
            activity = {
                "timestamp": timestamp,
                "action": action,
                "details": details or {}
            }
            data["activities"].append(activity)

            # Save back
            self.storage.save_json(data, filename)

            logger.info(f"Logged activity: {action} for user {self.user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to log activity {action} for {self.user_id}: {e}")
            return False

    def _load_activity_file(self, filename: str) -> Dict:
        """Load activity file or create empty structure."""
        try:
            data = self.storage.load_json(filename)
            # Ensure it has the right structure
            if "activities" not in data:
                data = self._empty_activity_file()
            return data
        except Exception:
            return self._empty_activity_file()

    def _empty_activity_file(self) -> Dict:
        """Return empty activity file structure."""
        return {
            "date": datetime.now(PACIFIC).strftime("%Y-%m-%d"),
            "activities": []
        }

    def get_activities(self, date_str: str) -> list:
        """
        Get all activities for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            List of activity dicts
        """
        try:
            filename = f"activity/{date_str}.json"
            data = self.storage.load_json(filename)
            return data.get("activities", [])
        except Exception:
            return []


def log_activity(user_id: str, action: str, details: Optional[Dict[str, Any]] = None) -> bool:
    """
    Convenience function to log an activity.

    Usage:
        from services.activity_logger import log_activity
        log_activity("peichin", "outfit_saved", {"reason": "love it"})
    """
    logger = ActivityLogger(user_id)
    return logger.log(action, details)
