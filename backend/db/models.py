"""
Database models (Pydantic schemas for database records)
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class User(BaseModel):
    """User database record"""
    id: UUID
    email: str
    legacy_user_id: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation schema"""
    email: EmailStr
    legacy_user_id: Optional[str] = None


class MagicLinkToken(BaseModel):
    """Magic link token database record"""
    id: UUID
    user_id: Optional[UUID] = None
    email: str
    token: str
    expires_at: datetime
    used_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
