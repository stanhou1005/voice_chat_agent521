"""
TTL cleanup: remove orphaned checkpoints older than 14 days.
Session metadata TTL is handled by LangGraph Store (TTLConfig).
Runs daily at 3:00 AM via APScheduler.
"""

from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import DATABASE_URL

TTL_DAYS = 14


async def cleanup_expired():
    """Delete expired checkpoints. Store handles session TTL automatically."""
    import asyncpg

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=TTL_DAYS)

        # Delete expired checkpoints
        await conn.execute(
            "DELETE FROM checkpoints WHERE created_at < $1",
            cutoff,
        )
        await conn.execute(
            "DELETE FROM checkpoint_blobs WHERE thread_id NOT IN (SELECT thread_id FROM checkpoints)"
        )
        await conn.execute(
            "DELETE FROM checkpoint_writes WHERE thread_id NOT IN (SELECT thread_id FROM checkpoints)"
        )
    finally:
        await conn.close()


def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cleanup_expired, "cron", hour=3, minute=0)
    scheduler.start()
    return scheduler
