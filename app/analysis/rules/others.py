"""Others sector scoring rules (methodology v1.0).

"Others" is a residual NEPSE bucket that includes a mix of businesses that
don't fit the primary sector taxonomy: reinsurance (HRL), Citizen Investment
Trust (CIT), Nepal Stock Exchange itself (NEPSE), NEPSE-related utilities,
and a couple of holding-adjacent names.

Because the sub-mix is heterogeneous, this methodology is deliberately
generic: profitability, growth, leverage, dividend, and valuation. Bands are
tuned to be somewhat forgiving so a diverse set of business models can still
be reasoned about, and the sector should be re-split into narrower buckets
(e.g. dedicated Reinsurance rules) as data quality improves.
"""
from app.analysis.rules.base import (
    Band,
    CategoryDefinition,
    Direction,
    MetricRule,
    SectorRules,
)


CATEGORIES = (
    CategoryDefinition("profitability",   "Profitability",   weight=0.22, facet="quality"),
    CategoryDefinition("growth",          "Growth",          weight=0.15, facet="quality"),
    CategoryDefinition("financial_risk",  "Financial Risk",  weight=0.18, facet="quality"),
    CategoryDefinition("dividend",        "Dividend",        weight=0.10, facet="quality"),
    CategoryDefinition("valuation",       "Valuation",       weight=0.35, facet="valuation"),
)


METRICS = (
    # --- Profitability -------------------------------------------------------
    MetricRule(
        key="roe", display_name="Return on Equity", category="profitability",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=15),
            Band("good",        80, min=10, max=15),
            Band("fair",        60, min=6,  max=10),
            Band("weak",        40, min=3,  max=6),
            Band("very_weak",   20, max=3),
        ),
        benchmark_text="Good: >10%",
        explanation="ROE captures how efficiently the company generates profit from shareholder equity.",
    ),
    MetricRule(
        key="roa", display_name="Return on Assets", category="profitability",
        weight=0.6, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=5),
            Band("good",        80, min=3, max=5),
            Band("fair",        60, min=1.5, max=3),
            Band("weak",        40, min=0.5, max=1.5),
            Band("very_weak",   20, max=0.5),
        ),
        benchmark_text="Good: >3%",
        explanation="ROA reflects how efficiently total assets are turned into profit.",
    ),
    MetricRule(
        key="net_profit_margin", display_name="Net Profit Margin", category="profitability",
        weight=0.5, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=12, max=20),
            Band("fair",        60, min=6,  max=12),
            Band("weak",        40, min=2,  max=6),
            Band("very_weak",   20, max=2),
        ),
        benchmark_text="Good: >12%",
        explanation="Bottom-line margin; wide bands because sub-industries in this bucket differ materially.",
    ),

    # --- Growth --------------------------------------------------------------
    MetricRule(
        key="net_profit_growth", display_name="Net Profit Growth (YoY)", category="growth",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=8,  max=20),
            Band("fair",        60, min=0,  max=8),
            Band("weak",        40, min=-15, max=0),
            Band("very_weak",   20, max=-15),
        ),
        benchmark_text="Good: >8% YoY",
        explanation="Sustained profit growth suggests business momentum.",
    ),
    MetricRule(
        key="eps_growth", display_name="EPS Growth (YoY)", category="growth",
        weight=0.7, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=15),
            Band("good",        80, min=5,  max=15),
            Band("fair",        60, min=-3, max=5),
            Band("weak",        40, min=-15, max=-3),
            Band("very_weak",   20, max=-15),
        ),
        benchmark_text="Good: >5% YoY",
        explanation="EPS growth captures per-share earnings improvement.",
    ),

    # --- Financial Risk ------------------------------------------------------
    MetricRule(
        key="debt_to_equity", display_name="Debt-to-Equity", category="financial_risk",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=0.4),
            Band("good",        80, min=0.4, max=1.0),
            Band("fair",        60, min=1.0, max=1.8),
            Band("weak",        40, min=1.8, max=2.8),
            Band("very_weak",   20, min=2.8),
        ),
        benchmark_text="Healthier: <1x | Stressed: >2.8x",
        explanation="Financial leverage; the appropriate level varies by business model within this bucket.",
    ),
    MetricRule(
        key="interest_coverage", display_name="Interest Coverage", category="financial_risk",
        weight=0.6, unit="x", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=6),
            Band("good",        80, min=4, max=6),
            Band("fair",        60, min=2.5, max=4),
            Band("weak",        40, min=1.5, max=2.5),
            Band("very_weak",   20, max=1.5),
        ),
        benchmark_text="Good: >4x | Danger: <1.5x",
        explanation="How comfortably operating profit covers interest expense.",
    ),

    # --- Dividend ------------------------------------------------------------
    MetricRule(
        key="dividend_yield", display_name="Dividend Yield", category="dividend",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=6),
            Band("good",        80, min=4, max=6),
            Band("fair",        60, min=2, max=4),
            Band("weak",        40, min=0.5, max=2),
            Band("very_weak",   20, max=0.5),
        ),
        benchmark_text="Good: >4%",
        explanation="Cash + bonus dividend relative to market price.",
    ),

    # --- Valuation -----------------------------------------------------------
    MetricRule(
        key="pe", display_name="P/E Ratio", category="valuation",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=12),
            Band("good",        80, min=12, max=18),
            Band("fair",        60, min=18, max=25),
            Band("weak",        40, min=25, max=35),
            Band("very_weak",   20, min=35),
        ),
        benchmark_text="Attractive: <18x | Expensive: >25x",
        explanation="Lower P/E generally indicates cheaper valuation relative to earnings.",
    ),
    MetricRule(
        key="pb", display_name="P/B Ratio", category="valuation",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=1.2),
            Band("good",        80, min=1.2, max=2.0),
            Band("fair",        60, min=2.0, max=3.0),
            Band("weak",        40, min=3.0, max=4.5),
            Band("very_weak",   20, min=4.5),
        ),
        benchmark_text="Attractive: <2x | Expensive: >3x",
        explanation="P/B compares market price to book value.",
    ),
)


PROFILE_OVERRIDES: dict[str, dict[str, float]] = {
    "growth":    {"growth": 0.28, "profitability": 0.22, "valuation": 0.18,
                  "financial_risk": 0.15, "dividend": 0.17},
    "dividend":  {"dividend": 0.30, "profitability": 0.20, "financial_risk": 0.15,
                  "valuation": 0.20, "growth": 0.15},
    "risk":      {"financial_risk": 0.32, "profitability": 0.20, "valuation": 0.18,
                  "dividend": 0.15, "growth": 0.15},
    "valuation": {"valuation": 0.42, "profitability": 0.18, "growth": 0.10,
                  "financial_risk": 0.18, "dividend": 0.12},
    "quality":   {"profitability": 0.28, "financial_risk": 0.22, "growth": 0.14,
                  "dividend": 0.14, "valuation": 0.22},
    "balanced":  {},
}


OTHERS_RULES = SectorRules(
    sector="Others",
    methodology_version="1.0",
    categories=CATEGORIES,
    metrics=METRICS,
    profile_weight_overrides=PROFILE_OVERRIDES,
)
