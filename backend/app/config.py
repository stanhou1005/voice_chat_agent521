"""
Application configuration.
Loads from .env file (in CONFIG_DIR or backend/ directory), then environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env: Docker mounts config at /config, dev uses backend/
_config_dir = os.getenv("CONFIG_DIR", str(Path(__file__).resolve().parent.parent))
_env_path = Path(_config_dir) / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
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

# ── Auth ───────────────────────────────────────────────────
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "72"))

# ── Server ───────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
