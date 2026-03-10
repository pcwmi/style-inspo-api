"""
Web Search Service - Search the web for fashion items and shopping recommendations.

Uses Brave Search API to find products, articles, and shopping results.
The agent uses this to find specific items it recommends but the user doesn't own yet.
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

MAX_RESULTS = 10


def web_search(query: str, count: int = MAX_RESULTS, freshness: Optional[str] = None) -> dict:
    """
    Search the web using Brave Search API.

    Args:
        query: Search query (e.g. "olive linen wide leg pants women under $100")
        count: Number of results to return (max 20)
        freshness: Optional freshness filter - "pd" (past day), "pw" (past week),
                   "pm" (past month), "py" (past year)

    Returns:
        {
            "query": str,
            "results": [{"title", "url", "description", "thumbnail"?, "price"?, "rating"?}],
            "result_count": int,
            "error": str or None
        }
    """
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return {
            "query": query,
            "results": [],
            "result_count": 0,
            "error": "BRAVE_SEARCH_API_KEY not configured",
        }

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }

    params = {
        "q": query,
        "count": min(count, 20),
        "text_decorations": False,
        "search_lang": "en",
    }

    if freshness:
        params["freshness"] = freshness

    try:
        resp = requests.get(BRAVE_SEARCH_URL, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        return {"query": query, "results": [], "result_count": 0, "error": "Search timed out"}
    except requests.RequestException as e:
        return {"query": query, "results": [], "result_count": 0, "error": f"Search failed: {e}"}

    results = []

    # Extract web results
    for item in data.get("web", {}).get("results", []):
        result = {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
        }

        # Include thumbnail if available
        thumbnail = item.get("thumbnail", {})
        if isinstance(thumbnail, dict) and thumbnail.get("src"):
            result["thumbnail"] = thumbnail["src"]

        # Include price/rating from extra snippets if present
        extras = item.get("extra_snippets", [])
        if extras:
            result["extra_info"] = extras[:2]  # Cap at 2 extra snippets

        results.append(result)

    logger.info(f"web_search: query='{query}' returned {len(results)} results")

    return {
        "query": query,
        "results": results[:count],
        "result_count": len(results),
        "error": None,
    }
