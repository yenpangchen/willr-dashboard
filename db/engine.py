from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import settings


def _database_url() -> str:
    url = settings.database_url.strip()
    if url:
        return url
    raise RuntimeError("DATABASE_URL is required (Postgres only mode).")


engine = create_engine(_database_url(), future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

