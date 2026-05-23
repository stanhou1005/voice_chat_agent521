"""
Verify LangGraph Store (long-term memory) migration.
Run after: python manage.py stop && python manage.py start
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.dirname(__file__))

from app.db.langgraph import init_store, get_store, close_store, STORE_NAMESPACE, STORE_TTL_SECONDS


async def main():
    # Initialize Store (normally done by FastAPI lifespan)
    store = await init_store()
    print("=" * 50)
    print("LangGraph Store Verification (Long-term Memory)")
    print("=" * 50)

    test_id = "store-test-001"

    # 1. Write session
    print("\n[1/5] Writing test session to Store...")
    value = {
        "thread_id": test_id,
        "title": "测试会话-Store",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_active_at": datetime.now(timezone.utc).isoformat(),
        "message_count": 4,
    }
    await store.aput(STORE_NAMESPACE, test_id, value)
    print(f"  ✓ Written: {value['title']}")

    # 2. Read back
    print("\n[2/5] Reading session back...")
    item = await store.aget(STORE_NAMESPACE, test_id)
    if item:
        print(f"  ✓ Found: {item.value['title']} (msg_count={item.value['message_count']})")
    else:
        print("  ✗ NOT FOUND!")
        return

    # 3. Update
    print("\n[3/5] Updating session...")
    value["message_count"] = 6
    value["last_active_at"] = datetime.now(timezone.utc).isoformat()
    await store.aput(STORE_NAMESPACE, test_id, value)
    item2 = await store.aget(STORE_NAMESPACE, test_id)
    assert item2.value["message_count"] == 6
    print("  ✓ Updated successfully")

    # 4. List sessions
    print("\n[4/5] Listing all sessions...")
    items = await store.asearch(STORE_NAMESPACE, limit=50)
    print(f"  ✓ Found {len(items)} session(s) in Store:")
    for it in items:
        v = it.value
        print(f"    - [{it.key}] {v.get('title', '?')[:40]} (msgs: {v.get('message_count', 0)})")

    # 5. Delete test session
    print("\n[5/5] Deleting test session...")
    await store.adelete(STORE_NAMESPACE, test_id)
    item3 = await store.aget(STORE_NAMESPACE, test_id)
    assert item3 is None
    print("  ✓ Deleted successfully")

    await close_store()

    print("\n" + "=" * 50)
    print(f"Store TTL: {STORE_TTL_SECONDS}s = {STORE_TTL_SECONDS // 86400} days")
    print("All checks passed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
