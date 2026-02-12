"""
Migration script to pre-populate users table with existing users.

Run this script once to:
1. Create user records for existing legacy users
2. Send claim emails to existing users

Usage:
    python -m scripts.migrate_users

Environment variables required:
    - DATABASE_URL: PostgreSQL connection string
    - RESEND_API_KEY: Resend API key for sending emails
    - FRONTEND_URL: Frontend URL for claim links
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from db.database import init_db, close_db, get_db
from services.user_service import UserService
from services.email_service import EmailService
from services.wardrobe_manager import WardrobeManager
from core.config import get_settings

# Existing users with their emails
# Update these with actual email addresses before running
EXISTING_USERS = [
    {"legacy_user_id": "peichin", "email": "peichin@example.com"},  # Update email
    {"legacy_user_id": "heather", "email": "heather@example.com"},  # Update email
    {"legacy_user_id": "john", "email": "john@example.com"},  # Update email
    {"legacy_user_id": "mary", "email": "mary@example.com"},  # Update email - note: case-insensitive
]


async def get_item_count(legacy_user_id: str) -> int:
    """Get number of wardrobe items for a user"""
    try:
        settings = get_settings()
        manager = WardrobeManager(storage_type=settings.STORAGE_TYPE)
        items = manager.get_items(legacy_user_id)
        return len(items)
    except Exception as e:
        print(f"  Warning: Could not get item count for {legacy_user_id}: {e}")
        return 0


async def migrate_user(legacy_user_id: str, email: str, send_email: bool = True) -> bool:
    """Migrate a single user"""
    print(f"\nMigrating user: {legacy_user_id} ({email})")

    try:
        # Check if user already exists
        existing = await UserService.get_user_by_email(email)
        if existing:
            print(f"  User already exists: {existing.id}")
            if not existing.legacy_user_id:
                # Link legacy user ID if not already linked
                await UserService.link_legacy_user(existing.id, legacy_user_id)
                print(f"  Linked legacy user ID: {legacy_user_id}")
            return True

        # Create new user with legacy_user_id
        user = await UserService.create_user(email, legacy_user_id)
        print(f"  Created user: {user.id}")

        if send_email:
            # Get item count for personalized email
            item_count = await get_item_count(legacy_user_id)
            print(f"  Item count: {item_count}")

            # Create claim token and send email
            token = await UserService.create_magic_link_token(email, user.id)
            success = await EmailService.send_claim_email(email, token, legacy_user_id, item_count)

            if success:
                print(f"  Claim email sent successfully")
            else:
                print(f"  Warning: Failed to send claim email")

        return True

    except Exception as e:
        print(f"  Error migrating user: {e}")
        return False


async def main():
    """Main migration function"""
    print("=" * 50)
    print("Style Inspo User Migration")
    print("=" * 50)

    # Check environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("\nError: DATABASE_URL not set")
        print("Please set DATABASE_URL environment variable")
        return

    resend_key = os.getenv("RESEND_API_KEY")
    send_emails = bool(resend_key)
    if not send_emails:
        print("\nWarning: RESEND_API_KEY not set, emails will not be sent")
        print("Magic link URLs will be logged instead")

    # Check if emails are placeholder values
    placeholder_emails = [u for u in EXISTING_USERS if "@example.com" in u["email"]]
    if placeholder_emails:
        print("\n" + "!" * 50)
        print("WARNING: Some users have placeholder emails!")
        print("Please update EXISTING_USERS with real email addresses:")
        for u in placeholder_emails:
            print(f"  - {u['legacy_user_id']}: {u['email']}")
        print("!" * 50)

        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Aborted")
            return

    # Initialize database
    print("\nConnecting to database...")
    try:
        await init_db()
        print("Database connected")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    # Migrate users
    print("\nMigrating users...")
    success_count = 0
    for user_data in EXISTING_USERS:
        result = await migrate_user(
            user_data["legacy_user_id"],
            user_data["email"],
            send_email=send_emails
        )
        if result:
            success_count += 1

    # Summary
    print("\n" + "=" * 50)
    print(f"Migration complete: {success_count}/{len(EXISTING_USERS)} users migrated")
    print("=" * 50)

    # Close database
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
