#!/usr/bin/env python3
"""
Simulate the SF packing conversation with Variant B prompt.

Replays the exact conversation from April 12, 2026:
  "Pack a Monday-Thursday SF trip, low-key working trip..."

Usage:
    cd backend
    PACKING_VARIANT=B python3 simulate_packing_ab.py

Outputs a transcript of what the agent would send over WhatsApp,
showing tool calls + text for evaluation.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from agent.tools import TOOLS, TOOLS_OPENAI
from agent.prompts import get_system_prompt


class SimAgent:
    """Minimal agent loop for simulation — same logic as StylingAgent but with
    clean tracing output for evaluating message structure."""

    def __init__(self, user_id: str, variant: str = "A"):
        self.user_id = user_id
        self.variant = variant
        self.system_prompt = get_system_prompt(variant)
        self.history = []
        self.turn_count = 0
        self.max_turns = 15

        import openai
        self.client = openai.OpenAI()
        self.model = "gpt-5.2"

        # Import tools executor from production agent
        from agent.agent import StylingAgent
        self._executor = StylingAgent(user_id=user_id, provider="openai")

        print(f"\n{'='*60}")
        print(f"Variant {variant} Simulation — user: {user_id}")
        print(f"Packing section: {'Visual-First' if variant == 'B' else 'Ingredients-First'}")
        print(f"{'='*60}\n")

    def send(self, user_message: str):
        """Send a user message and print the full agent response trace."""
        print(f"\n{'─'*50}")
        print(f"USER: {user_message}")
        print(f"{'─'*50}")

        self.history.append({"role": "user", "content": user_message})

        messages = [{"role": "system", "content": self.system_prompt}] + self.history
        tool_calls_made = []

        for turn in range(self.max_turns):
            self.turn_count += 1

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS_OPENAI,
                tool_choice="auto",
            )

            msg = response.choices[0].message
            finish = response.choices[0].finish_reason

            if finish == "stop":
                text = msg.content or ""
                print(f"\nAGENT TEXT:\n{text}")
                self.history.append({"role": "assistant", "content": text})
                if tool_calls_made:
                    print(f"\n[Tools used: {', '.join(tool_calls_made)}]")
                return text

            if finish == "tool_calls":
                messages.append(msg)
                tool_results = []

                for tc in msg.tool_calls:
                    fn = tc.function.name
                    args = json.loads(tc.function.arguments)
                    tool_calls_made.append(fn)

                    print(f"\n  TOOL → {fn}({json.dumps({k: str(v)[:80] for k, v in args.items()})})")

                    # Execute real tool for data fetching; mock for side-effects
                    if fn in ("get_profile", "get_items", "get_feedback_patterns",
                              "get_saved_outfits", "web_search", "get_not_worn_outfits",
                              "get_feedback", "get_considering_items"):
                        result = self._executor._execute_tool(fn, args)
                        # Summarize result for readability
                        if isinstance(result, dict):
                            if "items" in result:
                                print(f"  ← {len(result['items'])} items")
                            elif "profile" in result:
                                p = result["profile"]
                                print(f"  ← profile: {p.get('style_words', {})}")
                            elif "results" in result:
                                print(f"  ← {len(result.get('results', []))} search results")
                            else:
                                keys = list(result.keys())[:3]
                                print(f"  ← {{{', '.join(keys)}...}}")
                    elif fn == "present_outfit":
                        items = args.get("items", [])
                        label = args.get("label", "")
                        viz = args.get("visualize", False)
                        print(f"  ← [COLLAGE] {label or 'outfit'}: {', '.join(items[:4])}{'...' if len(items)>4 else ''}")
                        if viz:
                            print(f"  ← [VISUALIZATION requested]")
                        result = {"success": True, "message_sent": True}
                    elif fn == "send_message":
                        body = args.get("body", "")
                        media = args.get("media_urls", [])
                        if media:
                            print(f"  ← [SEND_MESSAGE with {len(media)} image(s)]: {body[:80]}")
                        else:
                            print(f"  ← [SEND_MESSAGE text]: {body[:120]}")
                        result = {"success": True}
                    elif fn == "resolve_items":
                        names = args.get("item_names", [])
                        print(f"  ← [RESOLVE] {len(names)} items")
                        result = {"items": {n: f"https://s3.example.com/{n}.jpg" for n in names}}
                    else:
                        print(f"  ← [MOCKED]")
                        result = {"success": True}

                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result)
                    })

                messages.extend(tool_results)

        print("\n[MAX TURNS REACHED]")
        return ""


def run_simulation(variant: str):
    agent = SimAgent(user_id="peichin", variant=variant)

    # Turn 1: Initial packing request
    agent.send("Pack a Monday-Thursday SF trip for me, look up the weather there. "
               "The trip is a low-key working trip. Mostly just working with two friends in the office. "
               "Pack mostly low key things, but maybe add some color since it's spring")

    # Turn 2: User answers the clarifying question
    agent.send("Tmrw to Thursday. First day and last day will uber since I have luggage, "
               "other days walking")

    # Turn 3: User asks to see outfits (only needed if agent didn't show them)
    # (Variant B should show outfits immediately after turn 2 — if so this is a no-op)
    # agent.send("Great, show me what the outfits look like every day")

    # Turn 4: User feedback + remove an item
    agent.send("These look great. I think I'll skip the Cortez sneaker. "
               "Now give me: what I will wear on Monday so I don't pack them, "
               "and the list of things I'll pack for the rest of the trip")

    # Turn 5: Follow-up question
    agent.send("How about belts")


if __name__ == "__main__":
    variant = os.getenv("PACKING_VARIANT", "B")
    print(f"Running simulation with PACKING_VARIANT={variant}")
    run_simulation(variant)
