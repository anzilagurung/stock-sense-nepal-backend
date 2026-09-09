"""Rule definitions for the analysis engine.

Rules are declarative: each metric describes its bands (excellent/good/fair/weak/very_weak),
a benchmark string for the UI, an explanation, category, weight, and whether higher or lower
values are better. The engine reads these — no hard-coded if/elif per metric.

Weights within a category do not need to sum to any particular number; they are normalised
inside the category. Category weights should ideally sum to 1.0 but the engine will normalise
them defensively.

Methodology v2.0 adds three declarative extensions used by the verdict/red-flag layer
(not the raw score, which stays a pure sector-band roll-up):

* ``RedFlag`` — hard-stop conditions per sector (e.g. NPL > 7% for banks).
* ``StabilityCriteria`` — thresholds for the Blue Chip / Established / Emerging tiers.
* ``critical_metric_keys`` — metrics whose absence should drop data completeness meaningfully.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


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


# --- Verdict / red-flag / stability primitives -------------------------------

RedFlagSeverity = str  # "caution" | "avoid" | "insufficient_data"


@dataclass(frozen=True)
class RedFlag:
    """A hard-stop rule that caps the verdict tier when triggered.

    The condition is a callable so cross-metric rules (e.g. "cheap P/E AND poor quality")
    can be expressed. The message shown to the user is the ``explanation`` field.

    ``severity`` controls how the verdict engine caps the tier:
    * ``avoid`` — verdict cannot rise above "Avoid"
    * ``caution`` — verdict cannot rise above "Caution"
    * ``insufficient_data`` — verdict is forced to "Insufficient Data"
    """
    key: str
    display_name: str
    severity: RedFlagSeverity
    condition: Callable[[dict[str, float | None]], bool]
    explanation: str


@dataclass(frozen=True)
class StabilityCriteria:
    """Thresholds used by the stability classifier for a specific tier."""
    tier: str                       # "blue_chip" | "established" | "emerging"
    min_years_listed: int | None = None
    min_dividend_streak_years: int | None = None
    min_average_roe: float | None = None
    min_market_cap_percentile: int | None = None   # 0-100 within sector
    min_data_completeness: float | None = None     # 0-1


@dataclass(frozen=True)
class SectorRules:
    sector: str
    methodology_version: str
    categories: tuple[CategoryDefinition, ...]
    metrics: tuple[MetricRule, ...]
    profile_weight_overrides: dict[str, dict[str, float]] = field(default_factory=dict)
    """profile_weight_overrides["growth"]["growth"] = 0.40 style overrides."""

    red_flags: tuple[RedFlag, ...] = ()
    """Sector-specific red flags. Empty tuple means only universal flags apply."""

    critical_metric_keys: tuple[str, ...] = ()
    """Metrics whose absence is treated as materially incomplete data."""

    stability_criteria: tuple[StabilityCriteria, ...] = ()
    """Thresholds for the Blue Chip / Established / Emerging classification."""

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


# --- Verdict tier ordering (weakest first, strongest last) ------------------

VERDICT_TIERS = (
    "insufficient_data",
    "avoid",
    "caution",
    "watchlist",
    "hold",
    "buy_candidate",
    "strong_buy_candidate",
)


def cap_verdict(current: str, ceiling: str) -> str:
    """Return the weaker of two verdict tiers."""
    if current not in VERDICT_TIERS or ceiling not in VERDICT_TIERS:
        return current
    return current if VERDICT_TIERS.index(current) <= VERDICT_TIERS.index(ceiling) else ceiling
