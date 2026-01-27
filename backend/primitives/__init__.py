"""
Primitives - Atomic operations for agent-first architecture.

These are the fundamental building blocks that an agent uses to interact
with user data. Each primitive is a simple CRUD operation with no bundled logic.

Design principles:
1. Tools are dumb data operations
2. Agent decides, tools execute
3. No bundled logic - each operation is atomic
4. "To change behavior, edit prompt or refactor code?" -> If refactor, too coarse
"""

from primitives.router import primitives_router

__all__ = ["primitives_router"]
