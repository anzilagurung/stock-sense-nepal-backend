"""Bundled full-universe company seed.

Loads a JSON snapshot of every NEPSE-listed security (symbol, name, sector) from
`_reference/stockmap.json` and upserts it into the `companies` table. This runs
once on first boot so the app always has the complete company list available,
independent of any external service.

Source of the snapshot: surajrimal07/NepseAPI-Unofficial (MIT).
Regenerate by re-downloading the file from that repository.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company

STOCKMAP_PATH = Path(__file__).parent / "_reference" / "stockmap.json"

# Promoter / Non-tradeable categories we skip so the app only shows real investable equity.
SKIPPED_SECTORS = {"Promoter Share"}


def load_stockmap() -> dict[str, dict]:
    if not STOCKMAP_PATH.exists():
        return {}
    with STOCKMAP_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def seed_companies(db: Session) -> dict[str, int]:
    """Upsert every company from the stockmap snapshot. Returns counts."""
    data = load_stockmap()
    inserted = 0
    skipped = 0
    updated = 0

    existing = {c.symbol: c for c in db.scalars(select(Company))}

    for symbol, meta in data.items():
        sector = meta.get("sector", "Unknown")
        if sector in SKIPPED_SECTORS:
            skipped += 1
            continue
        name = meta.get("name", symbol)

        if symbol in existing:
            c = existing[symbol]
            changed = False
            if c.name != name:
                c.name = name
                changed = True
            if c.sector != sector:
                c.sector = sector
                changed = True
            if changed:
                updated += 1
            continue

        db.add(Company(
            symbol=symbol,
            name=name,
            sector=sector,
            security_type="Equity",
            status="Listed",
        ))
        inserted += 1

    db.commit()
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "total": len(data)}
