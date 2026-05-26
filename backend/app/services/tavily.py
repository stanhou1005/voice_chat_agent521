"""
Tavily Search API wrapper — uses langchain_tavily for LangGraph tool compatibility.
Supports multiple API keys (comma-separated) with random selection to spread quota.
"""

import random
from langchain_tavily import TavilySearch
from app.models.settings import Settings


def _parse_keys(raw: str) -> list[str]:
    """Parse comma/whitespace separated API keys, filter empties."""
    if not raw:
        return []
    return [k.strip() for k in raw.replace("\n", ",").split(",") if k.strip()]


def _pick_key() -> str:
    return random.choice(_keys) if _keys else ""


_keys: list[str] = []


async def reload_keys():
    """Reload Tavily API keys from DB settings. Call on startup and after settings change."""
    global _keys
    try:
        settings = await Settings.get_singleton()
        _keys = _parse_keys(settings.tavily_key)
    except Exception:
        _keys = []


def get_tavily_tool() -> TavilySearch:
    """Get a TavilySearch instance with a randomly chosen API key."""
    kwargs: dict = {
        "max_results": 3,
        "search_depth": "advanced",
    }
    key = _pick_key()
    if key:
        kwargs["tavily_api_key"] = key
    return TavilySearch(**kwargs)


async def tavily_search(query: str) -> dict:
    """Execute a Tavily search query. Returns normalized dict."""
    tool = get_tavily_tool()
    result = tool.invoke({"query": query})
    if isinstance(result, str):
        return {"results": [{"content": result, "snippet": result[:200]}]}
    if isinstance(result, list):
        return {"results": result}
    return result if isinstance(result, dict) else {"results": []}
