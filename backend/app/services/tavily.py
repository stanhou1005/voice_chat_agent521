"""
Tavily Search API wrapper — uses langchain_tavily for LangGraph tool compatibility.
"""

from langchain_tavily import TavilySearch
from app.models.settings import Settings

_tool: TavilySearch | None = None


async def get_tavily_tool() -> TavilySearch:
    """Get or create TavilySearch tool instance from DB settings."""
    global _tool
    if _tool is not None:
        return _tool

    settings = await Settings.get_singleton()
    kwargs: dict = {
        "max_results": 3,
        "search_depth": "basic",
    }
    if settings.tavily_key:
        kwargs["tavily_api_key"] = settings.tavily_key
    if settings.proxy_url:
        kwargs["tavily_api_url"] = settings.proxy_url

    _tool = TavilySearch(**kwargs)
    return _tool


async def tavily_search(query: str) -> dict:
    """
    Execute a Tavily search query via langchain_tavily.
    Returns raw Tavily response dict.
    """
    tool = await get_tavily_tool()
    result = tool.invoke({"query": query})
    # result is a string (formatted search results) or list — normalize to dict
    if isinstance(result, str):
        return {"results": [{"content": result, "snippet": result[:200]}]}
    if isinstance(result, list):
        return {"results": result}
    return result if isinstance(result, dict) else {"results": []}
