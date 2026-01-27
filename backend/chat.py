#!/usr/bin/env python3
"""
Interactive CLI for testing the Styling Agent.

Usage:
    python chat.py                      # Default: anthropic, user=peichin
    python chat.py --provider openai    # Use OpenAI
    python chat.py --user dimple        # Different user
    python chat.py -v                   # Verbose mode (show full tool results)

Example conversation:
    > What tops do I have?
    > What should I wear for a casual Friday?
    > What outfits have I saved?
"""

import argparse
import json
import os
import sys
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from agent.tools import TOOLS, TOOLS_OPENAI
from agent.prompts import STYLING_SYSTEM_PROMPT


class TracingAgent:
    """Agent with visible traces for debugging."""

    def __init__(
        self,
        user_id: str,
        provider: str = "anthropic",
        model: Optional[str] = None,
        verbose: bool = False
    ):
        self.user_id = user_id
        self.provider = provider
        self.verbose = verbose
        self.max_turns = 10

        if model:
            self.model = model
        elif provider == "anthropic":
            self.model = "claude-sonnet-4-20250514"
        else:
            # gpt-5.1: Best reasoning for garment physics (~$0.024/outfit)
            # For production, consider gpt-5-mini (~$0.005/outfit)
            self.model = "gpt-5.1"

        # Initialize client
        if provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic()
        else:
            import openai
            self.client = openai.OpenAI()

        print(f"\n🤖 Agent initialized: {provider}/{self.model}")
        print(f"👤 User: {user_id}")
        print(f"📊 Verbose: {verbose}")
        print("-" * 50)

    def run(self, user_message: str) -> str:
        """Run the agent loop with tracing."""
        if self.provider == "anthropic":
            return self._run_anthropic(user_message)
        else:
            return self._run_openai(user_message)

    def _run_anthropic(self, user_message: str) -> str:
        """Anthropic/Claude agent loop with tracing."""
        messages = [{"role": "user", "content": user_message}]

        for turn in range(self.max_turns):
            print(f"\n⚙️  Turn {turn + 1}")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=STYLING_SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )

            print(f"   Stop reason: {response.stop_reason}")

            if response.stop_reason == "end_turn":
                return self._extract_text_anthropic(response)

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"\n   🔧 Tool: {block.name}")
                        print(f"      Input: {json.dumps(block.input, indent=2)}")

                        result = self._execute_tool(block.name, block.input)

                        if self.verbose:
                            print(f"      Result: {json.dumps(result, indent=2)}")
                        else:
                            # Abbreviated result
                            if isinstance(result, dict):
                                if "items" in result:
                                    print(f"      Result: {len(result['items'])} items")
                                elif "feedback" in result:
                                    print(f"      Result: {len(result['feedback'])} feedback entries")
                                elif "outfits" in result:
                                    print(f"      Result: {len(result['outfits'])} outfits")
                                elif "error" in result:
                                    print(f"      Result: ERROR - {result['error']}")
                                else:
                                    keys = list(result.keys())[:3]
                                    print(f"      Result: {{{', '.join(keys)}...}}")
                            else:
                                print(f"      Result: {str(result)[:100]}...")

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })

                messages.append({"role": "user", "content": tool_results})

        print("\n⚠️  Max turns reached")
        return "I apologize, but I wasn't able to complete this request."

    def _run_openai(self, user_message: str) -> str:
        """OpenAI agent loop with tracing."""
        messages = [
            {"role": "system", "content": STYLING_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        for turn in range(self.max_turns):
            print(f"\n⚙️  Turn {turn + 1}")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS_OPENAI,
                tool_choice="auto"
            )

            choice = response.choices[0]
            print(f"   Finish reason: {choice.finish_reason}")

            if choice.finish_reason == "stop":
                return choice.message.content or ""

            if choice.finish_reason == "tool_calls":
                messages.append(choice.message)

                for tool_call in choice.message.tool_calls:
                    tool_input = json.loads(tool_call.function.arguments)
                    print(f"\n   🔧 Tool: {tool_call.function.name}")
                    print(f"      Input: {json.dumps(tool_input, indent=2)}")

                    result = self._execute_tool(tool_call.function.name, tool_input)

                    if self.verbose:
                        print(f"      Result: {json.dumps(result, indent=2)}")
                    else:
                        # Abbreviated result
                        if isinstance(result, dict):
                            if "items" in result:
                                print(f"      Result: {len(result['items'])} items")
                            elif "feedback" in result:
                                print(f"      Result: {len(result['feedback'])} feedback entries")
                            elif "outfits" in result:
                                print(f"      Result: {len(result['outfits'])} outfits")
                            elif "error" in result:
                                print(f"      Result: ERROR - {result['error']}")
                            else:
                                keys = list(result.keys())[:3]
                                print(f"      Result: {{{', '.join(keys)}...}}")
                        else:
                            print(f"      Result: {str(result)[:100]}...")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

        print("\n⚠️  Max turns reached")
        return "I apologize, but I wasn't able to complete this request."

    def _extract_text_anthropic(self, response) -> str:
        """Extract text from Anthropic response."""
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """Execute a tool by calling the corresponding primitive."""
        import httpx

        base_url = os.getenv("PRIMITIVES_BASE_URL", "http://localhost:8000")

        try:
            if tool_name == "get_items":
                filter_type = tool_input.get("filter_type", "all")
                # Use compact=true to reduce tokens by ~80%
                url = f"{base_url}/primitives/items/{self.user_id}?filter_type={filter_type}&compact=true"
                resp = httpx.get(url, timeout=30)

            elif tool_name == "get_item":
                item_id = tool_input["item_id"]
                url = f"{base_url}/primitives/items/{self.user_id}/{item_id}"
                resp = httpx.get(url, timeout=30)

            elif tool_name == "get_profile":
                url = f"{base_url}/primitives/profile/{self.user_id}"
                resp = httpx.get(url, timeout=30)

            elif tool_name == "get_feedback":
                url = f"{base_url}/primitives/feedback/{self.user_id}"
                resp = httpx.get(url, timeout=30)

            elif tool_name == "get_feedback_patterns":
                url = f"{base_url}/primitives/feedback/{self.user_id}/patterns"
                resp = httpx.get(url, timeout=30)

            elif tool_name == "get_saved_outfits":
                url = f"{base_url}/primitives/outfits/{self.user_id}"
                resp = httpx.get(url, timeout=30)

            elif tool_name == "get_not_worn_outfits":
                limit = tool_input.get("limit", "")
                url = f"{base_url}/primitives/outfits/{self.user_id}/not-worn"
                if limit:
                    url += f"?limit={limit}"
                resp = httpx.get(url, timeout=30)

            elif tool_name == "get_worn_outfits":
                url = f"{base_url}/primitives/outfits/{self.user_id}/worn"
                resp = httpx.get(url, timeout=30)

            elif tool_name == "get_considering_items":
                status = tool_input.get("status", "")
                url = f"{base_url}/primitives/considering/{self.user_id}"
                if status:
                    url += f"?status={status}"
                resp = httpx.get(url, timeout=30)

            elif tool_name == "get_considering_stats":
                url = f"{base_url}/primitives/considering/{self.user_id}/stats"
                resp = httpx.get(url, timeout=30)

            else:
                return {"error": f"Unknown tool: {tool_name}"}

            resp.raise_for_status()
            return resp.json()

        except Exception as e:
            return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Interactive Styling Agent CLI")
    parser.add_argument("--provider", "-p", choices=["anthropic", "openai"],
                        default="anthropic", help="LLM provider")
    parser.add_argument("--model", "-m", help="Model name (optional)")
    parser.add_argument("--user", "-u", default="peichin", help="User ID")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show full tool results")
    args = parser.parse_args()

    agent = TracingAgent(
        user_id=args.user,
        provider=args.provider,
        model=args.model,
        verbose=args.verbose
    )

    print("\nType your message (or 'quit' to exit):\n")

    while True:
        try:
            user_input = input("> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            response = agent.run(user_input)
            print(f"\n💬 Agent:\n{response}\n")
            print("-" * 50)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
