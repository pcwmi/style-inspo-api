"""
Tool definitions for the styling agent.

These map to the primitives endpoints. Tools are "dumb" - they just
fetch/store data. All styling intelligence lives in the system prompt.
"""

TOOLS = [
    # --- WARDROBE ITEMS ---
    {
        "name": "get_items",
        "description": "Get all wardrobe items for the user. Returns items with styling details, colors, category, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter_type": {
                    "type": "string",
                    "enum": ["all", "styling_challenges", "regular_wear"],
                    "description": "Filter items by type. Default: all"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_item",
        "description": "Get a specific wardrobe item by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "The item ID"
                }
            },
            "required": ["item_id"]
        }
    },

    # --- PROFILE ---
    {
        "name": "get_profile",
        "description": "Get the user's style profile including their three style words (current, aspirational, feeling) and model descriptor.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    # --- FEEDBACK ---
    {
        "name": "get_feedback",
        "description": "Get all feedback (disliked outfits) from the user.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_feedback_patterns",
        "description": "Analyze feedback to find patterns in what the user dislikes. Returns common reasons, avoided items, and raw feedback. USE THIS to avoid repeating past mistakes.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    # --- SAVED OUTFITS ---
    {
        "name": "get_saved_outfits",
        "description": "Get all outfits the user has saved (liked).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_not_worn_outfits",
        "description": "Get saved outfits that haven't been worn yet (Ready to Wear queue).",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max number to return"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_worn_outfits",
        "description": "Get outfits that have been marked as worn.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    # --- OUTFIT ACTIONS ---
    {
        "name": "save_outfit",
        "description": "Save an outfit to the user's saved outfits. Call this when you've created an outfit the user wants to keep. Returns the outfit_id needed for visualization.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Item ID from wardrobe"},
                            "name": {"type": "string", "description": "Item name"},
                            "category": {"type": "string", "description": "Item category"}
                        },
                        "required": ["id", "name", "category"]
                    },
                    "description": "List of wardrobe items in the outfit"
                },
                "styling_notes": {
                    "type": "string",
                    "description": "Styling advice for wearing this outfit"
                },
                "occasion": {
                    "type": "string",
                    "description": "What occasion this outfit is for"
                },
                "vibe_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords describing the outfit vibe"
                }
            },
            "required": ["items", "styling_notes"]
        }
    },
    {
        "name": "visualize_outfit",
        "description": "Generate a visualization of an outfit on a model matching the user's description. Takes ~60 seconds. Call this after save_outfit to show the user how the outfit looks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "outfit_id": {
                    "type": "string",
                    "description": "The outfit ID returned from save_outfit"
                }
            },
            "required": ["outfit_id"]
        }
    },

    # --- CONSIDERING (SHOPPING) ---
    {
        "name": "get_considering_items",
        "description": "Get items the user is considering buying.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["considering", "bought", "passed"],
                    "description": "Filter by decision status"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_considering_stats",
        "description": "Get shopping decision statistics (how many bought, passed, money saved).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
]


def get_tool_by_name(name: str) -> dict:
    """Get a tool definition by name."""
    for tool in TOOLS:
        if tool["name"] == name:
            return tool
    return None


# OpenAI format (slightly different structure)
TOOLS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"]
        }
    }
    for tool in TOOLS
]
