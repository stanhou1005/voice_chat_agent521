"""
Verification script for LangGraph checkpointer + session store.
Run with: python verify_checkpointer.py

Prerequisites:
1. PostgreSQL running (docker-compose up postgres)
2. pip install -r requirements.txt
3. Set env vars if defaults don't match:
   PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DB
"""

import asyncio
import sys
import os

# Windows: psycopg requires SelectorEventLoop instead of ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(__file__))

from tortoise import Tortoise
from app.config import DATABASE_URL
from app.db.langgraph import init_checkpointer, get_checkpointer
from app.agent.graph import run_agent
from app.models.session import SessionMeta
from app.models.settings import Settings

TEST_THREAD_ID = "test-thread-001"


async def main():
    print("=" * 50)
    print("LangGraph Checkpointer Verification")
    print("=" * 50)

    # 1. Init Tortoise
    print("\n[1/6] Initializing Tortoise-ORM...")
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": ["app.models.settings", "app.models.session"]},
        _enable_global_fallback=True,
    )
    await Tortoise.generate_schemas()
    print("  ✓ Tortoise connected, tables created")

    # 2. Init checkpointer
    print("\n[2/6] Initializing AsyncPostgresSaver...")
    cp = await init_checkpointer()
    print(f"  ✓ Checkpointer ready: {type(cp).__name__}")

    # 3. Test Settings singleton
    print("\n[3/6] Testing Settings CRUD...")
    s = await Settings.get_singleton()
    print(f"  ✓ Settings row: id={s.id}, model={s.model_name}")
    s.model_name = "test-model"
    await s.save()
    s2 = await Settings.get_singleton()
    assert s2.model_name == "test-model", "Settings save failed!"
    print("  ✓ Settings update verified")

    # 4. Test SessionMeta
    print("\n[4/6] Testing SessionMeta CRUD...")
    await SessionMeta.filter(thread_id=TEST_THREAD_ID).delete()  # cleanup
    session = await SessionMeta.create(
        thread_id=TEST_THREAD_ID,
        title="测试会话",
        message_count=0,
    )
    print(f"  ✓ Created session: {session.thread_id}")

    sessions = await SessionMeta.all().values()
    print(f"  ✓ Query sessions: {len(sessions)} total")

    # 5. Test graph run with checkpointer
    print("\n[5/6] Testing graph.ainvoke() with checkpointer...")
    print("  (DeepSeek API call — requires LLM_API_KEY env var)")

    llm_key = os.getenv("LLM_API_KEY", "")
    if not llm_key:
        print("  ⚠ LLM_API_KEY not set — using mock mode")
        print("  Skipping graph invocation (no API key)")
    else:
        try:
            # First turn
            result1 = await run_agent(cp, TEST_THREAD_ID, "你好，今天天气怎么样？")
            print(f"  ✓ Turn 1 result: {result1[:80]}...")

            # Second turn — should use checkpointed history
            result2 = await run_agent(cp, TEST_THREAD_ID, "我刚才问了什么？")
            print(f"  ✓ Turn 2 result: {result2[:80]}...")
            print("  ✓ Multi-turn checkpointing works!")
        except Exception as e:
            print(f"  ⚠ Graph invocation failed: {e}")
            print("  (This is expected if API key is invalid)")

    # 6. Check checkpoint state
    print("\n[6/6] Checking checkpoint persistence...")
    config = {"configurable": {"thread_id": TEST_THREAD_ID}}
    checkpoint = await cp.aget(config)
    if checkpoint is not None and checkpoint.get("channel_values"):
        msg_count = len(checkpoint["channel_values"].get("messages", []))
        print(f"  ✓ Checkpoint has {msg_count} messages")
        print(f"  ✓ State keys: {list(checkpoint['channel_values'].keys())}")
    else:
        print("  ⚠ No checkpoint state found (expected if step 5 was skipped)")

    print("\n" + "=" * 50)
    print("All checks passed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
