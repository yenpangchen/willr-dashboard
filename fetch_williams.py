#!/usr/bin/env python3
"""CLI: Williams %R for Taiwan stocks (Yahoo)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from willr_core import ROOT, run_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Williams %R for TW stocks (Yahoo)")
    parser.add_argument(
        "--universe",
        choices=("watchlist", "tw50"),
        default="watchlist",
        help="watchlist=watchlist.txt; tw50=tw50_constituents.txt",
    )
    parser.add_argument("--watchlist", type=Path, default=ROOT / "watchlist.txt")
    parser.add_argument("--tw50-list", type=Path, default=ROOT / "tw50_constituents.txt")
    parser.add_argument("--period", type=int, default=14)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument(
        "--sort",
        choices=("symbol", "williams_r", "williams_r_desc"),
        default="symbol",
    )
    parser.add_argument("--recent", type=int, default=0, metavar="N")
    args = parser.parse_args()

    payload = run_snapshot(
        universe=args.universe,
        period=args.period,
        sort_key=args.sort,
        recent=args.recent,
        workers=args.workers,
        watchlist_path=args.watchlist,
        tw50_path=args.tw50_list,
    )

    out = pd.DataFrame(payload["snapshot"])
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_rows", 200)
    print(out.to_string(index=False))

    hist = payload.get("history") or []
    if hist:
        long_df = pd.DataFrame(hist)
        print()
        print(f"# Last {args.recent} sessions per symbol (OHLCV + Williams %R)")
        print(long_df.to_string(index=False))


if __name__ == "__main__":
    main()
