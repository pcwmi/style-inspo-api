"""
SMS API - Twilio webhook for incoming SMS/MMS.

Agent-native architecture:
1. User texts a request
2. We send immediate ack: "Working on it..."
3. Agent runs with SMSOutput handler
4. Agent calls resolve_items (text → images) + send_message (images → user)
5. Orchestration is just agent.run() - all logic is in agent + primitives
"""

import os
import logging
import re
from typing import Optional
from fastapi import APIRouter, Form, BackgroundTasks, Response

from services.twilio_service import send_sms

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
    Background task to process user request.

    Agent-native architecture:
    - Agent has resolve_items (text → images) and send_message (images → user) tools
    - Agent decides what to show and how (list vs outfit layout)
    - Orchestration is just: create agent with output handler, run it
    """
    try:
        logger.info(f"Processing request for {user_id}: {message}")

        # Import here to avoid circular imports
        from agent.agent import StylingAgent
        from agent.output import SMSOutput

        # Create output handler for this phone/user
        output = SMSOutput(phone=phone, user_id=user_id)

        # Create agent with output handler - agent controls what gets sent
        agent = StylingAgent(user_id=user_id, provider="openai", output=output)

        # Run agent - it will call resolve_items + send_message as needed
        response = agent.run(message)
        logger.info(f"Agent completed. Response: {response[:200] if response else '(none)'}...")

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        send_sms(phone, "Sorry, I had trouble with that. Please try again!")


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
