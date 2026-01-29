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
    # Normalize phone number (remove spaces, dashes)
    normalized = re.sub(r'[\s\-\(\)]', '', phone)

    for registered_phone, user_id in PHONE_TO_USER.items():
        if registered_phone and normalized.endswith(registered_phone[-10:]):
            return user_id

    logger.warning(f"Unknown phone number: {phone}")
    return None


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

IMPORTANT: This user is texting from their phone and wants to SEE the outfit.
After suggesting an outfit:
1. Call save_outfit with the specific items from their wardrobe (use item IDs)
2. Call visualize_outfit with the returned outfit_id
3. Include the visualization URL in your response

Keep your text response SHORT (under 300 chars) since this is SMS."""

        # Run agent
        response = agent.run(sms_prompt)

        # Try to extract visualization URL from response or agent state
        # The agent should have called visualize_outfit which returns the URL
        viz_url = extract_visualization_url(response)

        if viz_url:
            # Send MMS with image
            # Truncate response for SMS
            short_response = response[:280] if len(response) > 280 else response
            send_mms(phone, short_response, [viz_url])
            logger.info(f"Sent MMS to {phone} with visualization")
        else:
            # No visualization, just send text
            send_sms(phone, response[:1500])  # SMS limit
            logger.info(f"Sent SMS to {phone} (no visualization)")

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
