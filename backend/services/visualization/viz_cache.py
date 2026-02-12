"""
Visualization Cache - Redis-backed storage for viz status.

Used by web flow to poll for visualization completion.
SMS flow doesn't need this (push model - sends MMS directly).
"""

import json
import logging
import os
from typing import Optional

import redis

logger = logging.getLogger(__name__)

_redis: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """Get Redis connection (lazy initialization)."""
    global _redis
    if _redis is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                _redis = redis.from_url(redis_url)
                # Test connection
                _redis.ping()
                logger.info("Redis connection established for viz cache")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                _redis = None
    return _redis


def set_viz_pending(viz_key: str, ttl: int = 300) -> bool:
    """
    Mark visualization as pending.

    Args:
        viz_key: Unique key for this visualization (hash of image URLs)
        ttl: Time to live in seconds (default 5 min)

    Returns:
        True if set successfully, False if Redis unavailable
    """
    r = get_redis()
    if r:
        try:
            r.setex(f"viz:{viz_key}", ttl, json.dumps({"status": "pending"}))
            logger.debug(f"Set viz pending: {viz_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to set viz pending: {e}")
    return False


def set_viz_complete(viz_key: str, url: str, ttl: int = 3600) -> bool:
    """
    Store completed visualization URL.

    Args:
        viz_key: Unique key for this visualization
        url: Permanent S3 URL for the visualization image
        ttl: Time to live in seconds (default 1 hour)

    Returns:
        True if set successfully, False if Redis unavailable
    """
    r = get_redis()
    if r:
        try:
            r.setex(f"viz:{viz_key}", ttl, json.dumps({"status": "complete", "url": url}))
            logger.info(f"Set viz complete: {viz_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to set viz complete: {e}")
    return False


def set_viz_failed(viz_key: str, error: str = "", ttl: int = 300) -> bool:
    """
    Mark visualization as failed.

    Args:
        viz_key: Unique key for this visualization
        error: Optional error message
        ttl: Time to live in seconds (default 5 min)

    Returns:
        True if set successfully, False if Redis unavailable
    """
    r = get_redis()
    if r:
        try:
            r.setex(f"viz:{viz_key}", ttl, json.dumps({"status": "failed", "error": error}))
            logger.info(f"Set viz failed: {viz_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to set viz failed: {e}")
    return False


def get_viz_status(viz_key: str) -> dict:
    """
    Get visualization status.

    Args:
        viz_key: Unique key for this visualization

    Returns:
        Dict with:
            - status: "pending" | "complete" | "failed" | "not_found"
            - url: str (only if complete)
            - error: str (only if failed)
    """
    r = get_redis()
    if r:
        try:
            data = r.get(f"viz:{viz_key}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Failed to get viz status: {e}")
    return {"status": "not_found"}
