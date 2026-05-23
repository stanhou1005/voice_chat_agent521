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

MODELS = ["app.models.settings", "app.models.session"]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": MODELS},
        _enable_global_fallback=True,
    )
    await Tortoise.generate_schemas()
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

app.include_router(ws_router)
app.include_router(rest_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
