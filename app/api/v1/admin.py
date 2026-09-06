from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
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
