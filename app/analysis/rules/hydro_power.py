"""Hydro Power scoring rules (methodology v1.0).

Hydropower is capital-intensive and project-driven: financials are dominated by
leverage during construction, then swing to strong margins and dividends once the
plant is commissioned and debt is paid down. The bands below reflect that reality
rather than mechanically reusing bank thresholds.

These thresholds are a starting reference informed by common Nepalese hydropower
indicators (typical PLF for run-of-river plants, D/E during project financing,
mature-plant ROE/NPM, PPA tariff economics with NEA). They are INTENTIONALLY
configurable so the methodology can be refined without code changes.

Nothing here should be treated as a regulatory recommendation or a substitute
for reading the company's financials.
"""
from app.analysis.rules.base import (
    Band,
    CategoryDefinition,
    Direction,
    MetricRule,
    SectorRules,
)


CATEGORIES = (
    CategoryDefinition("profitability",   "Profitability",   weight=0.20, facet="quality"),
    CategoryDefinition("growth",          "Growth",          weight=0.15, facet="quality"),
    CategoryDefinition("financial_risk",  "Financial Risk",  weight=0.20, facet="quality"),
    CategoryDefinition("operations",      "Operations",      weight=0.10, facet="quality"),
    CategoryDefinition("dividend",        "Dividend",        weight=0.10, facet="quality"),
    CategoryDefinition("valuation",       "Valuation",       weight=0.25, facet="valuation"),
)


METRICS = (
    # --- Profitability -------------------------------------------------------
    MetricRule(
        key="roe", display_name="Return on Equity", category="profitability",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=14, max=20),
            Band("fair",        60, min=10, max=14),
            Band("weak",        40, min=6,  max=10),
            Band("very_weak",   20, max=6),
        ),
        benchmark_text="Good: >14% | Excellent: >20%",
        explanation="Mature hydropower plants generate strong ROE once project debt is paid down. Newly commissioned projects may score lower here.",
    ),
    MetricRule(
        key="roa", display_name="Return on Assets", category="profitability",
        weight=0.7, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=8),
            Band("good",        80, min=5, max=8),
            Band("fair",        60, min=3, max=5),
            Band("weak",        40, min=1.5, max=3),
            Band("very_weak",   20, max=1.5),
        ),
        benchmark_text="Good: >5%",
        explanation="Hydropower is asset-heavy, so ROA runs lower than sectors like banking. Watch the trend more than the absolute number.",
    ),
    MetricRule(
        key="net_profit_margin", display_name="Net Profit Margin", category="profitability",
        weight=0.7, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=45),
            Band("good",        80, min=30, max=45),
            Band("fair",        60, min=20, max=30),
            Band("weak",        40, min=10, max=20),
            Band("very_weak",   20, max=10),
        ),
        benchmark_text="Good: >30%",
        explanation="Once operational, hydropower plants earn very high margins because fuel cost is zero and revenue comes from a fixed PPA tariff.",
    ),

    # --- Growth --------------------------------------------------------------
    MetricRule(
        key="net_profit_growth", display_name="Net Profit Growth (YoY)", category="growth",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=25),
            Band("good",        80, min=12, max=25),
            Band("fair",        60, min=3,  max=12),
            Band("weak",        40, min=-8, max=3),
            Band("very_weak",   20, max=-8),
        ),
        benchmark_text="Good: >12% YoY",
        explanation="Growth in hydropower comes from tariff revisions, new units coming online, or improved hydrology. Year-to-year swings are common because of monsoon variance.",
    ),
    MetricRule(
        key="eps_growth", display_name="EPS Growth (YoY)", category="growth",
        weight=0.9, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=8,  max=20),
            Band("fair",        60, min=2,  max=8),
            Band("weak",        40, min=-8, max=2),
            Band("very_weak",   20, max=-8),
        ),
        benchmark_text="Good: >8% YoY",
        explanation="EPS growth captures per-share earnings improvement — useful because bonus/right issues are common in this sector.",
    ),

    # --- Financial Risk (leverage & coverage) --------------------------------
    MetricRule(
        key="debt_to_equity", display_name="Debt-to-Equity", category="financial_risk",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=0.8),
            Band("good",        80, min=0.8, max=1.5),
            Band("fair",        60, min=1.5, max=2.5),
            Band("weak",        40, min=2.5, max=3.5),
            Band("very_weak",   20, min=3.5),
        ),
        benchmark_text="Healthier: <1.5x | Stressed: >3.5x",
        explanation="Hydropower projects are debt-funded, so leverage matters more than in most sectors. Very high D/E raises refinancing risk if hydrology or tariffs disappoint.",
    ),
    MetricRule(
        key="interest_coverage", display_name="Interest Coverage", category="financial_risk",
        weight=0.9, unit="x", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=6),
            Band("good",        80, min=4, max=6),
            Band("fair",        60, min=2.5, max=4),
            Band("weak",        40, min=1.5, max=2.5),
            Band("very_weak",   20, max=1.5),
        ),
        benchmark_text="Good: >4x | Danger: <1.5x",
        explanation="How many times operating profit covers interest expense. Below 1.5x, the company is barely earning enough to service its debt.",
    ),

    # --- Operations ----------------------------------------------------------
    MetricRule(
        key="plant_load_factor", display_name="Plant Load Factor", category="operations",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=60),
            Band("good",        80, min=50, max=60),
            Band("fair",        60, min=40, max=50),
            Band("weak",        40, min=30, max=40),
            Band("very_weak",   20, max=30),
        ),
        benchmark_text="Good: >50% (Nepali run-of-river typical range 40–60%)",
        explanation="PLF is the fraction of the plant's rated capacity actually generated over the year. Higher PLF means the plant is producing closer to its potential.",
    ),

    # --- Dividend ------------------------------------------------------------
    MetricRule(
        key="dividend_yield", display_name="Dividend Yield", category="dividend",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=8),
            Band("good",        80, min=5, max=8),
            Band("fair",        60, min=3, max=5),
            Band("weak",        40, min=1, max=3),
            Band("very_weak",   20, max=1),
        ),
        benchmark_text="Good: >5%",
        explanation="Mature hydropower companies with paid-down debt often pay meaningful dividends. Yield is total dividend (cash + bonus) over market price.",
    ),
    MetricRule(
        key="payout_ratio", display_name="Payout Ratio", category="dividend",
        weight=0.6, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=60),
            Band("good",        80, min=40, max=60),
            Band("fair",        60, min=20, max=40),
            Band("weak",        40, min=5,  max=20),
            Band("very_weak",   20, max=5),
        ),
        benchmark_text="Good: >40%",
        explanation="Share of earnings paid out as dividend. Newer projects reinvest more (low payout), matured ones return more to shareholders.",
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
        explanation="Lower P/E generally indicates cheaper valuation relative to earnings. Hydropower P/E is often elevated when the market prices in future project completion.",
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
        explanation="P/B compares market price to book value. Very high P/B may indicate an optimistically priced expansion story.",
    ),
)


PROFILE_OVERRIDES: dict[str, dict[str, float]] = {
    "growth":    {"growth": 0.30, "profitability": 0.20, "valuation": 0.15,
                  "financial_risk": 0.15, "operations": 0.10, "dividend": 0.10},
    "dividend":  {"dividend": 0.30, "profitability": 0.18, "financial_risk": 0.15,
                  "valuation": 0.15, "operations": 0.10, "growth": 0.12},
    "risk":      {"financial_risk": 0.30, "operations": 0.15, "profitability": 0.15,
                  "valuation": 0.15, "dividend": 0.10, "growth": 0.15},
    "valuation": {"valuation": 0.35, "profitability": 0.18, "growth": 0.12,
                  "financial_risk": 0.15, "operations": 0.10, "dividend": 0.10},
    "quality":   {"profitability": 0.24, "financial_risk": 0.22, "operations": 0.14,
                  "growth": 0.16, "dividend": 0.14, "valuation": 0.10},
    "balanced":  {},  # default weights
}


HYDRO_POWER_RULES = SectorRules(
    sector="Hydro Power",
    methodology_version="2.0",
    categories=CATEGORIES,
    metrics=METRICS,
    profile_weight_overrides=PROFILE_OVERRIDES,
)
