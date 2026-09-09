"""Derived metrics computed on top of the raw ingested values.

These are read by the verdict layer (red flags, trajectory, rationale) and are
also merged into the snapshot's ``values`` dict so they appear consistently in
every downstream consumer. They intentionally *do not* introduce new scored
metrics in any sector — the 0-100 score arithmetic stays a pure roll-up of the
sector's declared bands. Derived metrics inform the verdict, not the score.

If any input is missing the derived value stays absent (``None``) — no
fabricated numbers.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalMetricPoint:
    """One historical observation of a metric — used for trajectory + volatility."""
    fiscal_year: str
    quarter: str
    metric_key: str
    value: float


@dataclass(frozen=True)
class DividendRecord:
    """Cash + bonus dividend for one fiscal year (already realised)."""
    fiscal_year: str
    cash_percent: float | None
    bonus_percent: float | None

    @property
    def total_percent(self) -> float:
        return (self.cash_percent or 0.0) + (self.bonus_percent or 0.0)


def compute_peg(values: dict[str, float | None]) -> float | None:
    """PEG ratio = P/E ÷ EPS growth (%). Below 1.5 is generally attractive.

    Rejects the calculation when EPS growth is <= 0 (a negative denominator
    would flip the sign and mislead).
    """
    pe = values.get("pe")
    growth = values.get("eps_growth")
    if pe is None or growth is None or growth <= 0:
        return None
    return round(pe / growth, 3)


def compute_dividend_coverage(values: dict[str, float | None]) -> float | None:
    """EPS ÷ DPS. Above 2.5x suggests the dividend is comfortably covered.

    Falls back to ``1 / payout_ratio`` when a direct DPS value isn't present.
    """
    eps = values.get("eps")
    dps = values.get("dps")
    if eps and dps and dps > 0:
        return round(eps / dps, 3)

    payout = values.get("payout_ratio")
    if payout and payout > 0:
        # payout_ratio is stored as a percentage in this codebase.
        return round(100.0 / payout, 3)
    return None


def compute_earnings_volatility(history: list[HistoricalMetricPoint]) -> float | None:
    """Coefficient of variation (stdev / |mean|) of EPS over recent history.

    Lower is better — stable earnings are prized. Needs at least 3 observations
    to be meaningful. Returns None otherwise.
    """
    eps_points = [p.value for p in history if p.metric_key == "eps"]
    if len(eps_points) < 3:
        return None
    mean = statistics.fmean(eps_points)
    if mean == 0:
        return None
    try:
        stdev = statistics.pstdev(eps_points)
    except statistics.StatisticsError:
        return None
    return round(stdev / abs(mean), 3)


def compute_dividend_streak(dividends: list[DividendRecord]) -> int:
    """Number of consecutive most-recent years the company paid ANY dividend."""
    if not dividends:
        return 0
    # Sort newest first, defensively.
    sorted_divs = sorted(dividends, key=lambda d: d.fiscal_year, reverse=True)
    streak = 0
    for d in sorted_divs:
        if d.total_percent > 0:
            streak += 1
        else:
            break
    return streak


def compute_consecutive_loss_quarters(history: list[HistoricalMetricPoint]) -> int:
    """Count the most recent consecutive quarters where EPS was negative.

    Used by the "2+ consecutive losses" red flag.
    """
    eps_points = [
        p for p in sorted(history, key=lambda h: (h.fiscal_year, h.quarter), reverse=True)
        if p.metric_key == "eps"
    ]
    streak = 0
    for p in eps_points:
        if p.value < 0:
            streak += 1
        else:
            break
    return streak


def compute_data_completeness(
    values: dict[str, float | None],
    expected_keys: tuple[str, ...],
    critical_keys: tuple[str, ...] = (),
) -> float:
    """Fraction of expected metrics that have a non-null value, weighted so that
    critical metrics count double.

    Returns a float 0-1. Empty expected_keys returns 1.0 (nothing to be missing).
    """
    if not expected_keys:
        return 1.0

    total_weight = 0.0
    filled_weight = 0.0
    critical_set = set(critical_keys)
    for key in expected_keys:
        w = 2.0 if key in critical_set else 1.0
        total_weight += w
        v = values.get(key)
        if v is not None:
            filled_weight += w
    return round(filled_weight / total_weight, 3) if total_weight > 0 else 1.0


def _years_between(iso_date: str | None) -> int | None:
    """Best-effort number of years between an ISO-ish date and today."""
    if not iso_date:
        return None
    # Accept "YYYY-MM-DD" and "YYYY/MM/DD" and "YYYY".
    from datetime import datetime
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y"):
        try:
            dt = datetime.strptime(iso_date, fmt)
            delta = datetime.utcnow() - dt
            return max(0, int(delta.days / 365))
        except (ValueError, TypeError):
            continue
    return None


def compute_years_listed(listed_date: str | None) -> int | None:
    return _years_between(listed_date)


def compute_average_over_history(
    history: list[HistoricalMetricPoint],
    metric_key: str,
    max_points: int = 4,
) -> float | None:
    """Average of a metric across the ``max_points`` most recent observations."""
    points = [p.value for p in history if p.metric_key == metric_key]
    if not points:
        return None
    tail = points[-max_points:] if len(points) > max_points else points
    return round(sum(tail) / len(tail), 3) if tail else None


def compute_metric_trend(
    history: list[HistoricalMetricPoint],
    metric_key: str,
    higher_is_better: bool,
    min_points: int = 3,
) -> tuple[str, float] | None:
    """Return (direction, magnitude) for a metric's recent trend.

    Direction: "improving" | "stable" | "declining".
    Magnitude: last-value ÷ first-value − 1 (approximate change fraction).
    """
    points = [p.value for p in history if p.metric_key == metric_key]
    if len(points) < min_points:
        return None
    first, last = points[0], points[-1]
    if first == 0:
        change = 0.0
    else:
        change = (last - first) / abs(first)

    threshold = 0.03  # 3% cumulative change to escape "stable"
    if abs(change) < threshold:
        direction = "stable"
    elif (change > 0) == higher_is_better:
        direction = "improving"
    else:
        direction = "declining"
    return direction, round(change, 3)
