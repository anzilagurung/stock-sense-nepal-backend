"""Mutual Fund scoring rules (methodology v1.0).

Almost all listed NEPSE mutual funds are close-ended schemes with a fixed
tenure. They trade on-exchange and typically at a discount to NAV. The
methodology here focuses on:

  - Discount / premium to NAV (the primary valuation driver)
  - Distribution yield (annual cash return per unit)
  - NAV growth (portfolio performance)
  - Expense ratio (drag on returns)

Because these funds don't have "earnings" in the corporate sense, traditional
PE/PB metrics are omitted; NAV metrics take their place.
"""
from app.analysis.rules.base import (
    Band,
    CategoryDefinition,
    Direction,
    MetricRule,
    SectorRules,
)


CATEGORIES = (
    CategoryDefinition("nav_performance",  "NAV Performance",  weight=0.30, facet="quality"),
    CategoryDefinition("distribution",     "Distribution",     weight=0.20, facet="quality"),
    CategoryDefinition("cost",             "Cost",             weight=0.10, facet="quality"),
    CategoryDefinition("valuation",        "Valuation",        weight=0.40, facet="valuation"),
)


METRICS = (
    # --- NAV Performance -----------------------------------------------------
    MetricRule(
        key="nav_growth", display_name="NAV Growth (YoY)", category="nav_performance",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=18),
            Band("good",        80, min=10, max=18),
            Band("fair",        60, min=4,  max=10),
            Band("weak",        40, min=-3, max=4),
            Band("very_weak",   20, max=-3),
        ),
        benchmark_text="Good: >10% YoY",
        explanation="Year-on-year change in net asset value per unit; the primary indicator of manager performance.",
    ),
    MetricRule(
        key="nav_per_unit", display_name="NAV / Unit", category="nav_performance",
        weight=0.4, unit="Rs", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=14),
            Band("good",        80, min=12, max=14),
            Band("fair",        60, min=10, max=12),
            Band("weak",        40, min=9,  max=10),
            Band("very_weak",   20, max=9),
        ),
        benchmark_text="Above par (Rs 10) is positive since inception",
        explanation="Absolute NAV per unit against the Rs 10 par value. Below par means the fund has lost money over its life.",
    ),

    # --- Distribution --------------------------------------------------------
    MetricRule(
        key="distribution_yield", display_name="Distribution Yield", category="distribution",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=10),
            Band("good",        80, min=6, max=10),
            Band("fair",        60, min=3, max=6),
            Band("weak",        40, min=1, max=3),
            Band("very_weak",   20, max=1),
        ),
        benchmark_text="Good: >6%",
        explanation="Annual cash distribution over market price. Close-ended funds often distribute realised gains and interest income.",
    ),

    # --- Cost ----------------------------------------------------------------
    MetricRule(
        key="expense_ratio_fund", display_name="Expense Ratio", category="cost",
        weight=1.0, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=1.5),
            Band("good",        80, min=1.5, max=2.0),
            Band("fair",        60, min=2.0, max=2.5),
            Band("weak",        40, min=2.5, max=3.0),
            Band("very_weak",   20, min=3.0),
        ),
        benchmark_text="Good: <2%",
        explanation="Annual expenses (management fee + operating cost) as a share of AUM. Every basis point comes out of investor returns.",
    ),

    # --- Valuation -----------------------------------------------------------
    MetricRule(
        key="discount_to_nav", display_name="Discount to NAV", category="valuation",
        weight=1.5, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=15),
            Band("good",        80, min=8,  max=15),
            Band("fair",        60, min=2,  max=8),
            Band("weak",        40, min=-3, max=2),
            Band("very_weak",   20, max=-3),
        ),
        benchmark_text="Good: >8% discount | Negative = premium",
        explanation="How much cheaper (positive) or more expensive (negative) the market price is vs NAV. Bigger discount is generally more attractive for buyers.",
    ),
    MetricRule(
        key="price_to_nav", display_name="Price / NAV", category="valuation",
        weight=0.8, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=0.85),
            Band("good",        80, min=0.85, max=0.95),
            Band("fair",        60, min=0.95, max=1.02),
            Band("weak",        40, min=1.02, max=1.10),
            Band("very_weak",   20, min=1.10),
        ),
        benchmark_text="Attractive: <0.95x | Premium: >1x",
        explanation="Reciprocal view of the same information as discount-to-NAV; ratio format is useful for comparisons.",
    ),
)


PROFILE_OVERRIDES: dict[str, dict[str, float]] = {
    "growth":    {"nav_performance": 0.40, "distribution": 0.15, "cost": 0.10, "valuation": 0.35},
    "dividend":  {"distribution": 0.38, "nav_performance": 0.22, "cost": 0.10, "valuation": 0.30},
    "risk":      {"nav_performance": 0.28, "cost": 0.15, "distribution": 0.20, "valuation": 0.37},
    "valuation": {"valuation": 0.52, "nav_performance": 0.22, "distribution": 0.14, "cost": 0.12},
    "quality":   {"nav_performance": 0.34, "cost": 0.16, "distribution": 0.20, "valuation": 0.30},
    "balanced":  {},
}


MUTUAL_FUND_RULES = SectorRules(
    sector="Mutual Fund",
    methodology_version="1.0",
    categories=CATEGORIES,
    metrics=METRICS,
    profile_weight_overrides=PROFILE_OVERRIDES,
)
