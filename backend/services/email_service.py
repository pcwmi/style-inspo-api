"""
Email service using Resend
"""

import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "Style Inspo <noreply@styleinspo.vercel.app>")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://styleinspo.vercel.app")


class EmailService:
    """Service for sending emails via Resend"""

    @staticmethod
    async def send_magic_link(email: str, token: str) -> bool:
        """Send magic link email to user"""
        if not RESEND_API_KEY:
            logger.warning("RESEND_API_KEY not configured, skipping email send")
            # In development, log the link instead
            magic_link = f"{FRONTEND_URL}/auth?token={token}"
            logger.info(f"Magic link for {email}: {magic_link}")
            return True

        magic_link = f"{FRONTEND_URL}/auth?token={token}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {RESEND_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": RESEND_FROM_EMAIL,
                        "to": [email],
                        "subject": "Sign in to Style Inspo",
                        "html": _magic_link_template(magic_link)
                    }
                )

                if response.status_code == 200:
                    logger.info(f"Magic link email sent to {email}")
                    return True
                else:
                    logger.error(f"Failed to send email: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    @staticmethod
    async def send_claim_email(email: str, token: str, legacy_user_id: str, item_count: int) -> bool:
        """Send claim account email to existing user"""
        if not RESEND_API_KEY:
            logger.warning("RESEND_API_KEY not configured, skipping email send")
            claim_link = f"{FRONTEND_URL}/auth?token={token}&claim=true"
            logger.info(f"Claim link for {email}: {claim_link}")
            return True

        claim_link = f"{FRONTEND_URL}/auth?token={token}&claim=true"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {RESEND_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": RESEND_FROM_EMAIL,
                        "to": [email],
                        "subject": "Your Style Inspo account is ready!",
                        "html": _claim_account_template(claim_link, legacy_user_id, item_count)
                    }
                )

                if response.status_code == 200:
                    logger.info(f"Claim email sent to {email}")
                    return True
                else:
                    logger.error(f"Failed to send claim email: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error sending claim email: {e}")
            return False


def _magic_link_template(magic_link: str) -> str:
    """HTML template for magic link email"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #FAF9F6;">
        <div style="background-color: white; border-radius: 8px; padding: 40px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h1 style="color: #1a1a1a; font-size: 24px; margin-bottom: 16px;">Sign in to Style Inspo</h1>

            <p style="color: #4a4a4a; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">
                Click the button below to sign in to your Style Inspo account. This link will expire in 15 minutes.
            </p>

            <a href="{magic_link}"
               style="display: inline-block; background-color: #C4704B; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 500; font-size: 16px;">
                Sign In
            </a>

            <p style="color: #888; font-size: 14px; margin-top: 32px; line-height: 1.5;">
                If you didn't request this email, you can safely ignore it.
            </p>

            <p style="color: #888; font-size: 14px; margin-top: 16px;">
                Or copy this link: <br>
                <span style="color: #666; word-break: break-all;">{magic_link}</span>
            </p>
        </div>
    </body>
    </html>
    """


def _claim_account_template(claim_link: str, legacy_user_id: str, item_count: int) -> str:
    """HTML template for claim account email"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #FAF9F6;">
        <div style="background-color: white; border-radius: 8px; padding: 40px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h1 style="color: #1a1a1a; font-size: 24px; margin-bottom: 16px;">Your Style Inspo account is ready!</h1>

            <p style="color: #4a4a4a; font-size: 16px; line-height: 1.6; margin-bottom: 16px;">
                Great news! We've set up a secure account for you. Your {item_count} wardrobe items and all your saved outfits are ready and waiting.
            </p>

            <p style="color: #4a4a4a; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">
                Click below to claim your account and continue where you left off.
            </p>

            <a href="{claim_link}"
               style="display: inline-block; background-color: #C4704B; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 500; font-size: 16px;">
                Claim My Account
            </a>

            <p style="color: #888; font-size: 14px; margin-top: 32px; line-height: 1.5;">
                This link will expire in 15 minutes. If you didn't expect this email, you can safely ignore it.
            </p>
        </div>
    </body>
    </html>
    """
