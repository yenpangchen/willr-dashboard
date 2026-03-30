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

from willr_core import SortKey, run_snapshot  # noqa: E402

WATCHLIST_PATH = ROOT / "watchlist.txt"
STATIC_DIR = Path(
    # Put static assets inside the backend bundle so Vercel Functions can read them.
    os.environ.get("WILLR_STATIC_DIR", str(ROOT / "api" / "static"))
).resolve()

app = FastAPI(title="WillR Dashboard API", version="1.0.0")

_cors_env = os.environ.get("WILLR_CORS_ORIGINS", "").strip()
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
    return {"ok": True}


@app.get("/api/snapshot")
def snapshot(
    period: int = Query(14, ge=2, le=120),
    sort: SortKey = Query("symbol"),
    recent: int = Query(60, ge=0, le=250, description="Trading days of history per symbol"),
    workers: int = Query(10, ge=1, le=32),
) -> dict:
    try:
        return run_snapshot(
            universe="tw50",
            period=period,
            sort_key=sort,
            recent=recent,
            workers=workers,
            watchlist_path=WATCHLIST_PATH,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="spa")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
