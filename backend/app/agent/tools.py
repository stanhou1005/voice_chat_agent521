"""
Agent state (Plan-Execute-Replan) and tools.
"""

from datetime import datetime, timezone
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.tools import tool

from app.services.tavily import get_tavily_tool


class AgentState(TypedDict):
    """Plan-Execute-Replan state. Checkpointed to PostgreSQL.

    - messages: conversation history (add_messages reducer, for short-term memory)
    - input: current user question
    - plan: ordered steps to execute
    - past_steps: (step_description, result) — accumulates within a turn, reset between turns
    - response: final answer set by replan when work is done
    """
    messages: Annotated[list, add_messages]
    input: str
    plan: list[str]
    past_steps: list[tuple]       # plain list — reset between turns
    response: str


# ── Tools ───────────────────────────────────────────────

@tool
def tavily_search_tool(query: str) -> str:
    """Search the web for current information. Use this for facts, news, or any
    up-to-date information you don't know."""
    tool = get_tavily_tool()
    result = tool.invoke({"query": query})
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        return "\n\n".join(str(r) for r in result[:3])
    return str(result)


@tool
def get_current_datetime() -> str:
    """Get the current date and time. Always call this first when the question
    involves 'latest', 'current', 'recent', or time-sensitive information."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d %H:%M:%S UTC")


TOOLS = [tavily_search_tool, get_current_datetime]
