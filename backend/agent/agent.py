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
import random
import time
from typing import Optional, Literal

from agent.tools import TOOLS, TOOLS_OPENAI
from agent.prompts import STYLING_SYSTEM_PROMPT, FAST_OUTFIT_PROMPT, get_system_prompt
from agent.edit_intent import build_constrained_edit_hint

logger = logging.getLogger(__name__)

Provider = Literal["anthropic", "openai"]


def get_compact_items(items: list, include_image_url: bool = True) -> list:
    """Build compact item list for agent consumption, shuffled to prevent positional bias.

    Single source of truth for item formatting — used by both _execute_tool
    and preload_user_context so all channels get identical behavior.

    Includes cut/fit/texture/sub_category so the agent can reason about
    silhouette, proportions, and layering (garment physics).
    """
    compact = []
    for item in items:
        sd = item.get("styling_details", {})
        entry = {
            "id": item["id"],
            "name": sd.get("name", ""),
            "category": sd.get("category", ""),
            "colors": sd.get("colors", []),
            "style": sd.get("style", ""),
        }
        # Garment physics fields — only include if present
        for field in ("cut", "fit", "texture", "sub_category"):
            val = sd.get(field, "")
            if val:
                entry[field] = val
        if include_image_url:
            entry["image_url"] = item.get("system_metadata", {}).get("image_url", "")
        compact.append(entry)
    random.shuffle(compact)
    return compact


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
        self.max_turns = 15
        self.output = output  # Injected output handler (modality-aware)
        self.conversation_context = conversation_context  # For stateful SMS
        self.preloaded_context = preloaded_context  # Eliminates context-gathering round-trip
        self.turn_log = []  # Structured trace of this run
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cached_tokens = 0
        self.timing = {"llm_calls": [], "tool_calls": []}  # Per-step latency tracking

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

    def _build_state_context(self, user_message: str) -> str:
        """Build structured SMS state context outside the prose transcript."""
        if not self.conversation_context:
            return ""

        sections = []
        active_pack = self.conversation_context.get("active_pack") or {}
        outfits = active_pack.get("outfits") or []
        if outfits:
            lines = [
                "# Active Pack State",
                "Use this as the source of truth for packing follow-ups and edits.",
            ]
            for outfit in outfits:
                label = outfit.get("label") or "Outfit"
                item_names = outfit.get("item_names") or [
                    item.get("name") for item in outfit.get("items", []) if item.get("name")
                ]
                if item_names:
                    lines.append(f"- {label}: {', '.join(item_names)}")
            sections.append("\n".join(lines))

        last_outfit = self.conversation_context.get("last_outfit") or {}
        last_item_names = last_outfit.get("item_names") or [
            item.get("name") for item in last_outfit.get("items", []) if item.get("name")
        ]
        if last_item_names and not outfits:
            sections.append("# Last Outfit State\n- " + ", ".join(last_item_names))

        edit_hint = build_constrained_edit_hint(user_message, active_pack)
        if edit_hint:
            sections.append("# Edit Scope\n" + edit_hint)

        if not sections:
            return ""
        return "\n\n---\n\n" + "\n\n".join(sections)

    def _build_context_prefix(self) -> str:
        """Backward-compatible text context summary for older tests/callers."""
        if not self.conversation_context:
            return ""

        lines = ["[CONTEXT]"]
        last_outfit = self.conversation_context.get("last_outfit") or {}
        if last_outfit:
            item_names = [
                item.get("name") for item in last_outfit.get("items", []) if item.get("name")
            ]
            if item_names:
                lines.append("Last outfit: " + ", ".join(item_names))
            elif last_outfit.get("image_urls"):
                lines.append(f"Last outfit: {len(last_outfit['image_urls'])} items")

            notes = last_outfit.get("styling_notes")
            if notes:
                lines.append("Styling notes: " + notes)

        for msg in self.conversation_context.get("messages", [])[-5:]:
            role = msg.get("role", "message")
            content = msg.get("content", "")
            if content:
                lines.append(f"{role}: {content}")

        return "\n".join(lines) if len(lines) > 1 else ""

    def run(self, user_message: str, image_urls: list[str] = None) -> str:
        """Run the agent loop until completion.

        Args:
            user_message: Current turn's text message
            image_urls: Current turn's images (base64 data URIs from Twilio)
        """
        self.timing["run_start"] = time.perf_counter()
        if self.provider == "anthropic":
            result = self._run_anthropic(user_message, image_urls=image_urls)
        else:
            result = self._run_openai(user_message, image_urls=image_urls)
        self.timing["total_ms"] = int((time.perf_counter() - self.timing["run_start"]) * 1000)
        logger.info(f"Agent timing: {self.timing['total_ms']}ms total, "
                     f"{len(self.timing['llm_calls'])} LLM calls, "
                     f"{len(self.timing['tool_calls'])} tool calls")
        return result

    def fast_generate(self, user_message: str) -> str:
        """Single-call outfit generation with structured JSON output.

        Makes 1 LLM call instead of 3, then handles resolve + collage + send
        deterministically. Falls back to full agent loop on failure.

        Returns the styling text from the generated outfit(s).
        """
        self.timing["run_start"] = time.perf_counter()
        self.timing["mode"] = "fast"

        # Build system prompt — use the FULL styling prompt (same quality as agent loop)
        # plus a JSON output instruction appended at the end
        json_instruction = """

---

# Output Format (CRITICAL)

You MUST respond with valid JSON. For each outfit requested, return:

{"outfits": [{"items": ["Exact Item Name 1", "Exact Item Name 2", ...], "styling_text": "Your styling advice — same warmth and personality as a text to a friend. Include the why.", "occasion": "what this outfit is for"}]}

Use EXACT item names from the wardrobe list. Include 3-6 items per outfit (top + bottom + shoes minimum, plus layers/accessories).
"""
        system_prompt = get_system_prompt() + json_instruction
        if self.preloaded_context:
            system_prompt += "\n\n# User Context\n\n" + self.preloaded_context

        # Single LLM call with structured JSON output
        llm_start = time.perf_counter()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
            )
        except Exception as e:
            logger.warning(f"Fast path LLM call failed: {e}, falling back to agent loop")
            self.timing["mode"] = "fast→agent_fallback"
            return self.run(user_message)

        llm_ms = int((time.perf_counter() - llm_start) * 1000)
        self.timing["llm_calls"].append({"turn": 1, "model": self.model, "ms": llm_ms})

        # Track tokens
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            cached = getattr(usage, 'prompt_tokens_details', None)
            cached_tokens = cached.cached_tokens if cached and hasattr(cached, 'cached_tokens') else 0
            self.total_input_tokens += usage.prompt_tokens
            self.total_output_tokens += usage.completion_tokens
            self.total_cached_tokens += cached_tokens
            logger.info(f"Fast path LLM: {llm_ms}ms, {usage.prompt_tokens} in ({cached_tokens} cached), {usage.completion_tokens} out")

        # Parse structured output
        raw = response.choices[0].message.content or ""
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Fast path JSON parse failed, falling back to agent loop")
            self.timing["mode"] = "fast→agent_fallback"
            return self.run(user_message)

        outfits = result.get("outfits", [])
        if not outfits:
            logger.warning("Fast path returned no outfits, falling back to agent loop")
            self.timing["mode"] = "fast→agent_fallback"
            return self.run(user_message)

        # Log the structured output to turn trace
        self.turn_log.append({
            "type": "fast_path_output",
            "outfit_count": len(outfits),
            "items_per_outfit": [len(o.get("items", [])) for o in outfits],
        })

        # Deterministic pipeline: resolve all → validate → collage (parallel) → send
        from primitives.matching import match_items_to_wardrobe
        from services.outfit_validator import validate_outfit

        # Phase 1: Resolve and validate all outfits (fast, sequential)
        resolve_start = time.perf_counter()
        valid_outfits = []  # [(styling_text, image_urls, resolved_items)]
        for i, outfit in enumerate(outfits):
            item_names = outfit.get("items", [])
            styling_text = outfit.get("styling_text", "")
            if not item_names:
                continue

            matched = match_items_to_wardrobe(self.user_id, item_names)
            resolved = [m for m in matched if m.get("matched")]
            image_urls = [m["image_path"] for m in resolved if m.get("image_path")]

            if len(resolved) < 2:
                logger.warning(f"Fast path outfit {i+1}: only {len(resolved)}/{len(item_names)} resolved, skipping")
                continue

            is_valid, rejection = validate_outfit(resolved)
            if not is_valid:
                logger.warning(f"Fast path outfit {i+1} filtered: {rejection}")
                continue

            valid_outfits.append((styling_text, image_urls, resolved))

        resolve_ms = int((time.perf_counter() - resolve_start) * 1000)
        self.timing["tool_calls"].append({"tool": "resolve_all", "ms": resolve_ms})

        if not valid_outfits:
            logger.warning("Fast path: all outfits failed validation, falling back to agent loop")
            self.timing["mode"] = "fast→agent_fallback"
            return self.run(user_message)

        # Phase 2: Generate collages + send (parallel for multiple outfits)
        from concurrent.futures import ThreadPoolExecutor

        send_start = time.perf_counter()

        def _present_one(args):
            styling_text, image_urls, resolved_items = args
            if self.output:
                item_names = [
                    item.get("styling_details", {}).get("name") or item.get("name", "")
                    for item in resolved_items
                ]
                self.output.present_outfit(
                    text=styling_text,
                    images=image_urls,
                    visualize=True,
                    skip_enhance=True,
                    item_names=item_names,
                )
            return styling_text

        if len(valid_outfits) == 1:
            all_styling_texts = [_present_one(valid_outfits[0])]
        else:
            with ThreadPoolExecutor(max_workers=len(valid_outfits)) as pool:
                all_styling_texts = list(pool.map(_present_one, valid_outfits))

        send_ms = int((time.perf_counter() - send_start) * 1000)
        self.timing["tool_calls"].append({"tool": "present_outfits_parallel", "ms": send_ms, "count": len(valid_outfits)})

        self.timing["total_ms"] = int((time.perf_counter() - self.timing["run_start"]) * 1000)
        logger.info(f"Fast path complete: {len(valid_outfits)} outfits in {self.timing['total_ms']}ms "
                     f"(LLM: {llm_ms}ms, collages: {send_ms}ms, {len(self.timing['llm_calls'])} calls)")

        return "\n\n".join(all_styling_texts)

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

            system_prompt = get_system_prompt() + self._build_state_context(user_message)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
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
        system_prompt = get_system_prompt() + self._build_state_context(user_message)
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

            llm_start = time.perf_counter()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS_OPENAI,
                tool_choice="auto"
            )
            llm_ms = int((time.perf_counter() - llm_start) * 1000)
            self.timing["llm_calls"].append({"turn": turn + 1, "model": self.model, "ms": llm_ms})
            logger.info(f"LLM call {turn + 1}: {llm_ms}ms")

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
                    tool_start = time.perf_counter()
                    result = self._execute_tool(
                        tool_call.function.name,
                        tool_args
                    )
                    tool_ms = int((time.perf_counter() - tool_start) * 1000)
                    self.timing["tool_calls"].append({"tool": tool_call.function.name, "ms": tool_ms})
                    logger.info(f"Tool {tool_call.function.name}: {tool_ms}ms")
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
                compact_items = get_compact_items(items)
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

                # Silent feedback (generated but not saved/disliked)
                silent_patterns = None
                try:
                    from services.storage_manager import StorageManager
                    storage = StorageManager(storage_type="s3", user_id=self.user_id)
                    data = storage.load_json("silent_feedback_patterns.json")
                    entries = data.get("entries", [])
                    if entries:
                        total_gen = sum(e.get("generated", 0) for e in entries)
                        total_sav = sum(e.get("saved", 0) for e in entries)
                        rate = round(total_sav / total_gen * 100) if total_gen > 0 else 0
                        recent_pattern = ""
                        for e in reversed(entries):
                            if e.get("pattern"):
                                recent_pattern = e["pattern"]
                                break
                        silent_patterns = {
                            "overall_save_rate": f"{rate}% ({total_sav} saved of {total_gen} generated, last {len(entries)} days)",
                            "recent_pattern": recent_pattern,
                            "last_updated": entries[-1].get("date", ""),
                        }
                except Exception:
                    pass

                result = {
                    "total_disliked": len(disliked_list),
                    "total_saved": len(saved_list),
                    "actionable_negative": actionable_negative,
                    "feedback": feedback,
                }
                if silent_patterns:
                    result["silent_patterns"] = silent_patterns
                return result

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

            elif tool_name == "mark_worn":
                manager = SavedOutfitsManager(user_id=self.user_id)
                outfit_id = tool_input.get("outfit_id")
                result = manager.mark_outfit_worn(outfit_id)
                if result:
                    logger.info(f"mark_worn: marked outfit {outfit_id} as worn")
                    return {"success": True, "outfit_id": outfit_id, "worn_at": result.get("worn_at")}
                else:
                    return {"error": f"Outfit {outfit_id} not found"}

            elif tool_name == "delete_outfit":
                manager = SavedOutfitsManager(user_id=self.user_id)
                outfit_id = tool_input.get("outfit_id")
                deleted = manager.delete_outfit(outfit_id)
                if deleted:
                    logger.info(f"delete_outfit: deleted outfit {outfit_id}")
                    return {"success": True, "outfit_id": outfit_id}
                else:
                    return {"error": f"Outfit {outfit_id} not found"}

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
            elif tool_name == "present_outfit":
                text = tool_input.get("text")
                images = tool_input.get("images", [])
                item_names = tool_input.get("item_names", [])
                visualize = tool_input.get("visualize", False)

                if self.output:
                    self.output.present_outfit(text=text, images=images, visualize=visualize, item_names=item_names)
                    logger.info(f"present_outfit: sent {len(images)} images, item_names={item_names}, visualize={visualize}")
                    return {
                        "status": "sent",
                        "images_count": len(images),
                        "visualize": visualize,
                        "item_names": item_names,
                        "label": text,
                    }
                else:
                    logger.info(f"present_outfit (no handler): text={text[:50] if text else None}..., {len(images)} images, item_names={item_names}")
                    return {
                        "status": "no_output_handler",
                        "would_send": {"text": text, "images": images, "visualize": visualize},
                        "item_names": item_names,
                        "label": text,
                    }

            elif tool_name == "send_message":
                text = tool_input.get("text")
                images = tool_input.get("images", [])

                if self.output:
                    self.output.send(text=text, images=images)
                    logger.info(f"send_message: sent {len(images)} images")
                    return {"status": "sent", "images_count": len(images)}
                else:
                    logger.info(f"send_message (no handler): text={text[:50] if text else None}..., {len(images)} images")
                    return {"status": "no_output_handler", "would_send": {"text": text, "images": images}}

            # --- WEB SEARCH & BROWSING ---
            elif tool_name == "web_search":
                from services.web_search import web_search
                query = tool_input.get("query", "")
                count = tool_input.get("count", 5)
                result = web_search(query, count=count)
                logger.info(f"web_search: '{query}' returned {result.get('result_count', 0)} results")
                return result

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

                # Run image analysis to extract full metadata (colors, cut, fit, texture, etc.)
                from services.image_analyzer import create_image_analyzer
                image_file.seek(0)
                try:
                    analyzer = create_image_analyzer(use_real_ai=True)
                    analysis_data = analyzer.analyze_clothing_item(image_file, product_title=name)
                    # Preserve agent-provided name and category over analyzer guesses
                    analysis_data["name"] = name
                    analysis_data["category"] = category
                except Exception as e:
                    logger.warning(f"add_considering_item: image analysis failed, using minimal metadata: {e}")
                    analysis_data = {
                        "name": name,
                        "category": category,
                        "sub_category": f"{category}_general",
                        "colors": [],
                        "style": "casual",
                        "brand": "",
                    }

                image_file.seek(0)  # Reset after analysis
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

            elif tool_name == "get_considering_items":
                from services.consider_buying_manager import ConsiderBuyingManager
                manager = ConsiderBuyingManager(user_id=self.user_id)
                status = tool_input.get("status")
                items = manager.get_items(status=status)
                return {"items": items, "count": len(items)}

            elif tool_name == "get_considering_stats":
                from services.consider_buying_manager import ConsiderBuyingManager
                manager = ConsiderBuyingManager(user_id=self.user_id)
                stats = manager.get_stats()
                return {"stats": stats}

            elif tool_name == "decide_considering_item":
                from services.consider_buying_manager import ConsiderBuyingManager
                manager = ConsiderBuyingManager(user_id=self.user_id)
                item_id = tool_input.get("item_id")
                decision = tool_input.get("decision")
                reason = tool_input.get("reason")
                result = manager.execute_decision(item_id, decision, reason)
                logger.info(f"decide_considering_item: {decision} on {item_id}")
                return {
                    "success": True,
                    "item_id": item_id,
                    "decision": decision,
                    "wardrobe_item_id": result["wardrobe_item"]["id"] if result.get("wardrobe_item") else None,
                }

            elif tool_name == "delete_considering_item":
                from services.consider_buying_manager import ConsiderBuyingManager
                manager = ConsiderBuyingManager(user_id=self.user_id)
                item_id = tool_input.get("item_id")
                manager.delete_item(item_id)
                logger.info(f"delete_considering_item: deleted {item_id}")
                return {"success": True, "item_id": item_id}

            elif tool_name == "update_considering_item":
                from services.consider_buying_manager import ConsiderBuyingManager
                manager = ConsiderBuyingManager(user_id=self.user_id)
                item_id = tool_input.get("item_id")
                updates = {}
                for field in ("name", "category", "price", "notes"):
                    if field in tool_input:
                        updates[field] = tool_input[field]
                result = manager.update_considering_item(item_id, updates)
                logger.info(f"update_considering_item: updated {item_id} with {list(updates.keys())}")
                return {"success": True, "item_id": item_id, "updated_fields": list(updates.keys())}

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
