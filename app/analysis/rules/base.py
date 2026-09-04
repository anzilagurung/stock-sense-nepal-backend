"""Rule definitions for the analysis engine.

Rules are declarative: each metric describes its bands (excellent/good/fair/weak/very_weak),
a benchmark string for the UI, an explanation, category, weight, and whether higher or lower
values are better. The engine reads these — no hard-coded if/elif per metric.

Weights within a category do not need to sum to any particular number; they are normalised
inside the category. Category weights should ideally sum to 1.0 but the engine will normalise
them defensively.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Direction(str, Enum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


@dataclass(frozen=True)
class Band:
    """A single quality band.

    Bounds are inclusive on both sides where sensible. `min` = None means -inf,
    `max` = None means +inf. Rating is the label ("excellent" / "good" / ...).
    Score is the 0-100 value awarded when the metric falls in this band.
    """
    rating: str
    score: float
    min: float | None = None
    max: float | None = None

    def contains(self, value: float) -> bool:
        if self.min is not None and value < self.min:
            return False
        if self.max is not None and value > self.max:
            return False
        return True


@dataclass(frozen=True)
class MetricRule:
    key: str                 # matches FinancialMetric.metric_key
    display_name: str
    category: str            # e.g. "profitability", "asset_quality"
    weight: float            # weight within the category
    unit: str                # "%", "x", "Rs", etc.
    direction: Direction
    bands: tuple[Band, ...]  # ordered best -> worst is fine; contains() handles matching
    benchmark_text: str      # short line shown in the UI ("Good: <3%")
    explanation: str         # human explanation of why this metric matters


@dataclass(frozen=True)
class CategoryDefinition:
    key: str
    display_name: str
    weight: float            # weight of the category in the overall score
    facet: str = "quality"   # "quality" or "valuation" — for the quality/valuation split


@dataclass(frozen=True)
class SectorRules:
    sector: str
    methodology_version: str
    categories: tuple[CategoryDefinition, ...]
    metrics: tuple[MetricRule, ...]
    profile_weight_overrides: dict[str, dict[str, float]] = field(default_factory=dict)
    """profile_weight_overrides["growth"]["growth"] = 0.40 style overrides."""

    def category(self, key: str) -> CategoryDefinition | None:
        for c in self.categories:
            if c.key == key:
                return c
        return None

    def metrics_in(self, category_key: str) -> list[MetricRule]:
        return [m for m in self.metrics if m.category == category_key]


RATING_ORDER = ["excellent", "good", "fair", "weak", "very_weak"]


def rating_from_score(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 55:
        return "fair"
    if score >= 40:
        return "weak"
    return "very_weak"
