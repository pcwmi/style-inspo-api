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
        conversation_context: Optional[dict] = None  # Stateful conversation context
    ):
        self.user_id = user_id
        self.provider = provider
        self.max_turns = 10
        self.output = output  # Injected output handler (modality-aware)
        self.conversation_context = conversation_context  # For stateful SMS

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

    def _build_context_prefix(self) -> str:
        """Build context from conversation history.

        The conversation IS the state. No parallel session state needed —
        the agent reads what was said, what photos were attached, and
        reasons from there.
        """
        if not self.conversation_context:
            return ""

        sections = []

        # --- RECENT CONVERSATION ---
        messages = self.conversation_context.get("messages", [])
        if messages:
            conv_lines = []
            # Full recent history (not truncated) - model reasons better with complete context
            for msg in messages[-10:]:  # Last 10 messages
                role = "User" if msg.get("role") == "user" else "You"
                content = msg.get("content", "")
                # Mark messages that had photos so agent knows which turn the photo came from
                photo_marker = ""
                if msg.get("image_urls"):
                    photo_marker = " [📷 photo included as image below]"
                conv_lines.append(f"{role}: {content}{photo_marker}")

            if conv_lines:
                sections.append("[RECENT CONVERSATION]\n" + "\n".join(conv_lines))

        # --- USER PREFERENCES ---
        # Note: In future, this will come from synthesized preferences (periodic LLM job).
        # For now, we'll pull from profile when it's passed in context.
        preferences = self.conversation_context.get("synthesized_preferences", {})
        if preferences:
            pref_lines = []
            if preferences.get("style_words"):
                pref_lines.append(f"Style words: {', '.join(preferences['style_words'])}")
            if preferences.get("likes"):
                pref_lines.append(f"Tends to like: {', '.join(preferences['likes'])}")
            if preferences.get("avoids"):
                pref_lines.append(f"Tends to avoid: {', '.join(preferences['avoids'])}")
            if preferences.get("style_dna"):
                pref_lines.append(f"Style DNA: {preferences['style_dna']}")

            if pref_lines:
                sections.append("[USER PREFERENCES]\n" + "\n".join(pref_lines))

        if sections:
            return "\n\n".join(sections) + "\n\n---\n\n"
        return ""

    def run(self, user_message: str, image_urls: list[str] = None, historical_image_urls: list[str] = None) -> str:
        """Run the agent loop until completion.

        Args:
            user_message: Current turn's text message
            image_urls: Current turn's images (base64 data URIs from Twilio)
            historical_image_urls: Photos from prior turns (S3 URLs) so agent can "look back"
        """
        # Prepend conversation context for stateful SMS
        context_prefix = self._build_context_prefix()
        if context_prefix:
            user_message = context_prefix + user_message
            logger.info(f"Added conversation context ({len(context_prefix)} chars)")

        # Merge historical + current images so agent sees full visual context
        all_images = []
        if historical_image_urls:
            all_images.extend(historical_image_urls)
            logger.info(f"Including {len(historical_image_urls)} historical photo(s) from prior turns")
        if image_urls:
            all_images.extend(image_urls)

        if self.provider == "anthropic":
            return self._run_anthropic(user_message, image_urls=all_images or None)
        else:
            return self._run_openai(user_message, image_urls=all_images or None)

    def _run_anthropic(self, user_message: str, image_urls: list[str] = None) -> str:
        """Anthropic/Claude agent loop."""
        # Build user message content (text + optional images)
        if image_urls:
            # Claude vision format
            user_content = [{"type": "text", "text": user_message}]
            for url in image_urls:
                user_content.append({
                    "type": "image",
                    "source": {"type": "url", "url": url}
                })
            logger.info(f"Including {len(image_urls)} image(s) in user message")
        else:
            user_content = user_message

        messages = [{"role": "user", "content": user_content}]

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

            # Log agent's text and tool calls with reasoning
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    logger.info(f"Agent text: {block.text[:300]}...")
                if block.type == "tool_use":
                    args = dict(block.input)
                    reasoning = args.pop("reasoning", None)
                    if reasoning:
                        logger.info(f"Reasoning: {reasoning}")
                    logger.info(f"Tool call: {block.name}({json.dumps(args, default=str)[:200]})")

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

    def _run_openai(self, user_message: str, image_urls: list[str] = None) -> str:
        """OpenAI agent loop."""
        # Build user message content (text + optional images)
        if image_urls:
            # Vision API format: array of content parts
            user_content = [{"type": "text", "text": user_message}]
            for url in image_urls:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            logger.info(f"Including {len(image_urls)} image(s) in user message")
        else:
            user_content = user_message

        messages = [
            {"role": "system", "content": STYLING_SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
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

            # Log agent's text response (if any)
            if choice.message.content:
                logger.info(f"Agent text: {choice.message.content[:300]}...")

            # Log each tool call with reasoning
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    args = json.loads(tc.function.arguments)
                    reasoning = args.pop("reasoning", None)
                    if reasoning:
                        logger.info(f"Reasoning: {reasoning}")
                    logger.info(f"Tool call: {tc.function.name}({json.dumps(args, default=str)[:200]})")

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
                # Filter out useless checkbox responses, keep only actionable feedback
                USELESS_CHECKBOX_RESPONSES = {
                    "the outfit doesn't make sense",
                    "not my style",
                    "won't look good on me",
                    "doesn't match my occasions",
                    "i don't like this outfit",
                    "doesn't fit my style",
                }

                manager = DislikedOutfitsManager(user_id=self.user_id)
                feedback_list = manager.get_disliked_outfits(enrich_with_current_images=False)

                actionable_feedback = []
                for f in feedback_list:
                    reason = f.get("user_reason", "").strip()
                    if not reason:
                        continue
                    if reason.lower().strip('"') in USELESS_CHECKBOX_RESPONSES:
                        continue

                    # Clean up "Other: " prefix
                    reason_clean = reason.strip('"').strip()
                    if reason_clean.lower().startswith('other:'):
                        reason = reason_clean[6:].strip()
                    else:
                        reason = reason_clean

                    outfit_data = f.get("outfit_data", {})
                    items = outfit_data.get("items", [])
                    item_names = [item.get("name", "Unknown") for item in items]

                    actionable_feedback.append({
                        "items": item_names,
                        "reason": reason,
                        "date": f.get("disliked_at", "")[:10]
                    })

                return {
                    "total_feedback": len(feedback_list),
                    "actionable_feedback": len(actionable_feedback),
                    "feedback": actionable_feedback
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

                if self.output:
                    self.output.send(text=text, images=images, layout=layout)
                    logger.info(f"send_message: sent {len(images)} images with layout={layout}")
                    return {"status": "sent", "images_count": len(images)}
                else:
                    # No output handler - just log what would be sent
                    logger.info(f"send_message (no handler): text={text[:50] if text else None}..., {len(images)} images")
                    return {"status": "no_output_handler", "would_send": {"text": text, "images": images, "layout": layout}}

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
