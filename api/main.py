"""FastAPI server: Williams %R dashboard API."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# project root (parent of api/)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from willr_core import (  # noqa: E402
    SortKey,
    Universe,
    read_watchlist_entries,
    run_snapshot,
    search_tw_symbols,
    watchlist_add,
    watchlist_remove,
)

WATCHLIST_PATH = ROOT / "watchlist.txt"
IS_VERCEL = os.environ.get("VERCEL") == "1"
STATIC_DIR = Path(
    # Put static assets inside the backend bundle so Vercel Functions can read them.
    # Default location is `api/static/` (populated by scripts/vercel-build.sh).
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
    universe: Universe = Query("tw50"),
    period: int = Query(14, ge=2, le=120),
    sort: SortKey = Query("symbol"),
    recent: int = Query(30, ge=0, le=250, description="Trading days of history per symbol"),
    workers: int = Query(10, ge=1, le=32),
) -> dict:
    try:
        return run_snapshot(
            universe=universe,
            period=period,
            sort_key=sort,
            recent=recent,
            workers=workers,
            watchlist_path=WATCHLIST_PATH,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/search")
def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(12, ge=1, le=30),
) -> dict[str, Any]:
    return {"query": q.strip(), "results": search_tw_symbols(q, limit)}


@app.get("/api/watchlist")
def get_watchlist() -> dict[str, Any]:
    return {"entries": read_watchlist_entries(WATCHLIST_PATH)}


class WatchlistPatch(BaseModel):
    add: list[str] = Field(default_factory=list, max_length=50)
    remove: list[str] = Field(default_factory=list, max_length=50)


@app.post("/api/watchlist")
def patch_watchlist(body: WatchlistPatch) -> dict[str, Any]:
    if IS_VERCEL:
        # Vercel Functions run on a read-only filesystem (except /tmp),
        # so writing watchlist.txt would fail.
        raise HTTPException(
            status_code=501,
            detail="watchlist.txt is read-only on Vercel. Edit watchlist.txt in the repo and redeploy.",
        )
    if not body.add and not body.remove:
        raise HTTPException(status_code=400, detail="Provide `add` and/or `remove`")
    out: dict[str, Any] = {"entries": read_watchlist_entries(WATCHLIST_PATH)}
    if body.add:
        r = watchlist_add(WATCHLIST_PATH, body.add)
        out["added"] = r["added"]
        out["skipped"] = r["skipped"]
    if body.remove:
        r2 = watchlist_remove(WATCHLIST_PATH, body.remove)
        out["removed"] = r2["removed"]
    out["entries"] = read_watchlist_entries(WATCHLIST_PATH)
    return out


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="spa")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
