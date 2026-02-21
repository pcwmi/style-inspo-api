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
        model: Optional[str] = None,
        output: Optional[any] = None,  # OutputHandler for send_message
        conversation_context: Optional[dict] = None,  # Stateful conversation context
        preloaded_context: Optional[str] = None  # Pre-fetched profile/items/feedback
    ):
        self.user_id = user_id
        self.provider = provider
        self.max_turns = 10
        self.output = output  # Injected output handler (modality-aware)
        self.conversation_context = conversation_context  # For stateful SMS
        self.preloaded_context = preloaded_context  # Eliminates context-gathering round-trip
        self.turn_log = []  # Structured trace of this run
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cached_tokens = 0

        # Set default model per provider
        if model:
            self.model = model
        elif provider == "anthropic":
            self.model = "claude-sonnet-4-20250514"
        else:
            self.model = "gpt-5.2"  # Best reasoning for styling

        # Initialize client
        if provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic()
        else:
            import openai
            self.client = openai.OpenAI()

    def _build_conversation_messages(self) -> list[dict]:
        """Convert conversation history to OpenAI multi-turn messages.

        Each message keeps its photos attached. The API understands
        which image belongs to which turn naturally.
        """
        if not self.conversation_context:
            return []

        messages = []
        for msg in self.conversation_context.get("messages", [])[-10:]:
            role = msg["role"]  # "user" or "assistant"
            content = msg.get("content", "")
            image_urls = msg.get("image_urls", [])

            if role == "user" and image_urls:
                # User message with photos → content array
                content_parts = [{"type": "text", "text": content}]
                for url in image_urls:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": url}
                    })
                messages.append({"role": "user", "content": content_parts})
            else:
                # Text-only message
                messages.append({"role": role, "content": content})

        return messages

    def _build_conversation_messages_anthropic(self) -> list[dict]:
        """Convert conversation history to Anthropic multi-turn messages."""
        if not self.conversation_context:
            return []

        messages = []
        for msg in self.conversation_context.get("messages", [])[-10:]:
            role = msg["role"]
            content = msg.get("content", "")
            image_urls = msg.get("image_urls", [])

            if role == "user" and image_urls:
                content_parts = [{"type": "text", "text": content}]
                for url in image_urls:
                    content_parts.append({
                        "type": "image",
                        "source": {"type": "url", "url": url}
                    })
                messages.append({"role": "user", "content": content_parts})
            else:
                messages.append({"role": role, "content": content})

        return messages

    def run(self, user_message: str, image_urls: list[str] = None) -> str:
        """Run the agent loop until completion.

        Args:
            user_message: Current turn's text message
            image_urls: Current turn's images (base64 data URIs from Twilio)
        """
        if self.provider == "anthropic":
            return self._run_anthropic(user_message, image_urls=image_urls)
        else:
            return self._run_openai(user_message, image_urls=image_urls)

    def _run_anthropic(self, user_message: str, image_urls: list[str] = None) -> str:
        """Anthropic/Claude agent loop."""
        # Start with conversation history (each message with its own photos)
        messages = self._build_conversation_messages_anthropic()
        history_count = len(messages)

        # Add current turn
        if image_urls:
            user_content = [{"type": "text", "text": user_message}]
            for url in image_urls:
                user_content.append({
                    "type": "image",
                    "source": {"type": "url", "url": url}
                })
            logger.info(f"Including {len(image_urls)} image(s) in current message")
        else:
            user_content = user_message

        messages.append({"role": "user", "content": user_content})
        logger.info(f"Sending {len(messages)} messages ({history_count} history + current)")

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

            # Extract text and tool calls for logging
            response_text = ""
            tool_calls_log = []
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    response_text = block.text
                    logger.info(f"Agent text: {block.text[:300]}...")
                if block.type == "tool_use":
                    args = dict(block.input)
                    reasoning = args.pop("reasoning", None)
                    if reasoning:
                        logger.info(f"Reasoning: {reasoning}")
                    logger.info(f"Tool call: {block.name}({json.dumps(args, default=str)[:200]})")
                    tool_calls_log.append({"tool": block.name, "args": args})

            # Log LLM response to turn trace
            self.turn_log.append({
                "type": "llm_response",
                "turn": turn + 1,
                "text": response_text,
                "tool_calls": tool_calls_log,
                "finish_reason": response.stop_reason,
            })

            if response.stop_reason == "end_turn":
                return self._extract_text_anthropic(response)

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._execute_tool(block.name, block.input)
                        # Log tool result to turn trace
                        self.turn_log.append({
                            "type": "tool_result",
                            "tool": block.name,
                            "args": {k: v for k, v in block.input.items() if k != "reasoning"},
                            "result_keys": list(result.keys()) if isinstance(result, dict) else None,
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })

                messages.append({"role": "user", "content": tool_results})

        logger.warning("Max turns reached")
        return "I apologize, but I wasn't able to complete this request."

    def _run_openai(self, user_message: str, image_urls: list[str] = None) -> str:
        """OpenAI agent loop."""
        # Start with system prompt (+ preloaded context if available)
        system_prompt = STYLING_SYSTEM_PROMPT
        if self.preloaded_context:
            system_prompt += (
                "\n\n---\n\n# User Context (pre-loaded)\n\n"
                "The user's profile, wardrobe, and feedback are provided below. "
                "Do NOT call get_profile, get_items, or get_feedback_patterns — this data is already here. "
                "Go straight to reasoning about outfits and calling resolve_items + send_message.\n\n"
                + self.preloaded_context
            )
            logger.info("Injected preloaded context into system prompt")
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (each message with its own photos)
        history = self._build_conversation_messages()
        messages.extend(history)

        # Add current turn
        if image_urls:
            user_content = [{"type": "text", "text": user_message}]
            for url in image_urls:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            logger.info(f"Including {len(image_urls)} image(s) in current message")
        else:
            user_content = user_message

        messages.append({"role": "user", "content": user_content})
        logger.info(f"Sending {len(messages)} messages ({len(history)} history + current)")

        for turn in range(self.max_turns):
            logger.info(f"Agent turn {turn + 1} (openai/{self.model})")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS_OPENAI,
                tool_choice="auto"
            )

            # Log token usage including cache status
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                cached = getattr(usage, 'prompt_tokens_details', None)
                cached_tokens = cached.cached_tokens if cached and hasattr(cached, 'cached_tokens') else 0
                self.total_input_tokens += usage.prompt_tokens
                self.total_output_tokens += usage.completion_tokens
                self.total_cached_tokens += cached_tokens
                logger.info(
                    f"Tokens: {usage.prompt_tokens} input ({cached_tokens} cached), "
                    f"{usage.completion_tokens} output"
                )

            choice = response.choices[0]
            logger.info(f"Finish reason: {choice.finish_reason}")

            # Log agent's text response (if any)
            response_text = choice.message.content or ""
            if response_text:
                logger.info(f"Agent text: {response_text[:300]}...")

            # Log each tool call with reasoning
            tool_calls_log = []
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    args = json.loads(tc.function.arguments)
                    reasoning = args.pop("reasoning", None)
                    if reasoning:
                        logger.info(f"Reasoning: {reasoning}")
                    logger.info(f"Tool call: {tc.function.name}({json.dumps(args, default=str)[:200]})")
                    tool_calls_log.append({"tool": tc.function.name, "args": args})

            # Log LLM response to turn trace
            self.turn_log.append({
                "type": "llm_response",
                "turn": turn + 1,
                "text": response_text,
                "tool_calls": tool_calls_log,
                "finish_reason": choice.finish_reason,
            })

            if choice.finish_reason == "stop":
                logger.info(
                    f"Agent complete: {turn + 1} turns, "
                    f"{self.total_input_tokens} total input ({self.total_cached_tokens} cached), "
                    f"{self.total_output_tokens} total output"
                )
                return response_text

            if choice.finish_reason == "tool_calls":
                messages.append(choice.message)

                for tool_call in choice.message.tool_calls:
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_args_clean = {k: v for k, v in tool_args.items() if k != "reasoning"}
                    result = self._execute_tool(
                        tool_call.function.name,
                        tool_args
                    )
                    # Log tool result to turn trace
                    self.turn_log.append({
                        "type": "tool_result",
                        "tool": tool_call.function.name,
                        "args": tool_args_clean,
                        "result_keys": list(result.keys()) if isinstance(result, dict) else None,
                    })
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
        # Capture reasoning for WebOutput (if it supports it)
        reasoning = tool_input.get("reasoning")
        if reasoning and self.output and hasattr(self.output, 'capture_reasoning'):
            self.output.capture_reasoning(tool_name, reasoning)

        try:
            # Import managers locally to avoid circular imports
            from services.wardrobe_manager import WardrobeManager
            from services.user_profile_manager import UserProfileManager
            from services.disliked_outfits_manager import DislikedOutfitsManager
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
                profile = manager.get_profile(self.user_id)
                return {"profile": profile}

            elif tool_name == "get_feedback":
                manager = DislikedOutfitsManager(user_id=self.user_id)
                feedback = manager.get_disliked_outfits(enrich_with_current_images=True)
                return {"feedback": feedback, "count": len(feedback)}

            elif tool_name == "get_feedback_patterns":
                # Positive + negative feedback patterns
                USELESS_CHECKBOX_RESPONSES = {
                    "the outfit doesn't make sense",
                    "not my style",
                    "won't look good on me",
                    "doesn't match my occasions",
                    "i don't like this outfit",
                    "doesn't fit my style",
                }

                feedback = []

                # Negative (dislikes) — filter out generic checkbox
                dislike_mgr = DislikedOutfitsManager(user_id=self.user_id)
                disliked_list = dislike_mgr.get_disliked_outfits(enrich_with_current_images=False)
                actionable_negative = 0

                for f in disliked_list:
                    reason = f.get("user_reason", "").strip()
                    if not reason:
                        continue
                    if reason.lower().strip('"') in USELESS_CHECKBOX_RESPONSES:
                        continue
                    reason_clean = reason.strip('"').strip()
                    if reason_clean.lower().startswith('other:'):
                        reason = reason_clean[6:].strip()
                    else:
                        reason = reason_clean

                    items = f.get("outfit_data", {}).get("items", [])
                    feedback.append({
                        "items": [i.get("name", "Unknown") for i in items],
                        "reason": reason.strip('"'),
                        "date": f.get("disliked_at", "")[:10],
                        "type": "negative",
                    })
                    actionable_negative += 1

                # Positive (saves) — include all with reasons
                from services.saved_outfits_manager import SavedOutfitsManager
                save_mgr = SavedOutfitsManager(user_id=self.user_id)
                saved_list = save_mgr.get_saved_outfits(enrich_with_current_images=False)

                for s in saved_list:
                    reason = s.get("user_reason", "").strip()
                    if not reason:
                        continue
                    items = s.get("outfit_data", {}).get("items", [])
                    feedback.append({
                        "items": [i.get("name", "Unknown") for i in items],
                        "reason": reason,
                        "date": s.get("saved_at", "")[:10],
                        "type": "positive",
                        "worn": bool(s.get("worn_at")),
                    })

                return {
                    "total_disliked": len(disliked_list),
                    "total_saved": len(saved_list),
                    "actionable_negative": actionable_negative,
                    "feedback": feedback,
                }

            elif tool_name == "save_feedback":
                manager = DislikedOutfitsManager(user_id=self.user_id)
                items = tool_input.get("items", [])
                feedback_type = tool_input.get("feedback_type", "negative")
                reason = tool_input.get("reason", "")
                style_lesson = tool_input.get("style_lesson", "")

                # Create outfit combo object
                class OutfitCombo:
                    def __init__(self, items):
                        self.items = items
                        self.styling_notes = ""
                        self.why_it_works = ""
                        self.confidence_level = ""
                        self.vibe_keywords = []

                outfit_combo = OutfitCombo(items=items)

                # Include style_lesson in the reason for richer context
                full_reason = f"{reason}"
                if style_lesson:
                    full_reason += f" [Style lesson: {style_lesson}]"

                # Save feedback (currently only negative/dislike is supported by manager)
                if feedback_type == "negative":
                    success = manager.dislike_outfit(
                        outfit_combo=outfit_combo,
                        reason=full_reason,
                        context={"feedback_type": feedback_type, "style_lesson": style_lesson}
                    )
                    logger.info(f"save_feedback: saved negative feedback for {len(items)} items")
                    return {"saved": success, "feedback_type": "negative", "items_count": len(items)}
                else:
                    # For positive feedback, we don't have a manager yet - log it
                    logger.info(f"save_feedback: positive feedback noted (not persisted yet): {reason}")
                    return {"saved": False, "feedback_type": "positive", "note": "Positive feedback logging not yet implemented"}

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

                # Debug: log what we received
                items = tool_input.get("items", [])
                logger.info(f"save_outfit received {len(items)} items: {items}")

                # Create outfit combo object (expected by manager)
                class OutfitCombo:
                    def __init__(self, items, styling_notes, vibe_keywords):
                        self.items = items
                        self.styling_notes = styling_notes
                        self.why_it_works = ""
                        self.confidence_level = ""
                        self.vibe_keywords = vibe_keywords

                outfit_combo = OutfitCombo(
                    items=items,
                    styling_notes=tool_input.get("styling_notes", ""),
                    vibe_keywords=tool_input.get("vibe_keywords", [])
                )

                outfit_id = manager.save_outfit(
                    outfit_combo=outfit_combo,
                    reason=tool_input.get("styling_notes", ""),
                    occasion=tool_input.get("occasion", "")
                )
                logger.info(f"save_outfit saved with ID: {outfit_id}")

                # Link SMS visualization if available in conversation state
                if hasattr(self.output, 'state_manager'):
                    try:
                        state = self.output.state_manager.get_state()
                        viz_url = (state.last_outfit or {}).get("visualization_url") if state else None
                        if viz_url:
                            manager.update_outfit_visualization(outfit_id, viz_url)
                            logger.info(f"save_outfit: linked SMS visualization to {outfit_id}")
                    except Exception as e:
                        logger.warning(f"save_outfit: failed to link SMS viz: {e}")

                return {"outfit_id": outfit_id, "status": "saved"}

            # Tools that still need HTTP (external services)
            elif tool_name == "visualize_outfit":
                # Skip visualization for now - just return the outfit items
                # Runway visualization takes 60-90s which is too slow for SMS
                return {
                    "status": "skipped",
                    "message": "Visualization skipped for SMS (too slow). Send item images directly."
                }

            # --- RESOLVER (text → images) ---
            elif tool_name == "resolve_items":
                from primitives.matching import match_items_to_wardrobe
                from services.outfit_validator import validate_outfit
                descriptions = tool_input.get("descriptions", [])
                matched = match_items_to_wardrobe(self.user_id, descriptions)

                resolved = []
                unresolved = []
                for i, item in enumerate(matched):
                    if item.get("matched"):
                        resolved.append({
                            "description": descriptions[i],
                            "name": item["name"],
                            "category": item.get("category", "unknown"),
                            "sub_category": item.get("sub_category", ""),
                            "image_url": item.get("image_path")
                        })
                    else:
                        unresolved.append(descriptions[i])

                # Validate outfit physical plausibility
                is_valid, rejection_reason = validate_outfit(resolved)
                if not is_valid:
                    logger.warning(
                        f"resolve_items outfit filtered: {rejection_reason} | "
                        f"Items: {[r['name'] for r in resolved]}"
                    )
                    try:
                        from services.activity_logger import log_activity
                        log_activity(self.user_id, "outfit_filtered", {
                            "reason": rejection_reason,
                            "channel": "sms",
                            "items": [{"name": r["name"], "category": r.get("category"), "sub_category": r.get("sub_category")} for r in resolved],
                        })
                    except Exception:
                        pass
                    return {
                        "resolved": resolved,
                        "unresolved": unresolved,
                        "validation_error": rejection_reason,
                        "suggestion": f"This outfit has a physical conflict: {rejection_reason}. Please try a different combination of items."
                    }

                logger.info(f"resolve_items: {len(resolved)} resolved, {len(unresolved)} unresolved")
                return {"resolved": resolved, "unresolved": unresolved}

            # --- OUTPUT (send to user) ---
            elif tool_name == "send_message":
                text = tool_input.get("text")
                images = tool_input.get("images", [])
                layout = tool_input.get("layout", "list")
                visualize = tool_input.get("visualize", False)

                if self.output:
                    self.output.send(text=text, images=images, layout=layout, visualize=visualize)
                    logger.info(f"send_message: sent {len(images)} images with layout={layout}, visualize={visualize}")
                    return {"status": "sent", "images_count": len(images), "visualize": visualize}
                else:
                    # No output handler - just log what would be sent
                    logger.info(f"send_message (no handler): text={text[:50] if text else None}..., {len(images)} images")
                    return {"status": "no_output_handler", "would_send": {"text": text, "images": images, "layout": layout, "visualize": visualize}}

            # --- WEB BROWSING ---
            elif tool_name == "browse_url":
                from services.web_browsing import browse_url
                result = browse_url(tool_input["url"])
                return result

            # --- CONSIDERING (SHOPPING) ---
            elif tool_name == "add_considering_item":
                import requests
                from io import BytesIO
                from services.consider_buying_manager import ConsiderBuyingManager

                name = tool_input.get("name", "Unnamed")
                image_url = tool_input.get("image_url")
                category = tool_input.get("category", "tops")
                price = tool_input.get("price")
                source_url = tool_input.get("source_url")

                # Download image from URL
                try:
                    headers = {"User-Agent": "StyleInspo/1.0"}
                    resp = requests.get(image_url, timeout=15, headers=headers)
                    resp.raise_for_status()
                    image_file = BytesIO(resp.content)
                except Exception as e:
                    return {"error": f"Failed to download image: {e}"}

                # Build analysis_data (skip LLM analysis — agent already knows the details)
                analysis_data = {
                    "name": name,
                    "category": category,
                    "sub_category": f"{category}_general",
                    "colors": [],
                    "style": "casual",
                    "brand": "",
                }

                manager = ConsiderBuyingManager(user_id=self.user_id)
                item = manager.add_item(
                    analysis_data=analysis_data,
                    image=image_file,
                    price=price,
                    source_url=source_url,
                )

                logger.info(f"add_considering_item: saved '{name}' as {item.get('id')}")
                return {
                    "success": True,
                    "item_id": item.get("id"),
                    "name": item.get("styling_details", {}).get("name"),
                    "message": f"Saved '{name}' to considering items. You can now include it in resolve_items."
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
