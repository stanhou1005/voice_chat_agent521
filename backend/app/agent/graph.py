"""
LangGraph workflow: START → plan → execute → replan → should_continue.
Matches demo graph_agent_workflow.py structure exactly.
"""

from typing import Any, Callable, Awaitable, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.nodes import plan_step, execute_step, replan_step
from app.agent.tools import AgentState
from app.agent.status import set_callback, clear_callback

_compiled_cache: dict[int, Any] = {}
MAX_ITERATIONS = 20


def build_graph() -> StateGraph:
    """Same structure as demo."""
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", plan_step)
    workflow.add_node("agent", execute_step)
    workflow.add_node("replan", replan_step)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "agent")
    workflow.add_edge("agent", "replan")

    workflow.add_conditional_edges(
        "replan",
        _should_end,
        {"agent": "agent", "__end__": END},
    )

    return workflow


def _should_end(state: AgentState) -> Literal["agent", "__end__"]:
    """Check if the replanner set a final response. (demo: should_end)"""
    if state.get("response"):
        return "__end__"
    if len(state.get("past_steps", [])) >= MAX_ITERATIONS:
        return "__end__"
    return "agent"


def get_compiled_graph(checkpointer: AsyncPostgresSaver):
    cid = id(checkpointer)
    if cid not in _compiled_cache:
        graph = build_graph()
        _compiled_cache[cid] = graph.compile(checkpointer=checkpointer)
    return _compiled_cache[cid]


async def run_agent(
    checkpointer: AsyncPostgresSaver,
    thread_id: str,
    user_input: str,
    on_status: Callable[[str, str], Awaitable[None]] | None = None,
) -> str:
    """
    Execute the Plan-Execute-Replan workflow for one user turn.
    Returns the final response text.
    """
    compiled = get_compiled_graph(checkpointer)
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": MAX_ITERATIONS * 3,
    }

    if on_status:
        set_callback(thread_id, on_status)

    try:
        result = await compiled.ainvoke(
            {"input": user_input, "messages": [HumanMessage(content=user_input)], "past_steps": [], "response": ""},
            config,
        )

        # Extract answer from response field (set by replan) or last AI message
        response = result.get("response", "")
        if response:
            return response

        messages = result.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return msg.content
            if isinstance(msg, dict) and msg.get("role") in ("ai", "assistant"):
                return msg["content"]

        # Last resort: pull from past_steps
        past = result.get("past_steps", [])
        if past:
            return past[-1][1][:500]

        return "抱歉，我无法回答这个问题。"

    finally:
        if on_status:
            clear_callback(thread_id)
