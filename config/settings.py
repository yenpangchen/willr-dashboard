from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "WillR Dashboard API"
    app_version: str = "2.0.0"

    data_dir: Path = Path("data")
    sqlite_path: Path = Path("data/willr.db")

    # Frontend static assets (for FastAPI static mount)
    static_dir: Path = Path("api/static")

    # CORS
    cors_origins: str = (
        "http://127.0.0.1:5173,http://localhost:5173,"
        "http://127.0.0.1:4173,http://localhost:4173,"
        "http://127.0.0.1:8000,http://localhost:8000"
    )

    # Runtime behavior
    allow_live_fallback: bool = True
    default_period: int = 14
    default_recent: int = 60

    # Redis (phase C)
    redis_url: str = "redis://localhost:6379/0"
    cache_enabled: bool = True
    snapshot_cache_ttl_seconds: int = 180
    cache_key_prefix: str = "willr"

    # Ingestion resiliency (phase C)
    ingest_fetch_retries: int = 3
    ingest_retry_backoff_seconds: float = 0.8

    # Alerting (phase C)
    alert_webhook_url: str = ""

    @property
    def is_vercel(self) -> bool:
        return os.environ.get("VERCEL") == "1"

    @property
    def effective_sqlite_path(self) -> Path:
        # Vercel runtime filesystem is read-only except /tmp.
        if self.is_vercel:
            return Path("/tmp/willr.db")
        return self.sqlite_path


settings = Settings()

