"""Trajectory scoring (methodology v2.0).

Every scored metric gets a "trajectory" label derived from the last 3+ historical
observations: ``improving`` / ``stable`` / ``declining`` / ``unknown``.

Aggregated across all metrics in a sector, we produce a single sentiment for
the company — used by the verdict engine to *promote* a Buy Candidate to
Strong Buy when a broad basket of metrics is improving, or to *demote* when
they are broadly declining. The raw 0-100 score is left unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.analysis.derived import HistoricalMetricPoint, compute_metric_trend
from app.analysis.rules import SECTOR_RULES
from app.analysis.rules.base import Direction


@dataclass(frozen=True)
class MetricTrajectory:
    metric_key: str
    direction: str      # "improving" | "stable" | "declining" | "unknown"
    change_fraction: float | None


@dataclass(frozen=True)
class TrajectoryReport:
    sentiment: str      # "improving" | "stable" | "declining" | "unknown"
    improving_count: int
    stable_count: int
    declining_count: int
    unknown_count: int
    per_metric: dict[str, MetricTrajectory]


def compute(sector: str, history: list[HistoricalMetricPoint]) -> TrajectoryReport:
    """Score every metric that has enough history and roll up an overall sentiment."""
    rules = SECTOR_RULES.get(sector)
    per_metric: dict[str, MetricTrajectory] = {}

    if rules is None or not history:
        return TrajectoryReport(
            sentiment="unknown",
            improving_count=0,
            stable_count=0,
            declining_count=0,
            unknown_count=0,
            per_metric={},
        )

    improving = stable = declining = unknown = 0
    for metric in rules.metrics:
        higher_is_better = metric.direction == Direction.HIGHER_IS_BETTER
        result = compute_metric_trend(history, metric.key, higher_is_better)
        if result is None:
            per_metric[metric.key] = MetricTrajectory(metric.key, "unknown", None)
            unknown += 1
            continue
        direction, change = result
        per_metric[metric.key] = MetricTrajectory(metric.key, direction, change)
        if direction == "improving":
            improving += 1
        elif direction == "declining":
            declining += 1
        else:
            stable += 1

    known = improving + stable + declining
    if known == 0:
        sentiment = "unknown"
    else:
        imp_ratio = improving / known
        dec_ratio = declining / known
        if imp_ratio - dec_ratio >= 0.30:
            sentiment = "improving"
        elif dec_ratio - imp_ratio >= 0.30:
            sentiment = "declining"
        else:
            sentiment = "stable"

    return TrajectoryReport(
        sentiment=sentiment,
        improving_count=improving,
        stable_count=stable,
        declining_count=declining,
        unknown_count=unknown,
        per_metric=per_metric,
    )
