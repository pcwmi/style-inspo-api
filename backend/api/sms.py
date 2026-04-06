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
import json
import logging
import random
import re
import base64
import uuid
import httpx
from io import BytesIO
from typing import Optional, List
from PIL import Image
from fastapi import APIRouter, Form, BackgroundTasks, Response

from services.twilio_service import send_sms

router = APIRouter()
logger = logging.getLogger(__name__)

# Phone to user mapping (hardcoded for MVP)
PHONE_TO_USER = {
    os.getenv("PEICHIN_PHONE_NUMBER", ""): "peichin",
    os.getenv("DANA_PHONE_NUMBER", ""): "dana",
    os.getenv("KATE_PHONE_NUMBER", ""): "kate",
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


async def upload_photos_to_s3(data_uris: List[str], user_id: str) -> List[str]:
    """
    Upload base64 data URIs to S3 for persistence across conversation turns.

    Returns list of S3 URLs. Photos are stored so the agent can "look back"
    at what the user sent in previous messages.
    """
    from services.storage_manager import StorageManager

    storage = StorageManager(
        storage_type=os.getenv("STORAGE_TYPE", "local"),
        user_id=user_id
    )

    s3_urls = []
    for data_uri in data_uris:
        try:
            # Decode base64 data URI → PIL Image
            header, encoded = data_uri.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            image = Image.open(BytesIO(image_bytes))

            filename = f"sms_{uuid.uuid4().hex[:8]}.jpg"
            url = storage.save_image(image, filename, subfolder="sms_photos")
            s3_urls.append(url)
        except Exception as e:
            logger.error(f"Failed to upload photo to S3: {e}")

    return s3_urls


def preload_user_context(user_id: str) -> str:
    """Pre-fetch profile, wardrobe items, and feedback patterns.

    Delegates to agent.context.preload_user_context (canonical location).
    Kept here for backwards compatibility with any external callers.
    """
    from agent.context import preload_user_context as _preload
    return _preload(user_id)


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

        # Download Twilio media and convert to base64 (Twilio URLs require auth)
        image_data_uris = None
        s3_photo_urls = None
        if image_urls:
            logger.info(f"Downloading {len(image_urls)} images from Twilio...")
            image_data_uris = await download_twilio_media(image_urls)
            logger.info(f"Downloaded {len(image_data_uris)} images as base64")

            # Upload photos to S3 for persistence across turns
            s3_photo_urls = await upload_photos_to_s3(image_data_uris, user_id)
            logger.info(f"Persisted {len(s3_photo_urls)} photos to S3")

        # Record user message WITH photo URLs (so conversation history includes photos)
        state_manager.append_message("user", message, image_urls=s3_photo_urls)

        # Build conversation context for agent
        # The conversation IS the state — agent reads messages + photos and reasons from there
        conversation_context = {
            "messages": state.messages,
        }

        # Import here to avoid circular imports
        from agent.agent import StylingAgent
        from agent.output import StatefulSMSOutput

        # Create stateful output handler that captures outfits
        output = StatefulSMSOutput(phone=phone, user_id=user_id, state_manager=state_manager)

        # Always use full agent loop for SMS — users need tool access
        # (web search for weather, add-to-wardrobe, considering items, etc.)
        # even on their first message in a conversation.

        # Pre-load user context
        preloaded = preload_user_context(user_id)
        logger.info(f"Preloaded context: {len(preloaded)} chars")

        # Create agent with output handler and conversation context
        agent = StylingAgent(
            user_id=user_id,
            provider="openai",
            output=output,
            conversation_context=conversation_context,
            preloaded_context=preloaded
        )

        logger.info(f"Using agent loop for {user_id} (images={bool(image_data_uris)}, history={len(state.messages)})")
        response = agent.run(message, image_urls=image_data_uris)
        logger.info(f"Agent completed. Response: {response[:200] if response else '(none)'}...")

        # Always send the agent's text response if it exists.
        # send_message/present_outfit deliver per-outfit content (collages + styling text).
        # The final response is the wrap-up (packing summary, WOFs, follow-up questions) —
        # complementary content, not a duplicate.
        if response:
            send_sms(phone, response)
            logger.info(f"Sent agent text response to {phone}")

        # Always record agent response in conversation state
        if response:
            state_manager.append_message("assistant", response)

        # Persist agent conversation log for eval/replay
        try:
            from services.agent_logger import log_agent_turn
            log_agent_turn(
                user_id=user_id,
                channel="sms",
                user_message=message,
                image_urls=s3_photo_urls,
                agent_response=response,
                turn_log=agent.turn_log,
                model=agent.model,
                conversation_length=len(state.messages),
                token_usage={
                    "input": agent.total_input_tokens,
                    "output": agent.total_output_tokens,
                    "cached": agent.total_cached_tokens,
                },
                timing=agent.timing,
            )
        except Exception as e:
            logger.warning(f"Failed to log agent turn: {e}")

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
    <Message>Hi! I don't recognize this number. Please sign up at peichin.me first.</Message>
</Response>""",
            media_type="application/xml"
        )

    # Send immediate in-character acknowledgment
    ack_messages = [
        "Ooh, let me look at this...",
        "Hmm, I have some ideas...",
        "Give me a sec...",
        "Let me think on this...",
        "Oh I'm already seeing something...",
    ]
    send_sms(From, random.choice(ack_messages))

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
