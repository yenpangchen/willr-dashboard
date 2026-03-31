#!/usr/bin/env python3
from __future__ import annotations

import logging
import time
from datetime import date
from datetime import datetime

import pandas as pd

from config.settings import settings
from db.engine import SessionLocal
from db.init_db import init_db
from repository.snapshot_repo import SnapshotRepository
from services.cache_service import invalidate_snapshot_cache
from services.observability import emit_alert, get_logger, log_event
from willr_core import fetch_history, fetch_yahoo_names, load_symbols, williams_percent_r

logger = get_logger(__name__)


def _fetch_history_with_retry(sym: str, lookback_days: int) -> pd.DataFrame:
    retries = max(1, settings.ingest_fetch_retries)
    backoff = max(0.1, settings.ingest_retry_backoff_seconds)
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return fetch_history(sym, lookback_days)
        except Exception as e:
            last_err = e
            log_event(
                logger,
                logging.WARNING,
                "ingest_fetch_retry",
                symbol=sym,
                attempt=attempt,
                retries=retries,
                error=f"{type(e).__name__}: {e}",
            )
            if attempt < retries:
                time.sleep(backoff * attempt)
    if last_err:
        raise last_err
    return pd.DataFrame()


def run(period: int = 14, lookback_days: int = 240) -> None:
    started_at = datetime.utcnow()
    log_event(logger, logging.INFO, "daily_ingest_start", period=period, lookback_days=lookback_days)
    init_db()
    with SessionLocal() as db:
        repo = SnapshotRepository(db)
        try:
            symbols = load_symbols(settings.data_dir.parent / "tw50_constituents.txt")
            name_map = fetch_yahoo_names(symbols)

            symbol_rows = [{"symbol": s, "name": name_map.get(s, ""), "universe": "tw50"} for s in symbols]
            price_rows: list[dict] = []
            wr_rows: list[dict] = []
            failed_symbols: list[str] = []

            for sym in symbols:
                try:
                    hist = _fetch_history_with_retry(sym, lookback_days)
                except Exception:
                    failed_symbols.append(sym)
                    continue
                if hist.empty:
                    continue
                hist = hist.copy()
                hist["WilliamsR"] = williams_percent_r(hist, period)
                for idx, r in hist.iterrows():
                    d = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
                    price_rows.append(
                        {
                            "symbol": sym,
                            "trade_date": d,
                            "open": float(r["Open"]) if pd.notna(r["Open"]) else None,
                            "high": float(r["High"]) if pd.notna(r["High"]) else None,
                            "low": float(r["Low"]) if pd.notna(r["Low"]) else None,
                            "close": float(r["Close"]) if pd.notna(r["Close"]) else None,
                            "volume": int(r["Volume"]) if pd.notna(r["Volume"]) else None,
                        }
                    )
                    wr_rows.append(
                        {
                            "symbol": sym,
                            "trade_date": d,
                            "period": period,
                            "value": float(r["WilliamsR"]) if pd.notna(r["WilliamsR"]) else None,
                        }
                    )

            repo.upsert_symbols(symbol_rows)
            repo.upsert_prices(price_rows)
            repo.upsert_williams(wr_rows)
            evicted = invalidate_snapshot_cache()
            finished_at = datetime.utcnow()
            elapsed_ms = int((finished_at - started_at).total_seconds() * 1000)
            repo.add_job_run(
                "daily_ingest",
                "success",
                (
                    f"symbols={len(symbol_rows)} "
                    f"prices={len(price_rows)} "
                    f"wr={len(wr_rows)} "
                    f"failed_symbols={len(failed_symbols)} "
                    f"cache_evicted={evicted} "
                    f"elapsed_ms={elapsed_ms}"
                ),
                started_at=started_at,
                finished_at=finished_at,
            )
            log_event(
                logger,
                logging.INFO,
                "daily_ingest_success",
                symbols=len(symbol_rows),
                prices=len(price_rows),
                wr=len(wr_rows),
                failed_symbols=len(failed_symbols),
                cache_evicted=evicted,
                elapsed_ms=elapsed_ms,
            )
            if failed_symbols:
                emit_alert(
                    "daily_ingest_partial_failure",
                    failed_symbols=failed_symbols[:15],
                    failed_count=len(failed_symbols),
                    elapsed_ms=elapsed_ms,
                )
        except Exception as e:
            finished_at = datetime.utcnow()
            elapsed_ms = int((finished_at - started_at).total_seconds() * 1000)
            repo.add_job_run(
                "daily_ingest",
                "failed",
                f"error={type(e).__name__}: {e}; elapsed_ms={elapsed_ms}",
                started_at=started_at,
                finished_at=finished_at,
            )
            log_event(
                logger,
                logging.ERROR,
                "daily_ingest_failed",
                error=f"{type(e).__name__}: {e}",
                elapsed_ms=elapsed_ms,
            )
            emit_alert("daily_ingest_failed", error=f"{type(e).__name__}: {e}", elapsed_ms=elapsed_ms)
            raise


if __name__ == "__main__":
    run()

