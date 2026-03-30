"""Shared Williams %R data pipeline for CLI and API."""

from __future__ import annotations

import math
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent

SortKey = Literal["symbol", "williams_r", "williams_r_desc"]
Universe = Literal["watchlist", "tw50"]


def load_symbols(path: Path) -> list[str]:
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "." in line:
            out.append(line.upper())
        else:
            out.append(f"{line}.TW")
    return out


def williams_percent_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hh = df["High"].rolling(period).max()
    ll = df["Low"].rolling(period).min()
    denom = hh - ll
    wr = (hh - df["Close"]) / denom * -100.0
    return wr.mask((denom == 0) | denom.isna())


def fetch_history(symbol: str, lookback_days: int) -> pd.DataFrame:
    t = yf.Ticker(symbol)
    df = t.history(period=f"{lookback_days}d", auto_adjust=False)
    if df.empty:
        return df
    return df.rename(columns=str.title)


def _pct_change(close_now: float, close_prev: float) -> float | None:
    if close_prev and close_prev != 0:
        return round((close_now / close_prev - 1.0) * 100.0, 2)
    return None


def process_symbol(
    sym: str,
    *,
    period: int,
    lookback_days: int,
    recent: int,
) -> tuple[dict, pd.DataFrame | None]:
    hist = fetch_history(sym, lookback_days)
    recent_df = None

    if hist.empty or len(hist) < period:
        return (
            {
                "symbol": sym,
                "as_of": None,
                "open": None,
                "high": None,
                "low": None,
                "close": None,
                "volume": None,
                "day_pct": "",
                "williams_r": None,
                "note": "no_data",
            },
            recent_df,
        )

    hist = hist.copy()
    hist["WilliamsR"] = williams_percent_r(hist, period)
    last = hist.iloc[-1]
    prev = hist.iloc[-2] if len(hist) >= 2 else None
    day_pct = ""
    if prev is not None:
        p = _pct_change(float(last["Close"]), float(prev["Close"]))
        if p is not None:
            day_pct = f"{p:+.2f}%"

    vol = last.get("Volume")
    vol_out: int | None
    if pd.isna(vol):
        vol_out = None
    else:
        vol_out = int(vol)

    wr_val = float(last["WilliamsR"]) if pd.notna(last["WilliamsR"]) else None
    if wr_val is not None:
        wr_val = round(wr_val, 2)

    row = {
        "symbol": sym,
        "as_of": last.name.strftime("%Y-%m-%d") if hasattr(last.name, "strftime") else str(last.name),
        "open": round(float(last["Open"]), 4),
        "high": round(float(last["High"]), 4),
        "low": round(float(last["Low"]), 4),
        "close": round(float(last["Close"]), 4),
        "volume": vol_out,
        "day_pct": day_pct,
        "williams_r": wr_val,
        "note": "",
    }

    if recent > 0:
        tail = hist.tail(recent).copy()
        tail.insert(0, "symbol", sym)
        tail = tail.rename_axis("date").reset_index()
        tail["date"] = tail["date"].apply(
            lambda x: x.strftime("%Y-%m-%d") if hasattr(x, "strftime") else str(x)
        )
        tail["WilliamsR"] = tail["WilliamsR"].round(2)
        for c in ("Open", "High", "Low", "Close"):
            tail[c] = tail[c].round(4)
        tail["Volume"] = pd.to_numeric(tail["Volume"], errors="coerce").fillna(0).astype("int64")
        recent_df = tail[
            ["symbol", "date", "Open", "High", "Low", "Close", "Volume", "WilliamsR"]
        ].rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
                "WilliamsR": "williams_r",
            }
        )

    return row, recent_df


def _sanitize_json_value(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    try:
        if pd.isna(v):
            return None
    except (ValueError, TypeError):
        pass
    return v


def snapshot_to_json_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    records = df.replace({pd.NA: None}).to_dict(orient="records")
    return [{k: _sanitize_json_value(v) for k, v in r.items()} for r in records]


def run_snapshot(
    *,
    universe: Universe,
    period: int = 14,
    sort_key: SortKey = "symbol",
    recent: int = 0,
    workers: int = 10,
    watchlist_path: Path | None = None,
    tw50_path: Path | None = None,
) -> dict[str, Any]:
    wl = watchlist_path or (ROOT / "watchlist.txt")
    t50 = tw50_path or (ROOT / "tw50_constituents.txt")
    path = t50 if universe == "tw50" else wl
    symbols = load_symbols(path)
    if not symbols:
        raise ValueError(f"No symbols in {path}")

    lookback_days = max(period + 60, 180)
    rows: list[dict] = []
    recent_parts: list[pd.DataFrame] = []

    max_workers = max(1, min(workers, len(symbols)))

    def job(sym: str) -> tuple[dict, pd.DataFrame | None]:
        return process_symbol(sym, period=period, lookback_days=lookback_days, recent=recent)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(job, s): s for s in symbols}
        for fut in as_completed(futures):
            summary, rdf = fut.result()
            rows.append(summary)
            if rdf is not None and not rdf.empty:
                recent_parts.append(rdf)

    out = pd.DataFrame(rows)
    if sort_key == "williams_r":
        out = out.sort_values(
            ["williams_r", "symbol"],
            ascending=[True, True],
            na_position="last",
        )
    elif sort_key == "williams_r_desc":
        out = out.sort_values(
            ["williams_r", "symbol"],
            ascending=[False, True],
            na_position="last",
        )
    else:
        out = out.sort_values("symbol", ascending=True, na_position="last")

    payload: dict[str, Any] = {
        "universe": universe,
        "period": period,
        "sort": sort_key,
        "recent_sessions": recent,
        "snapshot": snapshot_to_json_records(out),
    }

    if recent_parts and recent > 0:
        long_df = pd.concat(recent_parts, ignore_index=True)
        long_df = long_df.sort_values(["symbol", "date"], ascending=[True, True])
        hist_records = long_df.replace({pd.NA: None}).to_dict(orient="records")
        payload["history"] = [
            {k: _sanitize_json_value(v) for k, v in r.items()} for r in hist_records
        ]
    else:
        payload["history"] = []

    return payload


_watchlist_lock = threading.Lock()


def symbol_line_to_yahoo(line: str) -> str:
    s = line.strip().upper()
    if not s:
        raise ValueError("empty line")
    if "." in s:
        return s
    return f"{s}.TW"


def yahoo_to_file_line(yahoo: str) -> str:
    y = yahoo.strip().upper()
    if y.endswith(".TWO"):
        return y
    if y.endswith(".TW"):
        return y[:-3]
    if re.fullmatch(r"\d{3,5}", y):
        return y
    raise ValueError("invalid symbol")


def read_watchlist_entries(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    out: list[dict[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append({"line": line, "yahoo": symbol_line_to_yahoo(line)})
    return out


def resolve_numeric_yahoo(code: str) -> str:
    s = code.strip().upper()
    if not re.fullmatch(r"\d{3,5}", s):
        raise ValueError("Use 3–5 digit code, or e.g. 2330.TW / 6488.TWO")
    for cand in (f"{s}.TW", f"{s}.TWO"):
        if not fetch_history(cand, 7).empty:
            return cand
    raise ValueError(f"No Yahoo data for {s}.TW / {s}.TWO")


def coalesce_yahoo_for_add(raw: str) -> str:
    s = raw.strip().upper()
    if not s:
        raise ValueError("empty symbol")
    if s.endswith(".TW") or s.endswith(".TWO"):
        if fetch_history(s, 7).empty:
            raise ValueError(f"No Yahoo data for {s}")
        return s
    return resolve_numeric_yahoo(s)


def remove_target_yahoo_set(user_tokens: list[str]) -> set[str]:
    targets: set[str] = set()
    for raw in user_tokens:
        s = raw.strip().upper()
        if not s:
            continue
        if s.endswith(".TWO") or s.endswith(".TW"):
            targets.add(s)
        elif re.fullmatch(r"\d{3,5}", s):
            targets.add(f"{s}.TW")
            targets.add(f"{s}.TWO")
    return targets


def search_tw_symbols(query: str, limit: int = 16) -> list[dict[str, str]]:
    q = query.strip()
    if not q or limit < 1:
        return []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    try:
        from yfinance import Search

        res = Search(q, max_results=max(limit * 5, 40))
        for item in getattr(res, "quotes", None) or []:
            sym = str(item.get("symbol") or "").strip()
            if not sym or sym in seen:
                continue
            if sym.endswith(".TW") or sym.endswith(".TWO"):
                seen.add(sym)
                out.append(
                    {
                        "symbol": sym,
                        "name": str(item.get("shortname") or item.get("longname") or ""),
                        "exchange": str(item.get("exchange") or ""),
                        "quote_type": str(item.get("quoteType") or ""),
                    }
                )
            if len(out) >= limit:
                return out
    except Exception:
        pass

    if len(out) < limit and re.fullmatch(r"\d{3,5}", q):
        for suffix in (".TW", ".TWO"):
            sym = f"{q}{suffix}"
            if sym in seen or fetch_history(sym, 7).empty:
                continue
            seen.add(sym)
            out.append(
                {
                    "symbol": sym,
                    "name": "",
                    "exchange": "TWO" if suffix == ".TWO" else "TAI",
                    "quote_type": "EQUITY",
                }
            )
            break

    return out[:limit]


def watchlist_add(path: Path, symbols: list[str]) -> dict[str, Any]:
    added: list[str] = []
    skipped: list[dict[str, str]] = []
    with _watchlist_lock:
        if not path.parent.is_dir():
            raise ValueError("watchlist path has no parent directory")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file():
            path.write_text(
                "# One ticker per line. Listed: digits only. OTC e.g. 6488.TWO\n",
                encoding="utf-8",
            )
        have = {e["yahoo"] for e in read_watchlist_entries(path)}
        for raw in symbols:
            try:
                y = coalesce_yahoo_for_add(raw)
                line = yahoo_to_file_line(y)
            except ValueError as e:
                skipped.append({"symbol": raw, "reason": str(e)})
                continue
            if y in have:
                skipped.append({"symbol": raw, "reason": "duplicate"})
                continue
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
            have.add(y)
            added.append(line)
    return {"added": added, "skipped": skipped}


def watchlist_remove(path: Path, symbols: list[str]) -> dict[str, Any]:
    targets = remove_target_yahoo_set(symbols)
    removed: list[str] = []
    with _watchlist_lock:
        if not path.is_file():
            return {"removed": removed}
        lines = path.read_text(encoding="utf-8").splitlines()
        new_lines: list[str] = []
        for raw in lines:
            s = raw.strip()
            if not s or s.startswith("#"):
                new_lines.append(raw)
                continue
            y = symbol_line_to_yahoo(s)
            if y in targets:
                removed.append(s)
                continue
            new_lines.append(raw)
        path.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8")
    return {"removed": removed}
