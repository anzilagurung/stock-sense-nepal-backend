"""Peer-relative percentile service (methodology v2.0).

For every sector we compute p25 / p50 / p75 of each metric across all companies
that have a latest report. A given company's metric can then be labelled
``top_quartile``, ``above_median``, ``below_median``, or ``bottom_quartile``.

The absolute band score does not change — this is purely an overlay for
context and for the verdict rationale. Results are cached in memory for a
short TTL to avoid re-running on every request.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.models import Company, FinancialReport
from app.analysis.rules import SECTOR_RULES
from app.analysis.rules.base import Direction


_CACHE_TTL_SECONDS = 300  # 5 minutes; plenty for a mostly-static universe.
_cache: dict[str, tuple[float, dict[str, dict[str, float]]]] = {}


@dataclass(frozen=True)
class PercentileBand:
    p25: float
    p50: float
    p75: float


def _compute(db: Session, sector: str) -> dict[str, dict[str, float]]:
    """Latest-report percentile snapshot for every metric in the given sector."""
    rules = SECTOR_RULES.get(sector)
    if rules is None:
        return {}

    companies = list(db.scalars(select(Company).where(Company.sector == sector)))
    if len(companies) < 3:
        # Percentile needs at least a few peers to be meaningful.
        return {}

    values_by_metric: dict[str, list[float]] = {m.key: [] for m in rules.metrics}
    for c in companies:
        report = db.scalar(
            select(FinancialReport)
            .where(FinancialReport.company_id == c.id)
            .options(selectinload(FinancialReport.metrics))
            .order_by(FinancialReport.fiscal_year.desc(), FinancialReport.id.desc())
        )
        if report is None:
            continue
        for m in report.metrics:
            if m.metric_value is None:
                continue
            if m.metric_key in values_by_metric:
                values_by_metric[m.metric_key].append(m.metric_value)

    out: dict[str, dict[str, float]] = {}
    for key, xs in values_by_metric.items():
        if len(xs) < 3:
            continue
        xs_sorted = sorted(xs)
        try:
            q = statistics.quantiles(xs_sorted, n=4)
            out[key] = {"p25": q[0], "p50": q[1], "p75": q[2]}
        except statistics.StatisticsError:
            continue
    return out


def get_sector_percentiles(db: Session, sector: str) -> dict[str, dict[str, float]]:
    """Cached wrapper around :func:`_compute`."""
    now = time.time()
    entry = _cache.get(sector)
    if entry and (now - entry[0]) < _CACHE_TTL_SECONDS:
        return entry[1]
    fresh = _compute(db, sector)
    _cache[sector] = (now, fresh)
    return fresh


def clear_cache() -> None:
    """Test hook."""
    _cache.clear()


def percentile_band_for(
    value: float | None,
    key: str,
    percentiles: dict[str, dict[str, float]],
    higher_is_better: bool = True,
) -> str | None:
    """Bucket a value into a quartile label, respecting metric direction.

    For "lower is better" metrics (P/E, NPL, D/E) the polarity is inverted so
    ``top_quartile`` always means "best-in-sector".
    """
    if value is None:
        return None
    p = percentiles.get(key)
    if not p:
        return None

    if higher_is_better:
        if value >= p["p75"]:
            return "top_quartile"
        if value >= p["p50"]:
            return "above_median"
        if value >= p["p25"]:
            return "below_median"
        return "bottom_quartile"
    else:
        if value <= p["p25"]:
            return "top_quartile"
        if value <= p["p50"]:
            return "above_median"
        if value <= p["p75"]:
            return "below_median"
        return "bottom_quartile"


def is_higher_is_better(sector: str, metric_key: str) -> bool | None:
    """Look up direction on the sector's rule set."""
    rules = SECTOR_RULES.get(sector)
    if rules is None:
        return None
    for m in rules.metrics:
        if m.key == metric_key:
            return m.direction == Direction.HIGHER_IS_BETTER
    return None
