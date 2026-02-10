"""
PostgreSQL database connection and initialization
"""

import os
import asyncpg
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


def get_database_url() -> str:
    """Get database URL from environment, with fallback for local dev"""
    return os.getenv("DATABASE_URL", "postgresql://localhost:5432/styleinspo")


async def init_db() -> asyncpg.Pool:
    """Initialize database connection pool and create tables if needed"""
    global _pool

    if _pool is not None:
        return _pool

    database_url = get_database_url()
    logger.info(f"Connecting to database...")

    try:
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        logger.info("Database connection pool created")

        # Create tables if they don't exist
        await create_tables(_pool)

        return _pool
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def create_tables(pool: asyncpg.Pool):
    """Create required tables if they don't exist"""
    async with pool.acquire() as conn:
        # Users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT UNIQUE NOT NULL,
                legacy_user_id TEXT UNIQUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_login TIMESTAMPTZ
            )
        """)

        # Magic link tokens table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS magic_link_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                email TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                used_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Create index on token for fast lookups
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_magic_link_tokens_token
            ON magic_link_tokens(token)
        """)

        # Create index on email for user lookups
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email
            ON users(email)
        """)

        # Create index on legacy_user_id for migration lookups
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_legacy_user_id
            ON users(legacy_user_id)
        """)

        logger.info("Database tables created/verified")


async def get_db() -> asyncpg.Pool:
    """Get database connection pool, initializing if needed"""
    global _pool

    if _pool is None:
        _pool = await init_db()

    return _pool


async def close_db():
    """Close database connection pool"""
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")
