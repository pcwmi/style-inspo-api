"""
Agent conversation logger - persists agent turn traces to S3 for eval/replay.

Each agent.run() produces a structured trace (tool calls, reasoning, responses).
This module saves those traces to daily log files so they survive Railway log rotation.

Storage: {user_id}/agent_logs/{YYYY-MM-DD}.json
"""

import os
import logging
from datetime import datetime

from services.storage_manager import StorageManager

logger = logging.getLogger(__name__)


def log_agent_turn(user_id, channel, user_message, image_urls, agent_response,
                   turn_log, model, conversation_length):
    """Persist a complete agent turn trace to S3 for eval/replay."""
    storage = StorageManager(
        storage_type=os.getenv("STORAGE_TYPE", "local"),
        user_id=user_id
    )

    timestamp = datetime.now()
    entry = {
        "timestamp": timestamp.isoformat(),
        "channel": channel,
        "model": model,
        "conversation_length": conversation_length,
        "input": {
            "message": user_message,
            "image_urls": image_urls or [],
        },
        "output": {
            "response": agent_response,
        },
        "trace": turn_log,
    }

    # Append to daily log file (one file per user per day)
    date_str = timestamp.strftime("%Y-%m-%d")
    filename = f"agent_logs/{date_str}.json"

    existing = storage.load_json(filename) or {"date": date_str, "turns": []}
    existing["turns"].append(entry)
    storage.save_json(existing, filename)

    logger.info(f"Logged agent turn for {user_id} ({len(turn_log)} trace entries)")
