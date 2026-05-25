"""
LangGraph nodes: plan_step, execute_step, replan_step.
Matches demo graph_agent_workflow.py pattern exactly.
"""

from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent
from pydantic import BaseModel, Field

from app.agent.tools import AgentState, TOOLS
from app.agent.prompts import PLANNER_PROMPT, EXECUTOR_PROMPT, REPLANNER_PROMPT
from app.agent.status import emit
from app.utils.cancellation import get_cancel_event
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


# ── Pydantic models (same as demo) ────────────────────

class Plan(BaseModel):
    """未来要执行的计划"""
    steps: list[str] = Field(description="需要执行的不同步骤，应该按顺序排列")


class Act(BaseModel):
    """要执行的行为"""
    response: str | None = Field(default=None, description="如果要回应用户，填写此字段")
    next_steps: list[str] | None = Field(default=None, description="如果需要继续执行，填写剩余的计划步骤")

    def get_action_type(self) -> str:
        if self.response is not None:
            return "response"
        elif self.next_steps is not None:
            return "plan"
        return "unknown"


# ── LLM (two tiers, same as demo) ──────────────────────

def _get_pro_llm(temperature: float = 0) -> ChatDeepSeek:
    return ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=temperature,
        extra_body={"thinking": {"type": "disabled"}},
    )


def _get_flash_llm(temperature: float = 0) -> ChatDeepSeek:
    return ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=temperature,
        extra_body={"thinking": {"type": "disabled"}},
    )


# Structured output, cached
_planner = None
_replanner = None
_agent = None


def _get_planner():
    global _planner
    if _planner is None:
        _planner = PLANNER_PROMPT | _get_pro_llm(0).with_structured_output(Plan)
    return _planner


def _get_replanner():
    global _replanner
    if _replanner is None:
        _replanner = REPLANNER_PROMPT | _get_pro_llm(0).with_structured_output(Act)
    return _replanner


def _get_agent():
    global _agent
    if _agent is None:
        _agent = create_agent(model=_get_flash_llm(0), tools=TOOLS, system_prompt=EXECUTOR_PROMPT)
    return _agent


class CancelledError(Exception):
    pass


def _check_cancelled(config: RunnableConfig):
    thread_id = config.get("configurable", {}).get("thread_id", "")
    event = get_cancel_event(thread_id)
    if event and event.is_set():
        raise CancelledError("User cancelled")


def _get_conversation_history(state: AgentState, max_turns: int = 10) -> str:
    """Extract recent conversation for context."""
    messages = state.get("messages", [])
    if len(messages) <= 1:
        return ""
    recent = messages[-(max_turns * 2):]
    lines = []
    for msg in recent:
        if isinstance(msg, HumanMessage):
            lines.append(f"用户: {msg.content}")
        elif isinstance(msg, AIMessage):
            lines.append(f"助手: {msg.content}")
        elif isinstance(msg, dict):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("user", "human"):
                lines.append(f"用户: {content}")
            elif role in ("ai", "assistant"):
                lines.append(f"助手: {content}")
    return "\n".join(lines) if lines else ""


# ── Nodes (same names & logic as demo) ─────────────────

async def plan_step(state: AgentState, config: RunnableConfig) -> dict:
    """Decompose user's question into ordered steps. (demo: plan_step)"""
    _check_cancelled(config)

    thread_id = config.get("configurable", {}).get("thread_id", "")
    await emit(thread_id, "plan", "正在分析问题并制定计划…")

    user_input = state.get("input", "") or state.get("plan", "")  # fallback

    # Include conversation history for context-aware planning
    history = _get_conversation_history(state)
    planner = _get_planner()

    try:
        plan = await planner.ainvoke({"messages": [
            ("user", user_input),
        ]})
        steps = plan.steps
    except Exception:
        # Fallback
        llm = _get_pro_llm(0)
        resp = await llm.ainvoke([{"role": "user", "content": f"将以下问题拆解为1-5个步骤: {user_input}"}])
        steps = [s.strip() for s in resp.content.split("\n") if s.strip()][:5]
        if not steps:
            steps = [user_input]

    return {"input": user_input, "plan": steps}


async def execute_step(state: AgentState, config: RunnableConfig) -> dict:
    """Execute the FIRST step of the plan using tool-equipped agent. (demo: execute_step)"""
    _check_cancelled(config)

    thread_id = config.get("configurable", {}).get("thread_id", "")
    plan = state.get("plan", [])
    if not plan:
        return {}

    task = plan[0]
    await emit(thread_id, "search", f"正在执行: {task[:50]}")

    plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
    task_formatted = f"对于以下计划：\n{plan_str}\n你的任务是执行第1步，{task}。"

    agent = _get_agent()
    agent_response = await agent.ainvoke({"messages": [("user", task_formatted)]})

    result_content = agent_response["messages"][-1].content
    existing = state.get("past_steps", [])
    return {"past_steps": existing + [(task, result_content)]}


async def replan_step(state: AgentState, config: RunnableConfig) -> dict:
    """Evaluate progress, decide: continue or finish. (demo: replan_step)"""
    _check_cancelled(config)

    thread_id = config.get("configurable", {}).get("thread_id", "")
    await emit(thread_id, "replan", "正在评估执行结果…")

    plan = state.get("plan", [])
    past_steps = state.get("past_steps", [])

    # If all steps executed, done
    if len(past_steps) >= len(plan):
        past_str = "\n".join(f"- {t}: {r[:200]}" for t, r in past_steps)
        llm = _get_pro_llm(0.7)
        history = _get_conversation_history(state)
        resp = await llm.ainvoke([
            {"role": "system", "content": "根据以下执行结果和对话历史，生成最终答案。简洁、口语化、适合语音播放。用用户提问的语言回答。"},
            {"role": "user", "content": f"对话历史:\n{history}\n\n执行结果:\n{past_str}\n\n用户问题: {state.get('input', '')}"},
        ])
        return {"response": resp.content, "messages": [AIMessage(content=resp.content)]}

    # Build replanner prompt
    past_str = "\n".join(f"- {t}: {r[:300]}" for t, r in past_steps) if past_steps else "(无)"

    replanner = _get_replanner()
    try:
        act = await replanner.ainvoke({
            "input": state.get("input", ""),
            "plan": "\n".join(f"- {s}" for s in plan),
            "past_steps": past_str,
        })
    except Exception:
        # Fallback: continue with remaining
        remaining = plan[len(past_steps):]
        return {"plan": remaining}

    if act.get_action_type() == "response":
        return {"response": act.response, "messages": [AIMessage(content=act.response)]}
    elif act.get_action_type() == "plan":
        return {"plan": act.next_steps}
    else:
        remaining = plan[len(past_steps):]
        return {"plan": remaining}
