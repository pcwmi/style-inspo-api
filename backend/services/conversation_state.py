"""
Conversation State Manager - Redis-backed conversation context for SMS.

Stores:
- Last outfit shown (for save/feedback/refinement)
- Outfit history (last 3 outfits for "go back" functionality)
- Recent message history (for context)
- Automatic TTL expiration (24 hours)
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, List, Any

from redis import Redis
from core.config import settings

logger = logging.getLogger(__name__)

TTL_SECONDS = 86400  # 24 hours
MAX_MESSAGES = 10    # Cap message history
MAX_OUTFIT_HISTORY = 3  # Keep last 3 outfits for "go back" functionality


@dataclass
class ConversationState:
    """Conversation state for a phone number."""
    user_id: str
    phone: str
    last_outfit: Dict[str, Any] = field(default_factory=dict)
    outfit_history: List[Dict[str, Any]] = field(default_factory=list)  # Previous outfits (max 3)
    messages: List[Dict[str, str]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationState":
        return cls(
            user_id=data.get("user_id", ""),
            phone=data.get("phone", ""),
            last_outfit=data.get("last_outfit", {}),
            outfit_history=data.get("outfit_history", []),
            messages=data.get("messages", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", "")
        )


class ConversationStateManager:
    """Manage SMS conversation state in Redis."""

    def __init__(self, phone: str):
        self.phone = self._normalize_phone(phone)
        self.key = f"sms:conversation:{self.phone}"
        self._redis: Optional[Redis] = None

    @property
    def redis(self) -> Redis:
        """Lazy Redis connection with decode_responses=True for JSON storage."""
        if self._redis is None:
            self._redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for consistent Redis key.

        Strips whatsapp: prefix and non-digit characters (except +).
        """
        # Remove whatsapp: prefix
        normalized = phone.replace("whatsapp:", "")
        # Keep + and digits only
        normalized = "".join(c for c in normalized if c.isdigit() or c == "+")
        return normalized

    def get_state(self) -> Optional[ConversationState]:
        """Get current conversation state, or None if not found."""
        try:
            data = self.redis.get(self.key)
            if not data:
                return None
            parsed = json.loads(data)
            return ConversationState.from_dict(parsed)
        except Exception as e:
            logger.error(f"Failed to get conversation state: {e}")
            return None

    def save_state(self, state: ConversationState) -> bool:
        """Save conversation state with TTL.

        Returns True if successful, False otherwise.
        """
        try:
            state.updated_at = datetime.utcnow().isoformat() + "Z"
            # Cap message history
            state.messages = state.messages[-MAX_MESSAGES:]
            data = json.dumps(state.to_dict())
            self.redis.setex(self.key, TTL_SECONDS, data)
            logger.info(f"Saved conversation state for {self.phone}")
            return True
        except Exception as e:
            logger.error(f"Failed to save conversation state: {e}")
            return False

    def get_or_create_state(self, user_id: str) -> ConversationState:
        """Get existing state or create new one."""
        state = self.get_state()
        if state is None:
            state = ConversationState(user_id=user_id, phone=self.phone)
            self.save_state(state)
        return state

    def set_last_outfit(self, outfit: Dict[str, Any], push_to_history: bool = True) -> bool:
        """Update the last outfit shown.

        Args:
            outfit: Dict with items, styling_notes, collage_url, etc.
            push_to_history: If True, push current last_outfit to history before replacing

        When push_to_history is True, allows user to say "go back to the previous outfit"
        and agent can restore it from outfit_history.
        """
        state = self.get_state()
        if state:
            # Push current outfit to history before replacing (if it has items)
            if push_to_history and state.last_outfit and state.last_outfit.get("items"):
                state.outfit_history.append(state.last_outfit)
                # Cap history at MAX_OUTFIT_HISTORY
                state.outfit_history = state.outfit_history[-MAX_OUTFIT_HISTORY:]

            state.last_outfit = outfit
            return self.save_state(state)
        return False

    def get_outfit_from_history(self, index: int = 0) -> Optional[Dict[str, Any]]:
        """Get an outfit from history by index.

        Args:
            index: 0 = most recent in history, 1 = one before that, etc.

        Returns:
            Outfit dict or None if not found.
        """
        state = self.get_state()
        if state and state.outfit_history:
            # History is ordered oldest to newest, so reverse for access
            reversed_history = list(reversed(state.outfit_history))
            if 0 <= index < len(reversed_history):
                return reversed_history[index]
        return None

    def restore_outfit_from_history(self, index: int = 0) -> bool:
        """Restore an outfit from history as the current outfit.

        This is useful when user says "go back to the previous outfit".

        Args:
            index: 0 = most recent in history, 1 = one before that, etc.

        Returns:
            True if successfully restored, False if not found.
        """
        outfit = self.get_outfit_from_history(index)
        if outfit:
            # Don't push current to history when restoring (avoid duplicate)
            return self.set_last_outfit(outfit, push_to_history=False)
        return False

    def append_message(self, role: str, content: str) -> bool:
        """Append a message to conversation history.

        Args:
            role: 'user' or 'assistant'
            content: Message text (will be truncated to 500 chars)
        """
        state = self.get_state()
        if state:
            state.messages.append({
                "role": role,
                "content": content[:500],  # Truncate long messages
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            return self.save_state(state)
        return False

    def clear(self) -> bool:
        """Clear conversation state."""
        try:
            self.redis.delete(self.key)
            logger.info(f"Cleared conversation state for {self.phone}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear conversation state: {e}")
            return False
