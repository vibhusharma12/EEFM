"""Runtime configuration, read from environment variables (optionally a local .env)."""
import os

from dotenv import load_dotenv

load_dotenv()

APP_VERSION = "0.3.0"

CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

# Seconds to wait for Yahoo Finance before giving up.
UPSTREAM_TIMEOUT: float = float(os.getenv("UPSTREAM_TIMEOUT", "10"))

# How long successful / failed lookups are served from memory.
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
NEGATIVE_CACHE_TTL_SECONDS: int = int(os.getenv("NEGATIVE_CACHE_TTL_SECONDS", "60"))

# Trained Random Forest models are saved here with Joblib (set PERSIST_MODELS=false to disable).
MODEL_DIR: str = os.getenv("MODEL_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "models"))
PERSIST_MODELS: bool = os.getenv("PERSIST_MODELS", "true").strip().lower() not in {"0", "false", "no"}
