"""
Centralized LangGraph checkpointer + store management.
Singleton pattern — initialized once at app startup, shared across all requests.

- Checkpointer (AsyncPostgresSaver): short-term memory, conversation history
- Store (AsyncPostgresStore): long-term memory, session metadata list
"""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore

from app.config import DATABASE_URL

# ── Checkpointer ──────────────────────────────────────

_checkpointer: AsyncPostgresSaver | None = None
_cp_context: object | None = None


async def init_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer, _cp_context
    _cp_context = AsyncPostgresSaver.from_conn_string(DATABASE_URL)
    _checkpointer = await _cp_context.__aenter__()
    await _checkpointer.setup()
    return _checkpointer


def get_checkpointer() -> AsyncPostgresSaver:
    if _checkpointer is None:
        raise RuntimeError("Checkpointer not initialized.")
    return _checkpointer


async def close_checkpointer():
    global _checkpointer, _cp_context
    if _cp_context is not None:
        await _cp_context.__aexit__(None, None, None)
    _checkpointer = None
    _cp_context = None


# ── Store (Long-term memory) ──────────────────────────

_store: AsyncPostgresStore | None = None
_st_context: object | None = None

STORE_NAMESPACE = ("sessions",)
STORE_TTL_SECONDS = 14 * 86400  # 14 days


async def init_store() -> AsyncPostgresStore:
    """Initialize LangGraph Store for session metadata (long-term memory)."""
    global _store, _st_context
    _st_context = AsyncPostgresStore.from_conn_string(
        DATABASE_URL,
        ttl={"default_ttl": STORE_TTL_SECONDS, "refresh_on_read": True},
    )
    _store = await _st_context.__aenter__()
    await _store.setup()
    return _store


def get_store() -> AsyncPostgresStore:
    if _store is None:
        raise RuntimeError("Store not initialized.")
    return _store


async def close_store():
    global _store, _st_context
    if _st_context is not None:
        await _st_context.__aexit__(None, None, None)
    _store = None
    _st_context = None
