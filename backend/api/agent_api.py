"""
Agent API - REST endpoint for agent-to-agent outfit generation.

Synchronous POST endpoint that runs the StylingAgent and returns
structured JSON with outfits, collages, and optional visualizations.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class AgentRunRequest(BaseModel):
    user_id: str
    message: str
    provider: str = "openai"
    conversation_id: Optional[str] = None


@router.post("/agent/run")
async def agent_run(request: AgentRunRequest):
    """Run the styling agent and return structured results.

    Blocks ~35-40s (agent ~20s + optional viz ~15-20s).
    Designed for agent-to-agent calls, not browser clients.
    """
    result = await run_in_threadpool(_run_agent_sync, request)
    return result


def _run_agent_sync(request: AgentRunRequest) -> dict:
    """Run agent synchronously (called via run_in_threadpool)."""
    from agent.agent import StylingAgent
    from agent.output import APIOutput
    from agent.context import preload_user_context

    user_id = request.user_id
    logger.info(f"Agent API: starting for user={user_id}, message={request.message[:100]}")

    # Build conversation context if conversation_id provided
    conversation_context = None
    state_manager = None
    if request.conversation_id:
        try:
            from services.conversation_state import ConversationStateManager
            state_manager = ConversationStateManager(request.conversation_id)
            state = state_manager.get_or_create_state(user_id)
            conversation_context = {"messages": state.messages}
            state_manager.append_message("user", request.message)
        except Exception as e:
            logger.warning(f"Agent API: failed to load conversation state: {e}")

    output = APIOutput(user_id=user_id)
    preloaded = preload_user_context(user_id)

    agent = StylingAgent(
        user_id=user_id,
        provider=request.provider,
        output=output,
        conversation_context=conversation_context,
        preloaded_context=preloaded,
    )

    response = agent.run(request.message)
    logger.info(f"Agent API: completed for user={user_id}, {len(output.outfits)} outfits")

    # Log agent turn for eval/replay
    try:
        from services.agent_logger import log_agent_turn
        conversation_length = len(conversation_context.get("messages", [])) if conversation_context else 0
        log_agent_turn(
            user_id=user_id,
            channel="api",
            user_message=request.message,
            image_urls=None,
            agent_response=response,
            turn_log=agent.turn_log,
            model=agent.model,
            conversation_length=conversation_length,
            token_usage={
                "input": agent.total_input_tokens,
                "output": agent.total_output_tokens,
                "cached": agent.total_cached_tokens,
            },
        )
    except Exception as e:
        logger.warning(f"Agent API: failed to log agent turn: {e}")

    # Save assistant response to conversation state
    if state_manager and response:
        try:
            state_manager.append_message("assistant", response)
        except Exception as e:
            logger.warning(f"Agent API: failed to save conversation state: {e}")

    return {
        "outfits": output.outfits,
        "messages": output.messages,
        "text_response": response,
        "token_usage": {
            "input": agent.total_input_tokens,
            "output": agent.total_output_tokens,
            "cached": agent.total_cached_tokens,
        },
    }
