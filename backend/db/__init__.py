"""
Database module for PostgreSQL connectivity
"""

from .database import get_db, init_db, close_db
from .models import User, MagicLinkToken

__all__ = ["get_db", "init_db", "close_db", "User", "MagicLinkToken"]
