"""
REST API endpoints: sessions list, message history, settings.
Sessions stored in LangGraph Store (long-term memory).
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException

from app.models.settings import Settings
from app.core.auth import get_current_user
from app.db.langgraph import get_checkpointer, get_store, STORE_NAMESPACE, STORE_TTL_SECONDS

router = APIRouter(prefix="/api")


# ─── Sessions (LangGraph Store) ────────────────────────────

@router.get("/sessions")
async def list_sessions(limit: int = 50, offset: int = 0, user: dict = Depends(get_current_user)):
    """List historical sessions from LangGraph Store, sorted by last active time."""
    store = get_store()
    items = await store.asearch(STORE_NAMESPACE, limit=limit + offset, offset=0)
    current_user_id = user.get("sub", "")

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=STORE_TTL_SECONDS)
    sessions = []
    for item in items:
        v = item.value
        # Filter by current user
        if v.get("user_id") and str(v.get("user_id")) != str(current_user_id):
            continue
        created = v.get("created_at", "")
        if created:
            try:
                ct = datetime.fromisoformat(created)
                if ct < cutoff:
                    continue
            except (ValueError, TypeError):
                pass
        sessions.append({
            "thread_id": v.get("thread_id", item.key),
            "title": v.get("title", "新会话"),
            "created_at": created,
            "last_active_at": v.get("last_active_at", ""),
            "message_count": v.get("message_count", 0),
        })

    sessions.sort(key=lambda s: s["last_active_at"], reverse=True)
    sessions = sessions[offset:offset + limit]

    return {"sessions": sessions, "total": len(sessions)}


async def _check_session_owner(session_id: str, user_id: str):
    """Verify the session belongs to user_id. Raises 403 if not."""
    store = get_store()
    item = await store.aget(STORE_NAMESPACE, session_id)
    if item and item.value.get("user_id") and str(item.value.get("user_id")) != str(user_id):
        raise HTTPException(status_code=403, detail="Access denied")


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, user: dict = Depends(get_current_user)):
    """Get message history from LangGraph checkpointer."""
    try:
        await _check_session_owner(session_id, user.get("sub", ""))
        checkpointer = get_checkpointer()
        config = {"configurable": {"thread_id": session_id}}
        checkpoint = await checkpointer.aget(config)

        if checkpoint is None or checkpoint.get("channel_values") is None:
            return {"session_id": session_id, "messages": []}

        messages = checkpoint["channel_values"].get("messages", [])
        serialized = []
        for msg in messages:
            if hasattr(msg, "type") and hasattr(msg, "content"):
                role = msg.type
                if role == "human":
                    role = "user"
                elif role == "ai":
                    role = "assistant"
                serialized.append({"role": role, "text": msg.content})
            elif isinstance(msg, dict):
                role = msg.get("role", "")
                if role == "human":
                    role = "user"
                elif role == "ai":
                    role = "assistant"
                serialized.append({"role": role, "text": msg.get("content", "")})

        return {"session_id": session_id, "messages": serialized}

    except RuntimeError:
        raise HTTPException(status_code=503, detail="Checkpointer not ready")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user: dict = Depends(get_current_user)):
    """Delete a session: remove from Store and its checkpoint data."""
    await _check_session_owner(session_id, user.get("sub", ""))
    store = get_store()
    # 1. Remove from Store
    await store.adelete(STORE_NAMESPACE, session_id)

    # 2. Delete checkpoint data
    from tortoise import connections
    conn = connections.get("default")
    await conn.execute_query("DELETE FROM checkpoint_blobs WHERE thread_id = $1", [session_id])
    await conn.execute_query("DELETE FROM checkpoint_writes WHERE thread_id = $1", [session_id])
    await conn.execute_query("DELETE FROM checkpoints WHERE thread_id = $1", [session_id])

    return {"status": "ok"}


# ─── Settings ───────────────────────────────────────────────

@router.get("/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    s = await Settings.get_singleton()
    return {
        "model_name": s.model_name,
        "base_url": s.base_url,
        "api_key": s.api_key,
        "tavily_key": s.tavily_key,
        "proxy_url": s.proxy_url,
    }


@router.put("/settings")
async def update_settings(data: dict, user: dict = Depends(get_current_user)):
    s = await Settings.get_singleton()
    for field in ("model_name", "base_url", "api_key", "tavily_key", "proxy_url"):
        if field in data:
            setattr(s, field, data[field])
    await s.save()
    return {"status": "ok"}
