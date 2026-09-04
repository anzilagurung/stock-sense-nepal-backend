"""Ingestion orchestration.

Fetches prices/movers/summary from a `NepseDataSource`, then upserts them into the DB.
Every step is fail-soft: any single failing endpoint is captured in the FetchReport
but does not abort the rest of the run. If the whole upstream is unavailable, we
return an `ok=False` report and the app keeps serving whatever DB state we already have.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.source import FetchReport, NepseDataSource, PriceQuote
from app.models import Company, MarketPrice


async def _safe(coro, errors: list[str], label: str):
    try:
        return await coro
    except Exception as e:  # noqa: BLE001 — deliberately broad; we want partial success
        errors.append(f"{label}: {type(e).__name__}: {e}")
        return None


def _upsert_prices(db: Session, quotes: list[PriceQuote]) -> int:
    if not quotes:
        return 0

    # Map company_id per symbol so we don't re-query per row.
    symbols = {q.symbol for q in quotes}
    companies = {c.symbol: c for c in db.scalars(select(Company).where(Company.symbol.in_(symbols)))}

    trading_date = datetime.utcnow().strftime("%Y-%m-%d")
    written = 0

    for q in quotes:
        company = companies.get(q.symbol)
        if not company:
            continue  # source referenced a symbol we don't know — safe to skip

        latest = db.scalar(
            select(MarketPrice)
            .where(MarketPrice.company_id == company.id)
            .order_by(MarketPrice.id.desc())
            .limit(1)
        )

        if latest and latest.trading_date == trading_date:
            # Same trading day — update in place instead of piling rows.
            latest.ltp = q.ltp
            latest.previous_close = q.previous_close
            latest.change = q.change
            latest.percent_change = q.percent_change
            latest.day_high = q.day_high or latest.day_high
            latest.day_low = q.day_low or latest.day_low
            latest.volume = q.volume or latest.volume
            latest.turnover = q.turnover or latest.turnover
            latest.trades = q.trades or latest.trades
            latest.source = "nepse_unofficial"
        else:
            db.add(MarketPrice(
                company_id=company.id,
                trading_date=trading_date,
                ltp=q.ltp,
                previous_close=q.previous_close,
                change=q.change,
                percent_change=q.percent_change,
                day_high=q.day_high,
                day_low=q.day_low,
                volume=q.volume,
                turnover=q.turnover,
                trades=q.trades,
                source="nepse_unofficial",
            ))
        written += 1

    db.commit()
    return written


async def run_ingestion(source: NepseDataSource, db: Session) -> FetchReport:
    start = time.monotonic()
    errors: list[str] = []

    prices, gainers, losers, summary = await asyncio.gather(
        _safe(source.fetch_prices(),      errors, "prices"),
        _safe(source.fetch_top_gainers(), errors, "top_gainers"),
        _safe(source.fetch_top_losers(),  errors, "top_losers"),
        _safe(source.fetch_summary(),     errors, "summary"),
    )

    combined: dict[str, PriceQuote] = {}
    for bucket in (prices, gainers, losers):
        if not bucket:
            continue
        for q in bucket:
            # Prefer the most complete quote (prices > movers).
            if q.symbol not in combined or (q.volume or q.turnover):
                combined[q.symbol] = q

    written = _upsert_prices(db, list(combined.values()))
    duration_ms = int((time.monotonic() - start) * 1000)

    return FetchReport(
        provider=source.name,
        ok=written > 0,
        prices=written,
        top_movers=(len(gainers or []) + len(losers or [])),
        summary_ok=summary is not None,
        errors=errors,
        duration_ms=duration_ms,
    )
