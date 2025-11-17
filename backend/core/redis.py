"""
Redis connection for RQ job queue
"""

from redis import Redis
from core.config import settings
import logging

logger = logging.getLogger(__name__)

# Global Redis connection
redis_conn: Redis = None


def get_redis_connection(decode_responses: bool = False) -> Redis:
    """Get or create Redis connection
    
    Args:
        decode_responses: If True, decode Redis responses as strings.
                         RQ requires False for job serialization.
    """
    global redis_conn
    
    if redis_conn is None:
        try:
            redis_conn = Redis.from_url(settings.REDIS_URL, decode_responses=decode_responses)
            # Test connection
            redis_conn.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    return redis_conn


