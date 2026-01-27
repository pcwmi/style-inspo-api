"""
Agent - Simple agentic loop for styling assistant.

No framework needed. Just a loop that:
1. Sends user message + tools to Claude
2. If tool_use, executes and sends result back
3. If end_turn, returns response
"""

from agent.agent import run_agent, StylingAgent

__all__ = ["run_agent", "StylingAgent"]
