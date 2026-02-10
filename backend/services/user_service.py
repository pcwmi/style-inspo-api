"""
User service for database operations
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
import asyncpg
import logging

from db.database import get_db
from db.models import User, MagicLinkToken

logger = logging.getLogger(__name__)

# Token expiry in minutes
MAGIC_LINK_EXPIRY_MINUTES = 15


class UserService:
    """Service for user-related database operations"""

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email address"""
        pool = await get_db()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE email = $1",
                email.lower()
            )
            if row:
                return User(**dict(row))
            return None

    @staticmethod
    async def get_user_by_id(user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        pool = await get_db()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                user_id
            )
            if row:
                return User(**dict(row))
            return None

    @staticmethod
    async def get_user_by_legacy_id(legacy_user_id: str) -> Optional[User]:
        """Get user by legacy user ID (for migration)"""
        pool = await get_db()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE legacy_user_id = $1",
                legacy_user_id.lower()
            )
            if row:
                return User(**dict(row))
            return None

    @staticmethod
    async def create_user(email: str, legacy_user_id: Optional[str] = None) -> User:
        """Create a new user"""
        pool = await get_db()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (email, legacy_user_id)
                VALUES ($1, $2)
                RETURNING *
                """,
                email.lower(),
                legacy_user_id.lower() if legacy_user_id else None
            )
            logger.info(f"Created new user: {email}")
            return User(**dict(row))

    @staticmethod
    async def get_or_create_user(email: str) -> tuple[User, bool]:
        """Get existing user or create new one. Returns (user, is_new)"""
        user = await UserService.get_user_by_email(email)
        if user:
            return user, False

        user = await UserService.create_user(email)
        return user, True

    @staticmethod
    async def update_last_login(user_id: UUID):
        """Update user's last login timestamp"""
        pool = await get_db()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login = $1 WHERE id = $2",
                datetime.now(timezone.utc),
                user_id
            )

    @staticmethod
    async def link_legacy_user(user_id: UUID, legacy_user_id: str):
        """Link a legacy user ID to an authenticated user"""
        pool = await get_db()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET legacy_user_id = $1 WHERE id = $2",
                legacy_user_id.lower(),
                user_id
            )
            logger.info(f"Linked legacy user '{legacy_user_id}' to user {user_id}")

    # Magic Link Token Operations

    @staticmethod
    async def create_magic_link_token(email: str, user_id: Optional[UUID] = None) -> str:
        """Create a magic link token for authentication"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=MAGIC_LINK_EXPIRY_MINUTES)

        pool = await get_db()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO magic_link_tokens (email, user_id, token, expires_at)
                VALUES ($1, $2, $3, $4)
                """,
                email.lower(),
                user_id,
                token,
                expires_at
            )

        logger.info(f"Created magic link token for: {email}")
        return token

    @staticmethod
    async def verify_magic_link_token(token: str) -> Optional[MagicLinkToken]:
        """Verify a magic link token and return it if valid"""
        pool = await get_db()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM magic_link_tokens
                WHERE token = $1
                  AND expires_at > $2
                  AND used_at IS NULL
                """,
                token,
                datetime.now(timezone.utc)
            )

            if row:
                return MagicLinkToken(**dict(row))
            return None

    @staticmethod
    async def mark_token_used(token: str):
        """Mark a magic link token as used"""
        pool = await get_db()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE magic_link_tokens SET used_at = $1 WHERE token = $2",
                datetime.now(timezone.utc),
                token
            )

    @staticmethod
    async def cleanup_expired_tokens():
        """Clean up expired tokens (can be run periodically)"""
        pool = await get_db()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM magic_link_tokens WHERE expires_at < $1",
                datetime.now(timezone.utc)
            )
            logger.info(f"Cleaned up expired tokens: {result}")
