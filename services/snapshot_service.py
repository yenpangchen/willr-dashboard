from __future__ import annotations

from typing import Any

from config.settings import settings
from db.engine import SessionLocal
from repository.snapshot_repo import SnapshotRepository
from willr_core import run_snapshot


def _sort_snapshot(rows: list[dict[str, Any]], sort_key: str) -> list[dict[str, Any]]:
    if sort_key == "williams_r":
        return sorted(
            rows,
            key=lambda r: (r["williams_r"] is None, r["williams_r"] if r["williams_r"] is not None else 999, r["symbol"]),
        )
    if sort_key == "williams_r_desc":
        return sorted(
            rows,
            key=lambda r: (r["williams_r"] is None, -(r["williams_r"] if r["williams_r"] is not None else -999), r["symbol"]),
        )
    return sorted(rows, key=lambda r: r["symbol"])


def get_snapshot(period: int, sort_key: str, recent: int, workers: int) -> dict[str, Any]:
    snap: list[dict[str, Any]] = []
    hist: list[dict[str, Any]] = []
    db_ok = True
    try:
        with SessionLocal() as db:
            repo = SnapshotRepository(db)
            snap = repo.latest_snapshot(period=period, universe="tw50")
            hist = repo.recent_history(period=period, recent=recent, universe="tw50") if snap else []
    except Exception:
        db_ok = False

    if snap:
        return {
            "universe": "tw50",
            "period": period,
            "sort": sort_key,
            "recent_sessions": recent,
            "snapshot": _sort_snapshot(snap, sort_key),
            "history": hist,
            "source": "db",
        }
    if not settings.allow_live_fallback:
        return {
            "universe": "tw50",
            "period": period,
            "sort": sort_key,
            "recent_sessions": recent,
            "snapshot": [],
            "history": [],
            "source": "db_unavailable" if not db_ok else "db_empty",
        }

    payload = run_snapshot(
        universe="tw50",
        period=period,
        sort_key=sort_key,  # type: ignore[arg-type]
        recent=recent,
        workers=workers,
    )
    payload["source"] = "live_fallback"
    return payload


def get_meta(period: int) -> dict[str, Any]:
    try:
        with SessionLocal() as db:
            repo = SnapshotRepository(db)
            return {
                "universe": "tw50",
                "period": period,
                "symbol_count": repo.symbol_count("tw50"),
                "latest_trade_date": repo.latest_trade_date(period=period, universe="tw50"),
                "latest_job_run": repo.latest_job_run("daily_ingest"),
                "source": "db",
            }
    except Exception as e:
        raise ValueError(f"db_unavailable: {e}") from e

