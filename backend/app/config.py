import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend directory (parent of app/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_DIR / ".env")

_DEFAULT_SQLITE_URL = f"sqlite:///{(_BACKEND_DIR / 'linkplease.db').as_posix()}"


class Settings:
    """Application settings loaded from environment variables."""

    app_env: str
    database_url: str
    pseudogram_api_key: str | None
    pseudogram_base_url: str
    dm_worker_max_attempts: int
    dm_worker_retry_base_seconds: int
    dm_worker_sending_lease_seconds: int

    def __init__(self) -> None:
        self.app_env = os.getenv("APP_ENV", "development")

        configured_url = os.getenv("DATABASE_URL", "").strip()
        self.database_url = configured_url or _DEFAULT_SQLITE_URL

        self.pseudogram_api_key = os.getenv("PSEUDOGRAM_API_KEY") or None
        self.pseudogram_base_url = os.getenv(
            "PSEUDOGRAM_BASE_URL",
            "https://pseudogram-api.onrender.com",
        )
        self.dm_worker_max_attempts = int(os.getenv("DM_WORKER_MAX_ATTEMPTS", "5"))
        self.dm_worker_retry_base_seconds = int(
            os.getenv("DM_WORKER_RETRY_BASE_SECONDS", "30"),
        )
        self.dm_worker_sending_lease_seconds = int(
            os.getenv("DM_WORKER_SENDING_LEASE_SECONDS", "120"),
        )

        # Frontend allowed origin for production (optional). If unset, production origin
        # must be configured via FRONTEND_URL environment variable on deploy.
        # Local development origins are allowed separately in main.py.
        self.frontend_url = os.getenv("FRONTEND_URL", "").strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
