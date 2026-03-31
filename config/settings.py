from __future__ import annotations

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


settings = Settings()

