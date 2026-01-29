"""
SMS API - Twilio webhook for incoming SMS/MMS.

Flow:
1. User texts: "What should I wear for casual Friday?"
2. We send: "Working on your outfit..." (immediate ack)
3. Background: Agent generates outfit with item NAMES (not IDs)
4. We fuzzy match item names to wardrobe to get images
5. We generate a grid collage of the items
6. We send: MMS with collage + styling notes
"""

import os
import logging
import re
from typing import Optional, List
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


def extract_item_names(response: str) -> List[str]:
    """
    Extract item names from agent response.

    Expects format:
    ITEMS:
    - Item name 1
    - Item name 2

    Also handles variations like:
    Items: item1, item2, item3
    """
    items = []

    # Try structured ITEMS: format first
    if "ITEMS:" in response.upper():
        # Find the ITEMS section
        upper_response = response.upper()
        items_start = upper_response.find("ITEMS:")
        items_section = response[items_start + 6:]  # Skip "ITEMS:"

        lines = items_section.strip().split("\n")
        for line in lines:
            line = line.strip()
            # Stop at empty line or next section header
            if not line:
                break
            if line.rstrip(":").isupper() and len(line) > 2:
                break

            # Remove bullet point markers
            if line.startswith("-"):
                line = line[1:].strip()
            elif line.startswith("•"):
                line = line[1:].strip()
            elif line.startswith("*"):
                line = line[1:].strip()
            elif line[0].isdigit() and "." in line[:3]:
                line = line.split(".", 1)[1].strip()

            if line:
                items.append(line)

    return items


async def process_outfit_request(user_id: str, phone: str, message: str):
    """
    Background task to process outfit request.

    New architecture:
    1. Run agent - returns text with item names (ITEMS: section)
    2. Extract item names from response
    3. Fuzzy match to wardrobe (reuses reveal page logic)
    4. Generate grid collage from matched items
    5. Send MMS with collage image + styling notes
    """
    try:
        logger.info(f"Processing outfit request for {user_id}: {message}")

        # Import here to avoid circular imports
        from agent.agent import StylingAgent
        from primitives.matching import match_items_to_wardrobe
        from services.collage import generate_outfit_collage

        # Create agent with SMS-specific instructions
        agent = StylingAgent(user_id=user_id, provider="openai")

        # SMS prompt - agent returns item NAMES (not IDs)
        # This avoids the save_outfit workaround and lets fuzzy matching handle images
        sms_prompt = f"""User request (via SMS): {message}

Create ONE outfit for this occasion.

Return your response in this format:
[Brief styling tip - keep it under 200 characters]

ITEMS:
- [exact item name from wardrobe]
- [exact item name from wardrobe]
- [exact item name from wardrobe]
- [exact item name from wardrobe]

Important:
- Use EXACT item names as they appear in the wardrobe
- Include 3-5 items (top, bottom, shoes, optional accessories)
- Keep styling tip SHORT - it will be sent via text message"""

        # Run agent
        response = agent.run(sms_prompt)
        logger.info(f"Agent response: {response[:200]}...")

        # Extract item names from response
        item_names = extract_item_names(response)
        logger.info(f"Extracted {len(item_names)} item names: {item_names}")

        # Fuzzy match to wardrobe
        if item_names:
            matched_items = match_items_to_wardrobe(user_id, item_names)
            logger.info(f"Matched {len(matched_items)} items")

            # Get image URLs from matched items
            image_urls = [
                item["image_path"]
                for item in matched_items
                if item.get("image_path")
            ]
            logger.info(f"Found {len(image_urls)} images")

            if image_urls:
                # Generate collage
                collage_url = generate_outfit_collage(user_id, image_urls)

                if collage_url:
                    # Send MMS with collage image only (no text - it's redundant)
                    send_mms(phone, "", [collage_url])
                    logger.info(f"Sent MMS to {phone} with collage")
                    return
                else:
                    logger.warning("Collage generation failed, sending individual images")
                    # Fallback: send individual images (no text)
                    send_mms(phone, "", image_urls[:5])
                    logger.info(f"Sent MMS to {phone} with {len(image_urls)} individual images")
                    return

        # No items matched or extracted - send text only
        logger.warning("No items matched, sending text-only response")
        send_sms(phone, response[:1500])
        logger.info(f"Sent SMS to {phone} (no images)")

    except Exception as e:
        logger.error(f"Error processing outfit request: {e}", exc_info=True)
        send_sms(phone, "Sorry, I had trouble creating your outfit. Please try again!")


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
    send_sms(From, "Working on your outfit... (about 30 seconds)")

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
