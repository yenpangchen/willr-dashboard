"""FastAPI server: Williams %R dashboard API."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# project root (parent of api/)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import settings  # noqa: E402
from db.init_db import init_db  # noqa: E402
from services.snapshot_service import get_meta, get_snapshot  # noqa: E402
from willr_core import SortKey  # noqa: E402

STATIC_DIR = Path(os.environ.get("WILLR_STATIC_DIR", str(settings.static_dir))).resolve()

app = FastAPI(title=settings.app_name, version=settings.app_version)
DB_READY = init_db()

_cors_env = os.environ.get("WILLR_CORS_ORIGINS", settings.cors_origins).strip()
if _cors_env:
    _cors_list = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    _cors_list = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    db_url = settings.database_url.strip()
    return {
        "ok": True,
        "db_ready": DB_READY,
        "db_backend": settings.db_backend,
        "is_vercel": settings.is_vercel,
        "database_url_set": bool(db_url),
    }


@app.get("/api/snapshot")
def snapshot(
    period: int = Query(settings.default_period, ge=2, le=120),
    sort: SortKey = Query("symbol"),
    recent: int = Query(settings.default_recent, ge=0, le=250, description="Trading days of history per symbol"),
    workers: int = Query(10, ge=1, le=32),
) -> dict:
    try:
        return get_snapshot(period=period, sort_key=sort, recent=recent, workers=workers)
    except ValueError as e:
        detail = str(e)
        if detail.startswith("db_unavailable:"):
            raise HTTPException(status_code=503, detail=detail) from e
        raise HTTPException(status_code=400, detail=detail) from e


@app.get("/api/meta")
def meta(
    period: int = Query(settings.default_period, ge=2, le=120),
) -> dict:
    try:
        return get_meta(period=period)
    except ValueError as e:
        detail = str(e)
        if detail.startswith("db_unavailable:"):
            raise HTTPException(status_code=503, detail=detail) from e
        raise HTTPException(status_code=400, detail=detail) from e


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="spa")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
