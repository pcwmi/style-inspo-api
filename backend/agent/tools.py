"""
Tool definitions for the styling agent.

These map to the primitives endpoints. Tools are "dumb" - they just
fetch/store data. All styling intelligence lives in the system prompt.

Every tool includes a "reasoning" field so we can see WHY the agent
made each decision in the logs.
"""

# Common reasoning field added to all tools
REASONING_FIELD = {
    "reasoning": {
        "type": "string",
        "description": "Explain WHY you're calling this tool and what you expect to learn/accomplish"
    }
}

TOOLS = [
    # --- WARDROBE ITEMS ---
    {
        "name": "get_items",
        "description": "Get all wardrobe items for the user. Returns items with styling details, colors, category, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "filter_type": {
                    "type": "string",
                    "enum": ["all", "styling_challenges", "regular_wear"],
                    "description": "Filter items by type. Default: all"
                }
            },
            "required": ["reasoning"]
        }
    },
    {
        "name": "get_item",
        "description": "Get a specific wardrobe item by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "item_id": {
                    "type": "string",
                    "description": "The item ID"
                }
            },
            "required": ["reasoning", "item_id"]
        }
    },

    # --- PROFILE ---
    {
        "name": "get_profile",
        "description": "Get the user's style profile including their three style words (current, aspirational, feeling) and model descriptor.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD
            },
            "required": ["reasoning"]
        }
    },

    # --- FEEDBACK ---
    {
        "name": "get_feedback",
        "description": "Get all feedback (disliked outfits) from the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD
            },
            "required": ["reasoning"]
        }
    },
    {
        "name": "get_feedback_patterns",
        "description": "Analyze feedback to find patterns in what the user dislikes. Returns common reasons, avoided items, and raw feedback. USE THIS to avoid repeating past mistakes.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD
            },
            "required": ["reasoning"]
        }
    },
    {
        "name": "save_feedback",
        "description": "Save feedback about an outfit - either positive (what they loved) or negative (what didn't work). Use this when user says 'I don't like this because...' or 'I love this because...'",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Item name"},
                            "category": {"type": "string", "description": "Item category"}
                        },
                        "required": ["name"]
                    },
                    "description": "Items in the outfit being reviewed"
                },
                "feedback_type": {
                    "type": "string",
                    "enum": ["positive", "negative"],
                    "description": "Whether this is positive (loved it) or negative (didn't work) feedback"
                },
                "reason": {
                    "type": "string",
                    "description": "The user's reason - capture the SPIRIT, not just surface words. E.g., 'proportions felt off' not just 'didn't like it'"
                },
                "style_lesson": {
                    "type": "string",
                    "description": "What styling principle does this teach? E.g., 'User prefers fitted tops with wide pants, not oversized on oversized'"
                }
            },
            "required": ["reasoning", "items", "feedback_type", "reason", "style_lesson"]
        }
    },

    # --- SAVED OUTFITS ---
    {
        "name": "get_saved_outfits",
        "description": "Get all outfits the user has saved (liked).",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD
            },
            "required": ["reasoning"]
        }
    },
    {
        "name": "get_not_worn_outfits",
        "description": "Get saved outfits that haven't been worn yet (Ready to Wear queue).",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "limit": {
                    "type": "integer",
                    "description": "Max number to return"
                }
            },
            "required": ["reasoning"]
        }
    },
    {
        "name": "get_worn_outfits",
        "description": "Get outfits that have been marked as worn.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD
            },
            "required": ["reasoning"]
        }
    },

    # --- OUTFIT ACTIONS ---
    {
        "name": "save_outfit",
        "description": "Save an outfit to the user's saved outfits. Only call this when the user explicitly asks to save, or confirms after you offer. Never save silently. Returns the outfit_id needed for visualization.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
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
            "required": ["reasoning", "items", "styling_notes"]
        }
    },
    {
        "name": "visualize_outfit",
        "description": "Generate a visualization of an outfit on a model matching the user's description. Takes ~60 seconds. Call this after save_outfit to show the user how the outfit looks.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "outfit_id": {
                    "type": "string",
                    "description": "The outfit ID returned from save_outfit"
                }
            },
            "required": ["reasoning", "outfit_id"]
        }
    },

    # --- RESOLVER (text → images) ---
    {
        "name": "resolve_items",
        "description": "Match item names to wardrobe items and get their image URLs. Use EXACT names from get_items for best results. Returns resolved items with images and any unresolved names.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "descriptions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Item names to match (use exact names from get_items)"
                }
            },
            "required": ["reasoning", "descriptions"]
        }
    },

    # --- OUTPUT (send to user) ---
    {
        "name": "send_message",
        "description": "Send a message to the user with optional images. Use this to SHOW items/outfits, not just describe them.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "text": {
                    "type": "string",
                    "description": "Text message to send"
                },
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Image URLs from resolve_items to include"
                },
                "layout": {
                    "type": "string",
                    "enum": ["list", "outfit"],
                    "description": "How to display: 'list' for browsing items, 'outfit' for styled combination"
                }
            },
            "required": ["reasoning"]
        }
    },

    # --- WEB BROWSING ---
    {
        "name": "browse_url",
        "description": "Fetch a web page (e.g. a sale or collection page) and extract the products listed on it. Returns product names, prices, sale prices, and links. Use this when a user shares a URL and wants shopping advice.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "url": {
                    "type": "string",
                    "description": "The URL to browse (e.g. https://frame-store.com/collections/sale-women)"
                }
            },
            "required": ["reasoning", "url"]
        }
    },

    # --- CONSIDERING (SHOPPING) ---
    {
        "name": "get_considering_items",
        "description": "Get items the user is considering buying.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "status": {
                    "type": "string",
                    "enum": ["considering", "bought", "passed"],
                    "description": "Filter by decision status"
                }
            },
            "required": ["reasoning"]
        }
    },
    {
        "name": "get_considering_stats",
        "description": "Get shopping decision statistics (how many bought, passed, money saved).",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD
            },
            "required": ["reasoning"]
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
