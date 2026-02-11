"""
Authentication API endpoints
Magic link email authentication
"""

import os
import jwt
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Response, Cookie
from pydantic import BaseModel, EmailStr

from services.user_service import UserService
from services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter()

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30
COOKIE_NAME = "session"
# In development (HTTP), don't require secure cookies
IS_PRODUCTION = os.getenv("VERCEL_ENV") == "production" or os.getenv("FRONTEND_URL", "").startswith("https://")


class SendMagicLinkRequest(BaseModel):
    """Request to send magic link email"""
    email: EmailStr


class SendMagicLinkResponse(BaseModel):
    """Response after sending magic link"""
    success: bool
    message: str


class VerifyTokenResponse(BaseModel):
    """Response after verifying magic link token"""
    success: bool
    user_id: str
    email: str
    legacy_user_id: Optional[str] = None
    is_new_user: bool


class SessionUser(BaseModel):
    """Current session user info"""
    user_id: str
    email: str
    legacy_user_id: Optional[str] = None


def create_session_token(user_id: str, email: str, legacy_user_id: Optional[str] = None) -> str:
    """Create JWT session token"""
    payload = {
        "user_id": user_id,
        "email": email,
        "legacy_user_id": legacy_user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_session_token(token: str) -> Optional[dict]:
    """Decode and verify JWT session token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Session token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid session token: {e}")
        return None


@router.post("/auth/send-magic-link", response_model=SendMagicLinkResponse)
async def send_magic_link(request: SendMagicLinkRequest):
    """
    Send magic link email for authentication.
    Creates user if they don't exist.
    """
    email = request.email.lower()

    try:
        # Get or create user
        user, is_new = await UserService.get_or_create_user(email)

        # Create magic link token
        token = await UserService.create_magic_link_token(email, user.id)

        # Send email
        email_sent = await EmailService.send_magic_link(email, token)

        if not email_sent:
            raise HTTPException(status_code=500, detail="Failed to send email")

        return SendMagicLinkResponse(
            success=True,
            message="Magic link sent! Check your email."
        )

    except Exception as e:
        logger.error(f"Error sending magic link: {e}")
        raise HTTPException(status_code=500, detail="Failed to send magic link")


@router.get("/auth/verify")
async def verify_magic_link(token: str, response: Response):
    """
    Verify magic link token and set session cookie.
    Returns user info and sets HTTP-only session cookie.
    """
    try:
        # Verify token
        magic_token = await UserService.verify_magic_link_token(token)

        if not magic_token:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        # Get or create user (in case token was created before user)
        user, is_new = await UserService.get_or_create_user(magic_token.email)

        # Mark token as used
        await UserService.mark_token_used(token)

        # Update last login
        await UserService.update_last_login(user.id)

        # Create session token
        session_token = create_session_token(
            str(user.id),
            user.email,
            user.legacy_user_id
        )

        # Set HTTP-only cookie
        response.set_cookie(
            key=COOKIE_NAME,
            value=session_token,
            httponly=True,
            secure=IS_PRODUCTION,  # Only require HTTPS in production
            samesite="none" if IS_PRODUCTION else "lax",  # Cross-origin requires "none"
            max_age=JWT_EXPIRY_DAYS * 24 * 60 * 60,  # 30 days in seconds
            path="/"
        )

        logger.info(f"User logged in: {user.email} (new={is_new})")

        return VerifyTokenResponse(
            success=True,
            user_id=str(user.id),
            email=user.email,
            legacy_user_id=user.legacy_user_id,
            is_new_user=is_new
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying magic link: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify token")


@router.get("/auth/me", response_model=SessionUser)
async def get_current_user(session: Optional[str] = Cookie(None)):
    """
    Get current logged-in user from session cookie.
    Returns 401 if not logged in.
    """
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_session_token(session)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expired")

    return SessionUser(
        user_id=payload["user_id"],
        email=payload["email"],
        legacy_user_id=payload.get("legacy_user_id")
    )


@router.post("/auth/logout")
async def logout(response: Response):
    """
    Clear session cookie to log out user.
    """
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="none" if IS_PRODUCTION else "lax"
    )

    return {"success": True, "message": "Logged out"}


@router.post("/auth/link-legacy")
async def link_legacy_account(
    legacy_user_id: str,
    session: Optional[str] = Cookie(None)
):
    """
    Link a legacy user ID to the current authenticated user.
    Used during migration to connect existing data.
    """
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_session_token(session)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expired")

    user_id = UUID(payload["user_id"])

    try:
        await UserService.link_legacy_user(user_id, legacy_user_id)
        return {"success": True, "message": f"Linked legacy user '{legacy_user_id}'"}
    except Exception as e:
        logger.error(f"Error linking legacy user: {e}")
        raise HTTPException(status_code=500, detail="Failed to link legacy account")
