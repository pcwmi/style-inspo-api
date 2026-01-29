"""
SMS API - Twilio webhook for incoming SMS/MMS.

Flow:
1. User texts: "What should I wear for casual Friday?"
2. We send: "Working on your outfit..." (immediate ack)
3. Background: Agent generates outfit, saves it, triggers visualization
4. We send: MMS with outfit image + styling notes
"""

import os
import logging
import re
from typing import Optional
from fastapi import APIRouter, Form, BackgroundTasks, Response

from services.twilio_service import send_sms, send_mms

router = APIRouter()
logger = logging.getLogger(__name__)

# Phone to user mapping (hardcoded for MVP)
PHONE_TO_USER = {
    os.getenv("PEICHIN_PHONE_NUMBER", ""): "peichin",
}


def phone_to_user(phone: str) -> Optional[str]:
    """Map phone number to user_id."""
    # Strip whatsapp: prefix if present
    normalized = phone.replace("whatsapp:", "")
    # Remove spaces, dashes, parentheses
    normalized = re.sub(r'[\s\-\(\)]', '', normalized)

    for registered_phone, user_id in PHONE_TO_USER.items():
        if registered_phone and normalized.endswith(registered_phone[-10:]):
            return user_id

    logger.warning(f"Unknown phone number: {phone}")
    return None


def is_whatsapp(phone: str) -> bool:
    """Check if this is a WhatsApp number."""
    return phone.startswith("whatsapp:")


async def process_outfit_request(user_id: str, phone: str, message: str):
    """
    Background task to process outfit request.

    1. Run agent with SMS-specific prompt
    2. Agent saves outfit and triggers visualization
    3. Send MMS with result
    """
    try:
        logger.info(f"Processing outfit request for {user_id}: {message}")

        # Import here to avoid circular imports
        from agent.agent import StylingAgent

        # Create agent with SMS-specific instructions
        agent = StylingAgent(user_id=user_id, provider="openai")

        # Add SMS context to the message
        sms_prompt = f"""User request (via SMS): {message}

Create ONE outfit for this occasion. Keep response SHORT (under 250 chars).

Steps:
1. Call get_items to see the wardrobe
2. Pick items that work for this occasion
3. Call save_outfit with item IDs and a brief styling note

Your response should be a brief styling tip - I'll attach the item images separately."""

        # Run agent
        response = agent.run(sms_prompt)

        # Get the most recent saved outfit to extract item images
        from services.saved_outfits_manager import SavedOutfitsManager
        from services.wardrobe_manager import WardrobeManager

        outfit_manager = SavedOutfitsManager(user_id=user_id)
        wardrobe_manager = WardrobeManager(user_id=user_id)

        outfits = outfit_manager.get_saved_outfits()
        image_urls = []

        if outfits:
            # Get the most recent outfit
            latest_outfit = outfits[-1]
            item_ids = [item.get("id") for item in latest_outfit.get("items", [])]

            # Look up image URLs from wardrobe
            all_items = wardrobe_manager.get_wardrobe_items()
            item_lookup = {item["id"]: item for item in all_items}

            for item_id in item_ids:
                if item_id in item_lookup:
                    item = item_lookup[item_id]
                    image_url = item.get("system_metadata", {}).get("image_url")
                    if image_url:
                        image_urls.append(image_url)

        if image_urls:
            # Send MMS with item images
            short_response = response[:280] if len(response) > 280 else response
            # WhatsApp allows up to 10 media items
            send_mms(phone, short_response, image_urls[:5])
            logger.info(f"Sent MMS to {phone} with {len(image_urls)} images")
        else:
            # No images, just send text
            send_sms(phone, response[:1500])
            logger.info(f"Sent SMS to {phone} (no images)")

    except Exception as e:
        logger.error(f"Error processing outfit request: {e}")
        send_sms(phone, "Sorry, I had trouble creating your outfit. Please try again!")


def extract_visualization_url(text: str) -> Optional[str]:
    """
    Extract visualization URL from agent response.

    Looks for S3 URLs or visualization URLs in the text.
    """
    # Pattern for S3/CloudFront URLs
    patterns = [
        r'https://[^"\s]+\.s3\.[^"\s]+\.amazonaws\.com/[^"\s]+',
        r'https://[^"\s]+cloudfront\.net/[^"\s]+',
        r'https://[^"\s]+/visualizations/[^"\s]+\.(png|jpg|jpeg)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            url = match.group(0)
            # Clean up trailing punctuation
            url = url.rstrip('.,;:!?)')
            return url

    return None


@router.post("/incoming")
async def incoming_sms(
    background_tasks: BackgroundTasks,
    From: str = Form(...),
    Body: str = Form(...),
    NumMedia: str = Form(default="0"),
):
    """
    Twilio webhook for incoming SMS.

    Twilio sends:
    - From: Sender phone number
    - Body: Message text
    - NumMedia: Number of attached images
    """
    logger.info(f"Incoming SMS from {From}: {Body[:100]}...")

    # Map phone to user
    user_id = phone_to_user(From)

    if not user_id:
        # Unknown user
        return Response(
            content="""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Hi! I don't recognize this number. Please sign up at styleinspo.vercel.app first.</Message>
</Response>""",
            media_type="application/xml"
        )

    # Send immediate acknowledgment
    send_sms(From, "Working on your outfit... 👗✨ (this takes about a minute)")

    # Queue background processing
    background_tasks.add_task(
        process_outfit_request,
        user_id=user_id,
        phone=From,
        message=Body
    )

    # Return empty TwiML (ack already sent)
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml"
    )


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "sms"}
