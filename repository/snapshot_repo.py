from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from db.models import DailyPrice, IndicatorWilliams, JobRun, Symbol


class SnapshotRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_symbols(self, rows: list[dict[str, Any]]) -> None:
        for r in rows:
            stmt = insert(Symbol).values(
                symbol=r["symbol"],
                name=r.get("name", ""),
                universe=r.get("universe", "tw50"),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[Symbol.symbol],
                set_={"name": r.get("name", ""), "universe": r.get("universe", "tw50")},
            )
            self.db.execute(stmt)
        self.db.commit()

    def upsert_prices(self, rows: list[dict[str, Any]]) -> None:
        for r in rows:
            stmt = insert(DailyPrice).values(
                symbol=r["symbol"],
                trade_date=r["trade_date"],
                open=r.get("open"),
                high=r.get("high"),
                low=r.get("low"),
                close=r.get("close"),
                volume=r.get("volume"),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[DailyPrice.symbol, DailyPrice.trade_date],
                set_={
                    "open": r.get("open"),
                    "high": r.get("high"),
                    "low": r.get("low"),
                    "close": r.get("close"),
                    "volume": r.get("volume"),
                },
            )
            self.db.execute(stmt)
        self.db.commit()

    def upsert_williams(self, rows: list[dict[str, Any]]) -> None:
        for r in rows:
            stmt = insert(IndicatorWilliams).values(
                symbol=r["symbol"],
                trade_date=r["trade_date"],
                period=r["period"],
                value=r.get("value"),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[IndicatorWilliams.symbol, IndicatorWilliams.trade_date, IndicatorWilliams.period],
                set_={"value": r.get("value")},
            )
            self.db.execute(stmt)
        self.db.commit()

    def add_job_run(self, job_name: str, status: str, message: str = "") -> None:
        self.db.add(
            JobRun(
                job_name=job_name,
                status=status,
                message=message,
                finished_at=datetime.utcnow(),
            )
        )
        self.db.commit()

    def latest_snapshot(self, period: int, universe: str = "tw50") -> list[dict[str, Any]]:
        max_date = self.db.scalar(select(func.max(IndicatorWilliams.trade_date)).where(IndicatorWilliams.period == period))
        if max_date is None:
            return []

        q = (
            select(
                Symbol.symbol,
                Symbol.name,
                DailyPrice.trade_date,
                DailyPrice.open,
                DailyPrice.high,
                DailyPrice.low,
                DailyPrice.close,
                DailyPrice.volume,
                IndicatorWilliams.value,
            )
            .join(DailyPrice, and_(DailyPrice.symbol == Symbol.symbol, DailyPrice.trade_date == max_date))
            .join(
                IndicatorWilliams,
                and_(
                    IndicatorWilliams.symbol == Symbol.symbol,
                    IndicatorWilliams.trade_date == max_date,
                    IndicatorWilliams.period == period,
                ),
            )
            .where(Symbol.universe == universe)
        )
        rows = self.db.execute(q).all()
        if not rows:
            return []

        prev_date = self.db.scalar(
            select(func.max(DailyPrice.trade_date)).where(and_(DailyPrice.trade_date < max_date))
        )
        prev_close_map: dict[str, float] = {}
        if prev_date is not None:
            prev_rows = self.db.execute(
                select(DailyPrice.symbol, DailyPrice.close).where(DailyPrice.trade_date == prev_date)
            ).all()
            prev_close_map = {r[0]: float(r[1]) for r in prev_rows if r[1] is not None}

        out: list[dict[str, Any]] = []
        for symbol, name, trade_date, op, hi, lo, cl, vol, wr in rows:
            day_pct = ""
            if cl is not None and symbol in prev_close_map and prev_close_map[symbol] != 0:
                pct = (float(cl) / prev_close_map[symbol] - 1.0) * 100.0
                day_pct = f"{pct:+.2f}%"
            out.append(
                {
                    "symbol": symbol,
                    "name": name or "",
                    "as_of": trade_date.isoformat() if isinstance(trade_date, date) else str(trade_date),
                    "open": float(op) if op is not None else None,
                    "high": float(hi) if hi is not None else None,
                    "low": float(lo) if lo is not None else None,
                    "close": float(cl) if cl is not None else None,
                    "volume": int(vol) if vol is not None else None,
                    "day_pct": day_pct,
                    "williams_r": round(float(wr), 2) if wr is not None else None,
                    "note": "",
                }
            )
        return out

    def recent_history(self, period: int, recent: int, universe: str = "tw50") -> list[dict[str, Any]]:
        if recent <= 0:
            return []
        symbols = self.db.execute(select(Symbol.symbol).where(Symbol.universe == universe)).scalars().all()
        if not symbols:
            return []
        q = (
            select(
                DailyPrice.symbol,
                DailyPrice.trade_date,
                DailyPrice.open,
                DailyPrice.high,
                DailyPrice.low,
                DailyPrice.close,
                DailyPrice.volume,
                IndicatorWilliams.value,
            )
            .join(
                IndicatorWilliams,
                and_(
                    IndicatorWilliams.symbol == DailyPrice.symbol,
                    IndicatorWilliams.trade_date == DailyPrice.trade_date,
                    IndicatorWilliams.period == period,
                ),
            )
            .where(DailyPrice.symbol.in_(symbols))
            .order_by(DailyPrice.symbol.asc(), DailyPrice.trade_date.desc())
        )
        rows = self.db.execute(q).all()
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for symbol, trade_date, op, hi, lo, cl, vol, wr in rows:
            if len(grouped[symbol]) >= recent:
                continue
            grouped[symbol].append(
                {
                    "symbol": symbol,
                    "date": trade_date.isoformat() if isinstance(trade_date, date) else str(trade_date),
                    "open": float(op) if op is not None else None,
                    "high": float(hi) if hi is not None else None,
                    "low": float(lo) if lo is not None else None,
                    "close": float(cl) if cl is not None else None,
                    "volume": int(vol) if vol is not None else 0,
                    "williams_r": round(float(wr), 2) if wr is not None else None,
                }
            )

        out: list[dict[str, Any]] = []
        for symbol in sorted(grouped.keys()):
            out.extend(sorted(grouped[symbol], key=lambda r: r["date"]))
        return out

