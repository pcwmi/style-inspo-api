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
        "description": "Get the user's style profile including their three style words (current, aspirational, feeling), home location, and model descriptor.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD
            },
            "required": ["reasoning"]
        }
    },
    {
        "name": "update_location",
        "description": (
            "Update the user's home location (city/region used for weather and local context). "
            "Call this when the user tells you where they live or that they've moved "
            "(e.g. 'I just moved to Portland', 'I'm based in NYC now'). Do NOT call it for a "
            "one-off trip ('I'm in Chicago this weekend') — for those, just use that city for the "
            "current request without changing their saved home location."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "location": {
                    "type": "string",
                    "description": "The user's home location, e.g. 'Seattle, WA' or 'Portland, OR'."
                }
            },
            "required": ["reasoning", "location"]
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
        "description": "Get patterns in what the user loves (saved outfits) AND hates (dislikes), plus silent feedback (save rate and patterns from outfits generated but not saved). Returns explicit positive/negative feedback with reasons, and implicit signal from save rate. USE THIS to understand their taste — learn from successes, avoid repeating mistakes, and calibrate based on their overall save rate.",
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

    {
        "name": "mark_worn",
        "description": "Mark a saved outfit as worn. Use when user says 'I wore this today' or 'wore outfit #1'. Call get_not_worn_outfits first to find the outfit_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "outfit_id": {
                    "type": "string",
                    "description": "The outfit ID to mark as worn (from get_saved_outfits or get_not_worn_outfits)"
                }
            },
            "required": ["reasoning", "outfit_id"]
        }
    },

    {
        "name": "delete_outfit",
        "description": "Remove a saved outfit from the user's collection (unsave it). Use when user says 'unsave that outfit', 'remove that outfit', 'delete that saved outfit', etc. Call get_saved_outfits first to find the outfit_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "outfit_id": {
                    "type": "string",
                    "description": "The outfit ID to delete (from get_saved_outfits)"
                }
            },
            "required": ["reasoning", "outfit_id"]
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
        "name": "present_outfit",
        "description": "Present a NEW outfit you've composed from wardrobe items. Triggers editorial flat-lay collage. Use this when you've created a new outfit combination from the user's closet.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "text": {
                    "type": "string",
                    "description": "Text message to send with the outfit"
                },
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Image URLs from resolve_items for the outfit pieces"
                },
                "item_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Exact wardrobe item names (same order as images). REQUIRED — these persist in conversation history so you can reference the outfit's composition later (e.g. when building a pack list, regenerating a day, or answering follow-up questions). Use the exact names from get_items."
                },
                "visualize": {
                    "type": "boolean",
                    "description": "Generate a styled model visualization. Set true for complete outfits."
                }
            },
            "required": ["reasoning", "images", "item_names"]
        }
    },
    {
        "name": "send_message",
        "description": "Send text and/or images to the user AS-IS. No collage. Use for text replies, showing saved outfit visualizations, browsing items individually, or any non-outfit message.",
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
                    "description": "Image URLs to send as-is (no collage processing)"
                }
            },
            "required": ["reasoning"]
        }
    },

    # --- WEB SEARCH & BROWSING ---
    {
        "name": "web_search",
        "description": "Search the web for any real-world information — fashion items, weather, local events, shopping recommendations, or style inspiration. Use for: (1) finding specific products to recommend, (2) current weather to factor into outfit suggestions, (3) upcoming events or occasions, (4) any query requiring current/external info. Returns titles, URLs, descriptions, and thumbnails.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "query": {
                    "type": "string",
                    "description": "Search query — be specific with item type, color, material, price range, gender. E.g. 'women cream cable knit cardigan under $150'"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of results (default 5, max 20). Keep low to save tokens."
                }
            },
            "required": ["reasoning", "query"]
        }
    },
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
    {
        "name": "add_considering_item",
        "description": "Save a product to the user's item list — either something they're considering OR something they already bought. When the user says 'I bought X, add it to my wardrobe/closet' with a URL, use this followed immediately by decide_considering_item(decision='bought') to move it into their wardrobe. Also use when recommending products from browse_url so they can be included in outfit collages.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "name": {
                    "type": "string",
                    "description": "Product name (e.g., 'Hovey Striped Top Dove/Black')"
                },
                "image_url": {
                    "type": "string",
                    "description": "Product image URL (from browse_url results)"
                },
                "category": {
                    "type": "string",
                    "description": "Category: tops, bottoms, dresses, outerwear, shoes, bags, accessories"
                },
                "price": {
                    "type": "number",
                    "description": "Price in dollars"
                },
                "source_url": {
                    "type": "string",
                    "description": "Product page URL for purchase link"
                }
            },
            "required": ["reasoning", "name", "image_url", "category"]
        }
    },
    {
        "name": "decide_considering_item",
        "description": "Record a buying decision on an item the user is considering. Use when user says 'I bought the top' or 'pass on those pants'. Call get_considering_items first to find the item_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "item_id": {
                    "type": "string",
                    "description": "The considering item ID (from get_considering_items)"
                },
                "decision": {
                    "type": "string",
                    "enum": ["bought", "passed"],
                    "description": "Whether the user bought or passed on the item"
                },
                "reason": {
                    "type": "string",
                    "description": "Why they made this decision (optional but useful for learning)"
                }
            },
            "required": ["reasoning", "item_id", "decision"]
        }
    },
    {
        "name": "delete_considering_item",
        "description": "Remove an item from the considering list. Use when user says 'remove that', 'not interested anymore', or 'take it off the list'. Call get_considering_items first to find the item_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "item_id": {
                    "type": "string",
                    "description": "The considering item ID (from get_considering_items)"
                }
            },
            "required": ["reasoning", "item_id"]
        }
    },
    {
        "name": "update_considering_item",
        "description": "Update details of a considering item (name, category, price, notes). Use when user corrects info or adds context about a product.",
        "input_schema": {
            "type": "object",
            "properties": {
                **REASONING_FIELD,
                "item_id": {
                    "type": "string",
                    "description": "The considering item ID (from get_considering_items)"
                },
                "name": {
                    "type": "string",
                    "description": "Updated product name"
                },
                "category": {
                    "type": "string",
                    "description": "Updated category"
                },
                "price": {
                    "type": "number",
                    "description": "Updated price in dollars"
                },
                "notes": {
                    "type": "string",
                    "description": "Notes about the item (e.g., 'runs small', 'wait for sale')"
                }
            },
            "required": ["reasoning", "item_id"]
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
