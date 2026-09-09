"""One-shot CLI: bootstrap historical daily prices for every listed company.

Usage:
    # Runs against whatever DATABASE_URL env is set (defaults to local SQLite).
    python -m tool.backfill_prices --days 400

    # Only a subset (useful for testing / debugging one symbol):
    python -m tool.backfill_prices --days 30 --symbols NABIL EBL

    # Point at a specific Postgres URL (e.g. Render external URL):
    DATABASE_URL='postgresql://user:pass@host/db' \
        python -m tool.backfill_prices --days 400

For 350+ symbols × ~1 year of history the run takes ~3-5 minutes at the default
delay. Progress is streamed to stdout; the final line is a summary.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Make the repo root importable when running as `python tool/backfill_prices.py`.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.ingestion.backfill import run_backfill  # noqa: E402


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Backfill historical NEPSE daily prices from sharesansar.")
    ap.add_argument("--days", type=int, default=400,
                    help="Max rows per company (default: 400 ≈ ~1.5 trading years).")
    ap.add_argument("--delay", type=float, default=0.35,
                    help="Seconds to sleep between requests (default: 0.35).")
    ap.add_argument("--symbols", nargs="*", default=None,
                    help="Optional list of symbols to backfill; default is all listed companies.")
    return ap.parse_args()


async def _main() -> int:
    args = _parse_args()
    db = SessionLocal()
    try:
        report = await run_backfill(
            db,
            days=args.days,
            request_delay=args.delay,
            only_symbols=args.symbols,
            progress=print,
        )
    finally:
        db.close()

    print()
    print("=" * 60)
    print("Backfill complete")
    print(f"  Companies processed: {report.processed}/{report.total_companies}")
    print(f"  Rows created:        {report.rows_written}")
    print(f"  Rows updated:        {report.rows_updated}")
    print(f"  Empty responses:     {len(report.symbols_empty)}")
    print(f"  Failed:              {len(report.symbols_failed)}")
    print(f"  Duration:            {report.duration_ms / 1000:.1f}s")
    if report.symbols_failed:
        print("\nFailed symbols (first 10):")
        for sym, err in report.symbols_failed[:10]:
            print(f"  - {sym}: {err}")
    return 0 if not report.symbols_failed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
