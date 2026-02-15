"""
Agent-powered outfit generation for web via SSE.

Same agent that powers SMS, but with WebOutput that collects
structured outfit data for the frontend to render as outfit cards.
"""

import json
import logging
import queue
import threading

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/outfits/generate/agent-stream")
async def generate_outfits_agent_stream(
    user_id: str = Query(..., description="User ID"),
    mode: str = Query("occasion", description="Generation mode: 'occasion' or 'complete'"),
    occasions: str = Query(None, description="Comma-separated occasions"),
    anchor_items: str = Query(None, description="Comma-separated anchor item IDs"),
    weather_condition: str = Query(None, description="Weather condition"),
    temperature_range: str = Query(None, description="Temperature range"),
    device_id: str = Query(None, description="PostHog device ID"),
):
    """Stream agent-generated outfits via SSE.

    Uses the same StylingAgent that powers SMS, but with WebOutput
    that produces structured outfit data matching the frontend format.
    """

    async def event_generator():
        outfit_queue = queue.Queue()
        agent_done = threading.Event()
        agent_error = [None]

        def run_agent():
            try:
                from agent.agent import StylingAgent
                from agent.output import WebOutput

                web_output = WebOutput(
                    user_id=user_id,
                    outfit_queue=outfit_queue,
                )

                agent = StylingAgent(
                    user_id=user_id,
                    provider="openai",
                    output=web_output,
                )

                message = _build_agent_message(
                    mode, occasions, anchor_items,
                    weather_condition, temperature_range, user_id
                )

                logger.info(f"Agent-web starting for {user_id}: {message[:100]}")
                agent.run(message)
                logger.info(f"Agent-web completed for {user_id}, {len(web_output.outfits)} outfits produced")

            except Exception as e:
                agent_error[0] = str(e)
                logger.error(f"Agent-web error for {user_id}: {e}", exc_info=True)
            finally:
                agent_done.set()

        # Start agent in background thread
        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()

        # Yield outfits as they arrive from agent
        import asyncio
        outfit_num = 0

        while not agent_done.is_set() or not outfit_queue.empty():
            try:
                outfit = outfit_queue.get(timeout=0.5)
                outfit_num += 1

                # Validate physical plausibility
                from services.outfit_validator import validate_outfit
                is_valid, reason = validate_outfit(outfit.get("items", []))
                if not is_valid:
                    logger.warning(f"Agent-web outfit filtered: {reason}")
                    continue

                yield f"event: outfit\ndata: {json.dumps({'outfit_number': outfit_num, 'outfit': outfit})}\n\n"
                await asyncio.sleep(0)

            except queue.Empty:
                await asyncio.sleep(0.1)

        if agent_error[0]:
            yield f"event: error\ndata: {json.dumps({'error': agent_error[0]})}\n\n"
        else:
            yield f"event: complete\ndata: {json.dumps({'total': outfit_num})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _build_agent_message(
    mode: str,
    occasions: str,
    anchor_items: str,
    weather_condition: str,
    temperature_range: str,
    user_id: str,
) -> str:
    """Translate web query params into a natural-language agent message."""
    parts = []

    if mode == "occasion" and occasions:
        occasion_list = [o.strip().replace("-", " ") for o in occasions.split(",")]
        parts.append(f"Create 3 outfits for: {', '.join(occasion_list)}")
    elif mode == "complete" and anchor_items:
        # Look up anchor item names for a better prompt
        anchor_names = _lookup_anchor_names(user_id, anchor_items)
        if anchor_names:
            parts.append(f"Create 3 outfits featuring: {', '.join(anchor_names)}")
        else:
            parts.append(f"Create 3 outfits featuring these items (IDs: {anchor_items})")
    else:
        parts.append("Create 3 outfits for today")

    if weather_condition:
        parts.append(f"Weather: {weather_condition}")
    if temperature_range:
        parts.append(f"Temperature: {temperature_range}")

    return ". ".join(parts)


def _lookup_anchor_names(user_id: str, anchor_items: str) -> list:
    """Look up human-readable names for anchor item IDs."""
    try:
        from services.wardrobe_manager import WardrobeManager
        wm = WardrobeManager(user_id=user_id)
        all_items = wm.get_wardrobe_items(filter_type="all")
        id_to_name = {
            item.get("id"): item.get("styling_details", {}).get("name", "")
            for item in all_items
        }

        anchor_ids = [aid.strip() for aid in anchor_items.split(",")]
        names = [id_to_name.get(aid, aid) for aid in anchor_ids]
        return [n for n in names if n]
    except Exception:
        return []
