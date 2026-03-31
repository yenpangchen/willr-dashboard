#!/usr/bin/env python3
from __future__ import annotations

from datetime import date
from datetime import datetime

import pandas as pd

from db.engine import SessionLocal
from db.init_db import init_db
from repository.snapshot_repo import SnapshotRepository
from willr_core import fetch_history, fetch_yahoo_names, load_symbols, williams_percent_r
from config.settings import settings


def run(period: int = 14, lookback_days: int = 240) -> None:
    started_at = datetime.utcnow()
    init_db()
    with SessionLocal() as db:
        repo = SnapshotRepository(db)
        try:
            symbols = load_symbols(settings.data_dir.parent / "tw50_constituents.txt")
            name_map = fetch_yahoo_names(symbols)

            symbol_rows = [{"symbol": s, "name": name_map.get(s, ""), "universe": "tw50"} for s in symbols]
            price_rows: list[dict] = []
            wr_rows: list[dict] = []

            for sym in symbols:
                hist = fetch_history(sym, lookback_days)
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
            finished_at = datetime.utcnow()
            elapsed_ms = int((finished_at - started_at).total_seconds() * 1000)
            repo.add_job_run(
                "daily_ingest",
                "success",
                (
                    f"symbols={len(symbol_rows)} "
                    f"prices={len(price_rows)} "
                    f"wr={len(wr_rows)} "
                    f"elapsed_ms={elapsed_ms}"
                ),
                started_at=started_at,
                finished_at=finished_at,
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
            raise


if __name__ == "__main__":
    run()

