import asyncio
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.ingestion.backfill import run_backfill
from app.ingestion.nepse_unofficial import NepseUnofficialSource
from app.ingestion.runner import run_ingestion
from app.ingestion.sharesansar import SharesansarSource
from app.ingestion.source import NepseDataSource
from app.ingestion.stockmap import seed_companies

router = APIRouter(prefix="/admin", tags=["admin"])


def _pick_source(provider: str | None) -> NepseDataSource:
    key = (provider or settings.nepse_upstream).lower()
    if key in {"sharesansar", "share_sansar"}:
        return SharesansarSource()
    if key in {"nepse_unofficial", "unofficial", "surajrimal"}:
        return NepseUnofficialSource()
    raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'. Valid: sharesansar, nepse_unofficial")


@router.post("/refresh/prices")
async def refresh_prices(
    db: Session = Depends(get_db),
    provider: str | None = Query(default=None, description="Override upstream: sharesansar | nepse_unofficial"),
):
    """Attempt a live-price sync from the configured NEPSE data source.

    Always returns 200. The response body describes what succeeded and what failed —
    an upstream outage never propagates a 5xx to the caller.
    """
    source = _pick_source(provider)
    report = await run_ingestion(source, db)
    return {
        "ok": report.ok,
        "provider": report.provider,
        "prices_updated": report.prices,
        "top_movers_seen": report.top_movers,
        "summary_ok": report.summary_ok,
        "errors": report.errors,
        "duration_ms": report.duration_ms,
        "ran_at": datetime.utcnow().isoformat(),
    }


@router.post("/refresh/companies")
def refresh_companies(db: Session = Depends(get_db)):
    """Re-run the bundled stockmap seed. Idempotent — updates names/sectors if they changed."""
    counts = seed_companies(db)
    return {"ok": True, "counts": counts, "ran_at": datetime.utcnow().isoformat()}


async def _run_backfill_in_background(days: int, delay: float, symbols: list[str] | None):
    """Runs on its own DB session so it survives past the HTTP request lifecycle."""
    db = SessionLocal()
    try:
        # Progress goes to stdout so Render logs capture it.
        report = await run_backfill(
            db,
            days=days,
            request_delay=delay,
            only_symbols=symbols,
            progress=print,
        )
        print(
            f"[backfill] done: processed {report.processed}/{report.total_companies}, "
            f"created {report.rows_written}, updated {report.rows_updated}, "
            f"failed {len(report.symbols_failed)}, empty {len(report.symbols_empty)}, "
            f"took {report.duration_ms / 1000:.1f}s"
        )
    except Exception as e:
        print(f"[backfill] crashed: {e}")
    finally:
        db.close()


@router.post("/backfill/prices")
async def backfill_prices(
    background_tasks: BackgroundTasks,
    days: int = Query(default=400, ge=10, le=1000,
                      description="Max rows per company (~250 = 1 trading year)"),
    delay: float = Query(default=0.35, ge=0.15, le=2.0,
                         description="Seconds between requests (be a good citizen)"),
    symbols: str | None = Query(default=None,
                                description="Comma-separated symbols; default is all companies"),
):
    """Kick off a historical-price backfill as a background task.

    Returns immediately with an acknowledgement — the actual work (~3–5 min
    for the full universe) runs in the background and streams progress to
    the process stdout. Not authenticated; guard at the reverse-proxy layer
    if this needs to be locked down in production.
    """
    sym_list: list[str] | None = None
    if symbols:
        sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    background_tasks.add_task(_run_backfill_in_background, days, delay, sym_list)
    return {
        "ok": True,
        "started": True,
        "days": days,
        "delay_seconds": delay,
        "symbols_requested": sym_list,
        "note": "Backfill runs in the background; watch service logs for progress.",
        "ran_at": datetime.utcnow().isoformat(),
    }
