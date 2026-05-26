"""
FastAPI application entry point.
"""

import sys
import asyncio
import logging

# Windows: psycopg requires SelectorEventLoop instead of ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("voice_chat").setLevel(logging.DEBUG)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise

from app.config import DATABASE_URL
from app.db.cleanup import start_scheduler
from app.db.langgraph import init_checkpointer, close_checkpointer, init_store, close_store
from app.api.ws import router as ws_router
from app.api.rest import router as rest_router
from app.api.auth import router as auth_router
from app.models.settings import Settings

MODELS = ["app.models.settings", "app.models.session", "app.models.user"]


async def _sync_config_to_db():
    """Sync .env values into the DB Settings singleton row on startup."""
    import os
    try:
        from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
        s = await Settings.get_singleton()
        changed = False
        for field, value in [
            ("model_name", DEEPSEEK_MODEL),
            ("base_url", DEEPSEEK_BASE_URL),
            ("api_key", DEEPSEEK_API_KEY),
            ("tavily_key", os.getenv("TAVILY_API_KEY", "")),
            ("proxy_url", os.getenv("PROXY_URL", "")),
        ]:
            if getattr(s, field) != value:
                setattr(s, field, value)
                changed = True
        if changed:
            await s.save()
            logging.getLogger("voice_chat").info("Synced .env config to DB Settings table")
    except Exception:
        logging.getLogger("voice_chat").warning("Failed to sync config to DB (table may not exist yet)")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": MODELS},
        _enable_global_fallback=True,
    )
    await Tortoise.generate_schemas()
    await _sync_config_to_db()
    # Load Tavily keys into memory (for multi-key support)
    from app.services.tavily import reload_keys
    await reload_keys()
    await init_checkpointer()
    await init_store()
    scheduler = start_scheduler()
    yield
    # Shutdown
    scheduler.shutdown()
    await close_checkpointer()
    await close_store()
    await Tortoise.close_connections()


app = FastAPI(title="Voice Chat Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(ws_router)
app.include_router(rest_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
