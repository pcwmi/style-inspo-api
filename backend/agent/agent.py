"""
Styling Agent - Simple agentic loop.

No framework. Just ~50 lines of code that:
1. Sends user message + tools to LLM (Claude or OpenAI)
2. If tool_use, executes primitive and sends result back
3. If end_turn, returns response

The magic is in the system prompt, not the loop.
"""

import os
import json
import logging
from typing import Optional, Literal

from agent.tools import TOOLS, TOOLS_OPENAI
from agent.prompts import STYLING_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

Provider = Literal["anthropic", "openai"]


class StylingAgent:
    """Simple styling agent with tool use. Supports Claude and OpenAI."""

    def __init__(
        self,
        user_id: str,
        provider: Provider = "anthropic",
        model: Optional[str] = None
    ):
        self.user_id = user_id
        self.provider = provider
        self.max_turns = 10

        # Set default model per provider
        if model:
            self.model = model
        elif provider == "anthropic":
            self.model = "claude-sonnet-4-20250514"
        else:
            self.model = "gpt-4o"

        # Initialize client
        if provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic()
        else:
            import openai
            self.client = openai.OpenAI()

    def run(self, user_message: str) -> str:
        """Run the agent loop until completion."""
        if self.provider == "anthropic":
            return self._run_anthropic(user_message)
        else:
            return self._run_openai(user_message)

    def _run_anthropic(self, user_message: str) -> str:
        """Anthropic/Claude agent loop."""
        messages = [{"role": "user", "content": user_message}]

        for turn in range(self.max_turns):
            logger.info(f"Agent turn {turn + 1} (anthropic/{self.model})")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=STYLING_SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )

            logger.info(f"Stop reason: {response.stop_reason}")

            if response.stop_reason == "end_turn":
                return self._extract_text_anthropic(response)

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })

                messages.append({"role": "user", "content": tool_results})

        logger.warning("Max turns reached")
        return "I apologize, but I wasn't able to complete this request."

    def _run_openai(self, user_message: str) -> str:
        """OpenAI agent loop."""
        messages = [
            {"role": "system", "content": STYLING_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        for turn in range(self.max_turns):
            logger.info(f"Agent turn {turn + 1} (openai/{self.model})")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS_OPENAI,
                tool_choice="auto"
            )

            choice = response.choices[0]
            logger.info(f"Finish reason: {choice.finish_reason}")

            if choice.finish_reason == "stop":
                return choice.message.content or ""

            if choice.finish_reason == "tool_calls":
                messages.append(choice.message)

                for tool_call in choice.message.tool_calls:
                    result = self._execute_tool(
                        tool_call.function.name,
                        json.loads(tool_call.function.arguments)
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

        logger.warning("Max turns reached")
        return "I apologize, but I wasn't able to complete this request."

    def _extract_text_anthropic(self, response) -> str:
        """Extract text from Anthropic response."""
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """
        Execute a tool by calling managers directly (no HTTP to avoid deadlock).

        When the agent runs in a background task, HTTP calls to localhost would
        deadlock because the server is blocked waiting for the background task.
        """
        try:
            # Import managers locally to avoid circular imports
            from services.wardrobe_manager import WardrobeManager
            from services.user_profile_manager import UserProfileManager
            from services.feedback_manager import FeedbackManager
            from services.saved_outfits_manager import SavedOutfitsManager

            if tool_name == "get_items":
                filter_type = tool_input.get("filter_type", "all")
                manager = WardrobeManager(user_id=self.user_id)
                items = manager.get_wardrobe_items(filter_type=filter_type)
                # Return compact format for agent (less tokens)
                compact_items = [
                    {
                        "id": item["id"],
                        "name": item.get("styling_details", {}).get("name", ""),
                        "category": item.get("styling_details", {}).get("category", ""),
                        "colors": item.get("styling_details", {}).get("colors", []),
                        "style": item.get("styling_details", {}).get("style", ""),
                        "image_url": item.get("system_metadata", {}).get("image_url", ""),
                    }
                    for item in items
                ]
                return {"items": compact_items, "count": len(compact_items)}

            elif tool_name == "get_item":
                item_id = tool_input["item_id"]
                manager = WardrobeManager(user_id=self.user_id)
                items = manager.get_wardrobe_items(filter_type="all")
                for item in items:
                    if item.get("id") == item_id:
                        return {"item": item}
                return {"error": f"Item {item_id} not found"}

            elif tool_name == "get_profile":
                manager = UserProfileManager(user_id=self.user_id)
                return manager.get_profile()

            elif tool_name == "get_feedback":
                manager = FeedbackManager(user_id=self.user_id)
                return {"feedback": manager.get_all_feedback()}

            elif tool_name == "get_feedback_patterns":
                manager = FeedbackManager(user_id=self.user_id)
                return manager.get_feedback_patterns()

            elif tool_name == "get_saved_outfits":
                manager = SavedOutfitsManager(user_id=self.user_id)
                outfits = manager.get_saved_outfits()
                return {"outfits": outfits, "count": len(outfits)}

            elif tool_name == "get_not_worn_outfits":
                manager = SavedOutfitsManager(user_id=self.user_id)
                limit = tool_input.get("limit")
                outfits = manager.get_not_worn_outfits(limit=limit)
                return {"outfits": outfits, "count": len(outfits)}

            elif tool_name == "get_worn_outfits":
                manager = SavedOutfitsManager(user_id=self.user_id)
                outfits = manager.get_worn_outfits()
                return {"outfits": outfits, "count": len(outfits)}

            elif tool_name == "save_outfit":
                manager = SavedOutfitsManager(user_id=self.user_id)
                outfit_data = {
                    "items": tool_input.get("items", []),
                    "styling_notes": tool_input.get("styling_notes", ""),
                    "vibe_keywords": tool_input.get("vibe_keywords", [])
                }
                outfit_id = manager.save_outfit(
                    outfit_data=outfit_data,
                    reason=tool_input.get("styling_notes", ""),
                    occasion=tool_input.get("occasion", "")
                )
                return {"outfit_id": outfit_id, "status": "saved"}

            # Tools that still need HTTP (external services)
            elif tool_name == "visualize_outfit":
                # Skip visualization for now - just return the outfit items
                # Runway visualization takes 60-90s which is too slow for SMS
                return {
                    "status": "skipped",
                    "message": "Visualization skipped for SMS (too slow). Send item images directly."
                }

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}


def run_agent(
    user_id: str,
    message: str,
    provider: Provider = "anthropic",
    model: Optional[str] = None
) -> str:
    """Convenience function to run the agent."""
    agent = StylingAgent(user_id=user_id, provider=provider, model=model)
    return agent.run(message)
