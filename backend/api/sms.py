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
import base64
import httpx
from typing import Optional, List
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


async def download_twilio_media(media_urls: List[str]) -> List[str]:
    """
    Download Twilio media and convert to base64 data URIs.

    Twilio media URLs require authentication, so OpenAI can't access them directly.
    We download with our credentials and convert to base64.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        logger.error("Twilio credentials not configured")
        return []

    data_uris = []
    async with httpx.AsyncClient() as client:
        for url in media_urls:
            try:
                # Download with Twilio auth
                response = await client.get(
                    url,
                    auth=(account_sid, auth_token),
                    follow_redirects=True,
                    timeout=30.0
                )
                response.raise_for_status()

                # Get content type and convert to base64
                content_type = response.headers.get("content-type", "image/jpeg")
                base64_data = base64.b64encode(response.content).decode("utf-8")
                data_uri = f"data:{content_type};base64,{base64_data}"

                data_uris.append(data_uri)
                logger.info(f"Downloaded media: {len(response.content)} bytes, type={content_type}")

            except Exception as e:
                logger.error(f"Failed to download media {url}: {e}")

    return data_uris


async def process_outfit_request(user_id: str, phone: str, message: str, image_urls: list[str] = None):
    """
    Background task to process user request.

    Agent-native architecture:
    - Agent has resolve_items (text → images) and send_message (images → user) tools
    - Agent decides what to show and how (list vs outfit layout)
    - Orchestration is just: create agent with output handler, run it

    Stateful conversation:
    - Load conversation state from Redis
    - Pass context to agent for multi-turn flows
    - Save state (including last outfit) after agent response
    """
    try:
        logger.info(f"Processing request for {user_id}: {message}")

        # Load or create conversation state
        from services.conversation_state import ConversationStateManager
        state_manager = ConversationStateManager(phone)
        state = state_manager.get_or_create_state(user_id)
        logger.info(f"Loaded conversation state for {phone}: {len(state.messages)} prior messages")

        # Record user message
        state_manager.append_message("user", message)

        # Build conversation context for agent
        conversation_context = {
            "last_outfit": state.last_outfit,
            "messages": state.messages
        }

        # Download Twilio media and convert to base64 (Twilio URLs require auth)
        image_data_uris = None
        if image_urls:
            logger.info(f"Downloading {len(image_urls)} images from Twilio...")
            image_data_uris = await download_twilio_media(image_urls)
            logger.info(f"Downloaded {len(image_data_uris)} images as base64")

        # Import here to avoid circular imports
        from agent.agent import StylingAgent
        from agent.output import StatefulSMSOutput

        # Create stateful output handler that captures outfits
        output = StatefulSMSOutput(phone=phone, user_id=user_id, state_manager=state_manager)

        # Create agent with output handler and conversation context
        agent = StylingAgent(
            user_id=user_id,
            provider="openai",
            output=output,
            conversation_context=conversation_context
        )

        # Run agent - it will call resolve_items + send_message as needed
        response = agent.run(message, image_urls=image_data_uris)
        logger.info(f"Agent completed. Response: {response[:200] if response else '(none)'}...")

        # Record assistant response
        if response:
            state_manager.append_message("assistant", response)

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        send_sms(phone, "Sorry, I had trouble with that. Please try again!")


@router.post("/incoming")
async def incoming_sms(
    background_tasks: BackgroundTasks,
    From: str = Form(...),
    Body: str = Form(...),
    NumMedia: str = Form(default="0"),
    MediaUrl0: str = Form(default=None),
    MediaUrl1: str = Form(default=None),
    MediaUrl2: str = Form(default=None),
):
    """
    Twilio webhook for incoming SMS/MMS.

    Twilio sends:
    - From: Sender phone number
    - Body: Message text
    - NumMedia: Number of attached images
    - MediaUrl0, MediaUrl1, ...: URLs to attached images
    """
    logger.info(f"Incoming SMS from {From}: {Body[:100]}...")

    # Collect image URLs (Twilio sends MediaUrl0, MediaUrl1, etc.)
    image_urls = [url for url in [MediaUrl0, MediaUrl1, MediaUrl2] if url]
    if image_urls:
        logger.info(f"Received {len(image_urls)} image(s): {image_urls}")

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
        message=Body,
        image_urls=image_urls if image_urls else None
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
