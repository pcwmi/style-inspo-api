# Stateful SMS Conversations Plan

*Created: 2026-02-09*
*Status: Planning*

## Problem Statement

Currently, SMS/WhatsApp conversations are **stateless** - each message is processed independently with no memory of previous interactions. This prevents natural conversational flows like:

- "Save that outfit" (agent doesn't know which outfit)
- "That's off, try again" (agent can't revise without context)
- "Make it more casual" (no reference to what "it" is)
- Heart reaction on image (no way to know which outfit to save)

## Current Architecture

```
User texts "outfit for work"
    ↓
Twilio webhook → /api/sms/incoming
    ↓
Background task: process_outfit_request()
    ↓
StylingAgent.run(message)  ← NO HISTORY, just single message
    ↓
Agent generates outfit → resolve_items → send_message
    ↓
User receives outfit via MMS
    ↓
User says "save this" → NEW stateless request (agent has no idea what "this" is)
```

**Key files:**
- `/Users/peichin/Projects/style-inspo-api/backend/api/sms.py` - Twilio webhook handler
- `/Users/peichin/Projects/style-inspo-api/backend/agent/agent.py` - Agent loop
- `/Users/peichin/Projects/style-inspo-api/backend/agent/output.py` - SMSOutput handler
- `/Users/peichin/Projects/style-inspo-api/backend/agent/prompts.py` - System prompt

---

## Design Options Analysis

### Option A: Redis State (Recommended)

**Store conversation state in Redis per phone number.**

```
Key: sms:conversation:{phone_hash}
Value: {
  "user_id": "peichin",
  "messages": [
    {"role": "user", "content": "outfit for work", "timestamp": "..."},
    {"role": "assistant", "content": "Here's your outfit...", "outfit_data": {...}, "timestamp": "..."}
  ],
  "last_outfit": {
    "items": [...],
    "styling_notes": "...",
    "image_urls": [...],
    "message_sid": "SM..."  // Twilio message ID for reaction mapping
  },
  "updated_at": "..."
}
TTL: 24 hours (configurable)
```

**Pros:**
- Redis already configured (used for RQ job queue)
- Fast reads/writes (~1ms)
- Built-in TTL for automatic cleanup
- Perfect for ephemeral conversation state

**Cons:**
- Additional Redis calls per message (~2-3 ops)
- State lost if Redis restarts (acceptable for conversations)

**Implementation effort:** Low-Medium (1-2 days)

### Option B: S3 State (Alternative)

**Store conversation state in S3 alongside user data.**

```
S3 Key: {user_id}/sms_conversations.json
Structure: {
  "conversations": {
    "{phone_hash}": {
      "messages": [...],
      "last_outfit": {...},
      "updated_at": "..."
    }
  }
}
```

**Pros:**
- Reuses existing StorageManager patterns
- Persistent across restarts
- No additional infrastructure

**Cons:**
- Slower (~100-200ms per read/write)
- More complex cleanup (need scheduled job)
- Overkill for ephemeral state

**Implementation effort:** Medium (2-3 days)

### Option C: Include Context in Prompt

**Pass last N messages in the agent prompt itself.**

```python
# Build context from recent messages
context = get_recent_messages(phone, limit=5)
augmented_prompt = f"""
Recent conversation:
{format_messages(context)}

Current message: {user_message}
"""
agent.run(augmented_prompt)
```

**Pros:**
- Simple implementation
- No state management needed
- Agent naturally handles context

**Cons:**
- Token overhead for every message
- Can't reference specific outfit data (just text)
- Limited history depth

**Implementation effort:** Low (few hours)

### Recommendation: Option A (Redis) + C (Prompt Context)

**Hybrid approach:**
1. Store state in Redis (outfit data, message SIDs)
2. Include recent messages in prompt for natural conversation
3. Agent uses state for actions (save_outfit, apply feedback)

---

## Recommended Architecture

### Data Model: ConversationState

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class OutfitContext:
    """The most recent outfit shown to user."""
    items: List[dict]           # Item names + IDs + image URLs
    styling_notes: str
    message_sid: Optional[str]  # Twilio SID for reaction mapping
    created_at: str

@dataclass
class Message:
    """A single message in the conversation."""
    role: str                   # "user" or "assistant"
    content: str                # Text content
    timestamp: str
    outfit_context: Optional[OutfitContext] = None  # If this message included an outfit

@dataclass
class ConversationState:
    """Full conversation state for a phone number."""
    user_id: str
    phone_hash: str             # Hashed phone for privacy
    messages: List[Message]
    last_outfit: Optional[OutfitContext]
    updated_at: str

    # Limits
    MAX_MESSAGES = 10           # Keep last 10 messages
    TTL_SECONDS = 86400         # 24 hour expiry
```

### State Manager Service

```python
# New file: backend/services/conversation_state.py

import json
import hashlib
from datetime import datetime
from typing import Optional
from core.redis import get_redis_connection

class ConversationStateManager:
    """Manage conversation state in Redis."""

    KEY_PREFIX = "sms:conversation:"
    DEFAULT_TTL = 86400  # 24 hours
    MAX_MESSAGES = 10

    def __init__(self, phone: str, user_id: str):
        self.phone = phone
        self.user_id = user_id
        self.phone_hash = self._hash_phone(phone)
        self.redis = get_redis_connection(decode_responses=True)
        self.key = f"{self.KEY_PREFIX}{self.phone_hash}"

    def _hash_phone(self, phone: str) -> str:
        """Hash phone for privacy in Redis keys."""
        return hashlib.sha256(phone.encode()).hexdigest()[:16]

    def get_state(self) -> Optional[dict]:
        """Get current conversation state."""
        data = self.redis.get(self.key)
        if data:
            return json.loads(data)
        return None

    def save_state(self, state: dict) -> None:
        """Save conversation state with TTL."""
        state["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self.redis.setex(
            self.key,
            self.DEFAULT_TTL,
            json.dumps(state)
        )

    def add_message(self, role: str, content: str, outfit_context: dict = None) -> None:
        """Add a message to conversation history."""
        state = self.get_state() or {
            "user_id": self.user_id,
            "phone_hash": self.phone_hash,
            "messages": [],
            "last_outfit": None
        }

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        if outfit_context:
            message["outfit_context"] = outfit_context
            state["last_outfit"] = outfit_context

        state["messages"].append(message)

        # Trim to max messages
        if len(state["messages"]) > self.MAX_MESSAGES:
            state["messages"] = state["messages"][-self.MAX_MESSAGES:]

        self.save_state(state)

    def get_last_outfit(self) -> Optional[dict]:
        """Get the most recent outfit shown."""
        state = self.get_state()
        if state:
            return state.get("last_outfit")
        return None

    def get_messages_for_prompt(self, limit: int = 5) -> str:
        """Format recent messages for inclusion in agent prompt."""
        state = self.get_state()
        if not state or not state.get("messages"):
            return ""

        messages = state["messages"][-limit:]
        formatted = []
        for msg in messages:
            role = "User" if msg["role"] == "user" else "You"
            formatted.append(f"{role}: {msg['content']}")

        return "\n".join(formatted)

    def set_last_outfit_message_sid(self, message_sid: str) -> None:
        """Update the message SID for the last outfit (for reaction mapping)."""
        state = self.get_state()
        if state and state.get("last_outfit"):
            state["last_outfit"]["message_sid"] = message_sid
            self.save_state(state)

    def clear(self) -> None:
        """Clear conversation state."""
        self.redis.delete(self.key)
```

---

## Conversation Flows

### Flow 1: Feedback ("that's off" / "try again")

```
User: "outfit for work meeting"
    ↓
Agent: generates outfit → saves to state → sends MMS
    ↓
User: "that's off, too formal"
    ↓
[State lookup] → finds last_outfit
    ↓
Agent prompt includes:
  - Recent messages (context)
  - Last outfit items (what to revise)
  - Feedback: "too formal"
    ↓
Agent:
  1. Calls save_feedback(items, "negative", "too formal")
  2. Generates revised outfit (more casual)
  3. Sends new outfit via send_message
    ↓
Agent response: "Got it - less formal. How about this?"
```

### Flow 2: Save ("save this" / "love it")

```
User: "outfit for brunch"
    ↓
Agent: generates outfit → saves to state → sends MMS
    ↓
User: "love it, save this"
    ↓
[State lookup] → finds last_outfit with items
    ↓
Agent:
  1. Calls save_outfit(items from state)
  2. Sends confirmation
    ↓
Agent response: "Saved! You can find it in your Ready to Wear queue."
```

### Flow 3: Iteration ("make it more casual" / "swap the shoes")

```
User: "date night outfit"
    ↓
Agent: generates outfit → saves to state → sends MMS
    ↓
User: "swap the shoes for something lower"
    ↓
[State lookup] → finds last_outfit
    ↓
Agent prompt includes:
  - Last outfit items
  - Modification request: "swap shoes for lower"
    ↓
Agent:
  1. Identifies current shoes in outfit
  2. Finds alternative lower shoes from wardrobe
  3. Generates revised outfit
  4. Updates state with new outfit
  5. Sends via send_message
    ↓
Agent response: "Swapped the heels for your loafers."
```

### Edge Case: New Request Mid-Conversation

```
User: "outfit for gym"
    ↓
Agent: generates gym outfit → saves to state
    ↓
User: "actually, what about dinner instead?"
    ↓
[Detect: new request, not feedback on last outfit]
    ↓
Agent: generates dinner outfit → REPLACES state
    ↓
[Old gym outfit context is gone - this is intentional]
```

**Detection heuristic:** If user message contains occasion keywords or explicit "new outfit" signals, treat as new request rather than iteration.

---

## Reactions Section (WhatsApp Heart = Save)

### Research Findings

**Twilio WhatsApp Reaction Support: NOT CURRENTLY AVAILABLE**

Based on research of [Twilio's WhatsApp API documentation](https://www.twilio.com/docs/whatsapp/api), [Messaging Webhooks](https://www.twilio.com/docs/usage/webhooks/messaging-webhooks), and [Conversations Webhooks](https://www.twilio.com/docs/conversations/conversations-webhooks):

1. **Twilio does NOT currently support reaction webhooks** for WhatsApp messages
2. The documented webhook events include message add/update/remove, but NOT reactions
3. Other providers (Vonage, 360dialog, WhatsApp Cloud API directly) DO support reaction webhooks
4. Twilio's WhatsApp feature set is growing - they added [typing indicators in 2025](https://www.courier.com/blog/how-to-use-whatsapp-typing-indicators-on-twilio-public-beta-guide) and [reply context](https://www.twilio.com/en-us/changelog/whatsapp-inbound-messages-will-now-include-reply-context)

### Workaround Options

#### Option 1: Text-Based Save (Recommended for Now)

Since reactions aren't available, rely on text commands:

```
User hearts image (nothing happens - Twilio doesn't see it)
    ↓
User sends: "love it" or "save" or "yes" or even just a heart emoji "❤️"
    ↓
Agent recognizes save intent → saves last outfit from state
```

**Detection patterns for save intent:**
- Explicit: "save", "save this", "save it", "keep this"
- Positive: "love it", "perfect", "yes", "this is it"
- Emoji: "❤️", "👍", "🔥", "💯"

#### Option 2: Monitor Twilio Changelog

Subscribe to [Twilio Changelog](https://www.twilio.com/en-us/changelog) for WhatsApp updates. When/if reactions become available, the webhook will likely include:

```json
{
  "MessageType": "reaction",
  "ReactionEmoji": "❤️",
  "ReactedMessageSid": "SM...",  // The outfit message they reacted to
  "From": "whatsapp:+1...",
  ...
}
```

#### Option 3: WhatsApp Cloud API Direct Integration

If reactions are critical, could bypass Twilio and integrate directly with [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components#messages-object) which DOES support reaction webhooks.

**Tradeoff:** More complex setup, lose Twilio's unified SMS+WhatsApp handling.

### Future Implementation (When Twilio Adds Reactions)

```python
# In api/sms.py - add reaction handler

@router.post("/reaction")
async def handle_reaction(
    From: str = Form(...),
    ReactionEmoji: str = Form(...),
    ReactedMessageSid: str = Form(...),
):
    """Handle WhatsApp reaction webhook (when available)."""
    user_id = phone_to_user(From)
    if not user_id:
        return Response(status_code=200)  # Ignore unknown users

    # Only process positive reactions
    SAVE_REACTIONS = {"❤️", "👍", "🔥", "💯", "😍"}
    if ReactionEmoji not in SAVE_REACTIONS:
        return Response(status_code=200)

    # Look up which outfit this reaction is for
    state_manager = ConversationStateManager(phone=From, user_id=user_id)
    last_outfit = state_manager.get_last_outfit()

    if not last_outfit:
        send_sms(From, "I'm not sure which outfit you're reacting to. Send 'save' to save the last one!")
        return Response(status_code=200)

    # Verify message SID matches (if we tracked it)
    if last_outfit.get("message_sid") and last_outfit["message_sid"] != ReactedMessageSid:
        # Reaction is to an older message - need to look up
        # For MVP, just save the most recent outfit
        pass

    # Save the outfit
    from services.saved_outfits_manager import SavedOutfitsManager
    manager = SavedOutfitsManager(user_id=user_id)

    # Create outfit combo from state
    class OutfitCombo:
        def __init__(self, items, styling_notes):
            self.items = items
            self.styling_notes = styling_notes
            self.why_it_works = ""
            self.confidence_level = ""
            self.vibe_keywords = []

    outfit = OutfitCombo(
        items=last_outfit["items"],
        styling_notes=last_outfit.get("styling_notes", "")
    )

    outfit_id = manager.save_outfit(outfit_combo=outfit, reason="Saved via reaction")

    if outfit_id:
        send_sms(From, "Saved! ✓")
    else:
        send_sms(From, "Couldn't save that outfit. Try 'save' instead.")

    return Response(status_code=200)
```

### Message SID Tracking

To map reactions to specific outfits, we need to track which Twilio message SID corresponds to which outfit:

```python
# In agent/output.py - SMSOutput.send()

def send(self, text: Optional[str], images: List[str], layout: str = "list"):
    # ... existing collage generation ...

    if collage_url:
        if text:
            send_sms(self.phone, text)
        message_sid = send_mms(self.phone, " ", [collage_url])

        # Track which message contains which outfit
        if message_sid and hasattr(self, 'current_outfit'):
            state_manager = ConversationStateManager(
                phone=self.phone,
                user_id=self.user_id
            )
            state_manager.set_last_outfit_message_sid(message_sid)
```

---

## Implementation Steps

### Phase 1: State Infrastructure (Day 1)

1. **Create ConversationStateManager**
   - File: `backend/services/conversation_state.py`
   - Redis-based state storage
   - Methods: get_state, save_state, add_message, get_last_outfit

2. **Update sms.py to use state**
   - Initialize state manager with phone + user_id
   - Store user message before processing
   - Pass state context to agent

3. **Update agent to receive context**
   - Modify `StylingAgent.__init__` to accept conversation context
   - Include recent messages in prompt construction

### Phase 2: Prompt Integration (Day 1-2)

4. **Update system prompt for stateful conversations**
   - Add section: "CONVERSATION CONTEXT"
   - Instructions for handling feedback on last outfit
   - Instructions for save commands

5. **Add context injection in agent.run()**
   ```python
   def run(self, user_message: str, conversation_context: str = None):
       if conversation_context:
           augmented_message = f"""
   RECENT CONVERSATION:
   {conversation_context}

   CURRENT MESSAGE: {user_message}
   """
       else:
           augmented_message = user_message
       # ... rest of run logic
   ```

### Phase 3: Output Tracking (Day 2)

6. **Track outfits in SMSOutput**
   - After sending outfit, save to conversation state
   - Include items, styling notes, image URLs
   - Optionally track message SID for future reaction support

7. **Update send_message tool to return outfit data**
   - Agent can pass outfit data to output handler
   - Output handler stores in state

### Phase 4: Testing (Day 2-3)

8. **Create test scenarios with MockOutput**
   - Multi-turn conversation simulation
   - Feedback flow testing
   - Save flow testing
   - Edge case testing

---

## Test Cases for Self-Verification

### Test 1: Basic Feedback Flow

```python
def test_feedback_flow():
    """User gives feedback on outfit, agent revises."""
    output = MockOutput()
    state = ConversationStateManager(phone="+1234567890", user_id="test")

    # Turn 1: Request outfit
    agent = StylingAgent(user_id="test", output=output)
    agent.run("outfit for work")

    # Verify outfit was generated and saved to state
    assert len(output.messages) == 1
    last_outfit = state.get_last_outfit()
    assert last_outfit is not None
    assert len(last_outfit["items"]) > 0

    # Turn 2: Give feedback
    context = state.get_messages_for_prompt()
    agent2 = StylingAgent(user_id="test", output=output)
    agent2.run("too formal, try again", conversation_context=context)

    # Verify feedback was captured and new outfit generated
    assert len(output.messages) == 2
    # Could also verify save_feedback was called via mock
```

### Test 2: Save Flow

```python
def test_save_flow():
    """User saves outfit via text command."""
    output = MockOutput()
    state = ConversationStateManager(phone="+1234567890", user_id="test")

    # Turn 1: Generate outfit
    agent = StylingAgent(user_id="test", output=output)
    agent.run("brunch outfit")

    # Store outfit context (normally done by output handler)
    # ...

    # Turn 2: Save
    context = state.get_messages_for_prompt()
    agent2 = StylingAgent(user_id="test", output=output)
    agent2.run("save this", conversation_context=context)

    # Verify outfit was saved
    from services.saved_outfits_manager import SavedOutfitsManager
    manager = SavedOutfitsManager(user_id="test")
    saved = manager.get_saved_outfits()
    assert len(saved) > 0
```

### Test 3: State Expiry

```python
def test_state_expiry():
    """Conversation state expires after TTL."""
    state = ConversationStateManager(phone="+1234567890", user_id="test")
    state.add_message("user", "test message")

    # Verify state exists
    assert state.get_state() is not None

    # Manually expire (or wait in integration test)
    state.redis.delete(state.key)

    # Verify state is gone
    assert state.get_state() is None
```

### Test 4: Max Messages Trim

```python
def test_max_messages():
    """Conversation history is trimmed to max messages."""
    state = ConversationStateManager(phone="+1234567890", user_id="test")

    # Add more than MAX_MESSAGES
    for i in range(15):
        state.add_message("user", f"message {i}")

    # Verify only last MAX_MESSAGES are kept
    current = state.get_state()
    assert len(current["messages"]) == state.MAX_MESSAGES
    assert current["messages"][0]["content"] == "message 5"  # First 5 trimmed
```

### Test 5: New Request Replaces Context

```python
def test_new_request():
    """New outfit request replaces previous outfit context."""
    output = MockOutput()
    state = ConversationStateManager(phone="+1234567890", user_id="test")

    # Turn 1: Gym outfit
    agent = StylingAgent(user_id="test", output=output)
    agent.run("gym outfit")
    gym_outfit = state.get_last_outfit()

    # Turn 2: Dinner outfit (new request)
    context = state.get_messages_for_prompt()
    agent2 = StylingAgent(user_id="test", output=output)
    agent2.run("dinner outfit instead", conversation_context=context)
    dinner_outfit = state.get_last_outfit()

    # Verify outfit was replaced
    assert dinner_outfit != gym_outfit
```

---

## Risks and Mitigations

### Risk 1: Race Conditions

**Problem:** User sends two messages quickly before first finishes processing.

**Mitigation:**
- Redis atomic operations (SETNX for locking)
- Last-write-wins for conversation state (acceptable)
- Background task queue already serializes per-user

```python
# Optional: Add per-user lock
def process_with_lock(phone: str, user_id: str, message: str):
    lock_key = f"sms:lock:{phone_hash}"
    if not redis.setnx(lock_key, "1"):
        # Another message is processing
        send_sms(phone, "One moment, still working on your last request...")
        return

    redis.expire(lock_key, 60)  # 60 second timeout
    try:
        # Process message
        ...
    finally:
        redis.delete(lock_key)
```

### Risk 2: State Size Growth

**Problem:** Conversation state grows too large with outfit data.

**Mitigation:**
- MAX_MESSAGES limit (10 messages)
- Only store essential outfit data (not full item objects)
- TTL expires old conversations

**State size estimate:**
- 10 messages x ~200 chars = 2KB
- 1 outfit context x ~1KB = 1KB
- Total: ~3KB per conversation (well under Redis limits)

### Risk 3: Redis Unavailable

**Problem:** Redis down = state unavailable.

**Mitigation:**
- Graceful degradation: treat as new conversation
- Agent still works, just without context
- Log warning for monitoring

```python
def get_state(self) -> Optional[dict]:
    try:
        data = self.redis.get(self.key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}")
        return None  # Graceful degradation
```

### Risk 4: Incorrect Context Interpretation

**Problem:** Agent misinterprets "this" or "that" reference.

**Mitigation:**
- Clear prompt instructions for context handling
- Default to most recent outfit for ambiguous references
- Ask for clarification if truly ambiguous

```
# In system prompt
If user says "save this" or "love it" without context,
save the most recent outfit you showed them.

If user's feedback is ambiguous (could apply to multiple outfits),
ask: "Which outfit are you referring to?"
```

### Risk 5: Reaction Mapping Failure

**Problem:** User reacts to older message, state only has latest outfit.

**Mitigation (when reactions available):**
- Store message SID with each outfit in state
- If reaction SID doesn't match latest, check if we have it
- Fallback: save latest outfit with warning

---

## Success Metrics

1. **Conversation success rate:** % of multi-turn conversations that complete without user confusion
2. **Save via context:** % of saves that use "save this" vs explicit re-specification
3. **Feedback application:** % of revision requests that successfully modify the previous outfit
4. **State hit rate:** % of messages that successfully retrieve conversation state

---

## Future Enhancements

1. **Cross-channel state:** Share conversation state between SMS and web chat
2. **Outfit history:** Store more than just last outfit for "show me the second one"
3. **Proactive follow-up:** "Did you end up wearing that outfit?"
4. **Multi-day context:** "Something like what you suggested yesterday"

---

## References

- [Twilio WhatsApp API Documentation](https://www.twilio.com/docs/whatsapp/api)
- [Twilio Messaging Webhooks](https://www.twilio.com/docs/usage/webhooks/messaging-webhooks)
- [Twilio Conversations Webhooks](https://www.twilio.com/docs/conversations/conversations-webhooks)
- [WhatsApp Typing Indicators (2025 feature)](https://www.courier.com/blog/how-to-use-whatsapp-typing-indicators-on-twilio-public-beta-guide)
- [WhatsApp Reply Context Changelog](https://www.twilio.com/en-us/changelog/whatsapp-inbound-messages-will-now-include-reply-context)
