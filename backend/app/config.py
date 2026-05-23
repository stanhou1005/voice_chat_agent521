"""
Application configuration.
Loads from .env file, then environment variables, with fallback defaults.

Two API key lines:
  - LLM_API_KEY / LLM_BASE_URL → DeepSeek (LangGraph agent)
  - SILICONFLOW_API_KEY          → SiliconFlow (ASR + TTS)
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env from backend/ directory
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings(BaseModel):
    model_name: str = "deepseek-v4-pro"
    base_url: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    tavily_key: str = ""
    proxy_url: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model_name=os.getenv("LLM_MODEL_NAME", "deepseek-v4-pro"),
            base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
            api_key=os.getenv("LLM_API_KEY", ""),
            tavily_key=os.getenv("TAVILY_API_KEY", ""),
            proxy_url=os.getenv("PROXY_URL", ""),
        )


# ── Database ─────────────────────────────────────────────
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres")
PG_DB = os.getenv("PG_DB", "voice_chat")

DATABASE_URL = f"postgres://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"

# ── DeepSeek (LLM) ───────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("LLM_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("LLM_MODEL_NAME", "deepseek-v4-pro")

# ── SiliconFlow (ASR + TTS) ──────────────────────────────
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"

# ── Server ───────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
