"""One-shot historical price backfill.

Populates ``market_prices`` with the last N daily bars for every listed
company using sharesansar's per-company history endpoint. Idempotent — an
``(company_id, trading_date)`` row that already exists is updated in place.

Designed to be safely re-runnable and side-effect friendly:

* Progress is reported via a callback so a caller can log / stream updates.
* Individual symbol failures are captured but never abort the run — the report
  at the end lists everything that went wrong.
* No API auth needed; the endpoint driving this must gate access itself.

Typical use: run once against production DB to bootstrap ~1 year of prices so
EMA20 / EMA50 / ATR14 immediately have enough data to compute. The daily
``/admin/refresh/prices`` cron takes over from there.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.sharesansar_history import (
    HistoricalPrice,
    SharesansarHistoryClient,
)
from app.models import Company, MarketPrice

ProgressFn = Callable[[str], None]


@dataclass
class BackfillReport:
    total_companies: int = 0
    processed: int = 0
    rows_written: int = 0
    rows_updated: int = 0
    symbols_empty: list[str] = field(default_factory=list)
    symbols_failed: list[tuple[str, str]] = field(default_factory=list)  # (symbol, error)
    duration_ms: int = 0


def _upsert_history_for_company(
    db: Session,
    company: Company,
    rows: list[HistoricalPrice],
    source: str = "sharesansar_history",
) -> tuple[int, int]:
    """Insert/update every row for one company. Returns (created, updated)."""
    if not rows:
        return 0, 0

    dates_to_look_up = [r.published_date for r in rows]
    existing = {
        p.trading_date: p
        for p in db.scalars(
            select(MarketPrice).where(
                MarketPrice.company_id == company.id,
                MarketPrice.trading_date.in_(dates_to_look_up),
            )
        )
    }

    created = 0
    updated = 0
    prev_close: float | None = None

    for row in rows:  # sorted oldest → newest
        change = 0.0
        pct = 0.0
        if prev_close and prev_close > 0:
            change = round(row.close - prev_close, 2)
            pct = round((row.close - prev_close) / prev_close * 100, 2)

        record = existing.get(row.published_date)
        if record is None:
            db.add(MarketPrice(
                company_id=company.id,
                trading_date=row.published_date,
                ltp=row.close,
                previous_close=prev_close or 0.0,
                change=change,
                percent_change=pct,
                day_high=row.high,
                day_low=row.low,
                volume=row.volume,
                turnover=row.turnover,
                source=source,
            ))
            created += 1
        else:
            # Only overwrite fields the backfill can source authoritatively;
            # leave week52/market_cap untouched if a live source populated them.
            record.ltp = row.close
            if prev_close and prev_close > 0:
                record.previous_close = prev_close
                record.change = change
                record.percent_change = pct
            record.day_high = row.high or record.day_high
            record.day_low = row.low or record.day_low
            record.volume = row.volume or record.volume
            record.turnover = row.turnover or record.turnover
            record.source = source
            updated += 1

        prev_close = row.close

    return created, updated


async def run_backfill(
    db: Session,
    days: int = 400,
    request_delay: float = 0.35,
    only_symbols: list[str] | None = None,
    progress: ProgressFn | None = None,
) -> BackfillReport:
    """Backfill last ``days`` bars for every company (or just ``only_symbols``).

    ``request_delay`` is applied between requests — keep it above 0.25s to be
    a good citizen of sharesansar.
    """
    import time
    start = time.monotonic()

    q = select(Company).order_by(Company.symbol)
    companies = list(db.scalars(q))
    if only_symbols:
        wanted = {s.upper() for s in only_symbols}
        companies = [c for c in companies if c.symbol.upper() in wanted]

    report = BackfillReport(total_companies=len(companies))
    log = progress or (lambda _: None)

    async with SharesansarHistoryClient(request_delay=request_delay) as client:
        for company in companies:
            try:
                rows = await client.fetch_history(company.symbol, max_rows=days)
            except Exception as e:  # network/parse — log and continue
                report.symbols_failed.append((company.symbol, str(e)[:200]))
                log(f"[FAIL] {company.symbol}: {e}")
                report.processed += 1
                continue

            if not rows:
                report.symbols_empty.append(company.symbol)
                log(f"[EMPTY] {company.symbol}")
                report.processed += 1
                continue

            try:
                created, updated = _upsert_history_for_company(db, company, rows)
                db.commit()
            except Exception as e:
                db.rollback()
                report.symbols_failed.append((company.symbol, f"db: {e}"[:200]))
                log(f"[DB-FAIL] {company.symbol}: {e}")
                report.processed += 1
                continue

            report.rows_written += created
            report.rows_updated += updated
            report.processed += 1
            log(
                f"[OK] {company.symbol}: +{created} new, ~{updated} updated "
                f"({report.processed}/{report.total_companies})"
            )

    report.duration_ms = int((time.monotonic() - start) * 1000)
    return report
