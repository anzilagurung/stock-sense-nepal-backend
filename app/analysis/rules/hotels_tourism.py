"""Hotels & Tourism scoring rules (methodology v1.0).

Includes hotels, resorts, and tourism-adjacent businesses (e.g. cable cars).
Earnings are highly seasonal and sensitive to tourist arrivals, so this
methodology weights leverage/coverage heavily (a hotel with 3x D/E in a
weak season is fragile) and moderates the growth weight to smooth out
year-to-year seasonality.
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
    CategoryDefinition("growth",          "Growth",          weight=0.12, facet="quality"),
    CategoryDefinition("financial_risk",  "Financial Risk",  weight=0.22, facet="quality"),
    CategoryDefinition("operations",      "Operations",      weight=0.08, facet="quality"),
    CategoryDefinition("dividend",        "Dividend",        weight=0.08, facet="quality"),
    CategoryDefinition("valuation",       "Valuation",       weight=0.30, facet="valuation"),
)


METRICS = (
    # --- Profitability -------------------------------------------------------
    MetricRule(
        key="roe", display_name="Return on Equity", category="profitability",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=14),
            Band("good",        80, min=9, max=14),
            Band("fair",        60, min=5, max=9),
            Band("weak",        40, min=2, max=5),
            Band("very_weak",   20, max=2),
        ),
        benchmark_text="Good: >9%",
        explanation="Hotels are asset-heavy so ROE runs lower than services or manufacturing.",
    ),
    MetricRule(
        key="roa", display_name="Return on Assets", category="profitability",
        weight=0.6, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=6),
            Band("good",        80, min=4, max=6),
            Band("fair",        60, min=2, max=4),
            Band("weak",        40, min=0.5, max=2),
            Band("very_weak",   20, max=0.5),
        ),
        benchmark_text="Good: >4%",
        explanation="Asset-heavy businesses naturally show lower ROA; watch the trend.",
    ),
    MetricRule(
        key="operating_margin", display_name="Operating Margin", category="profitability",
        weight=0.8, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=25),
            Band("good",        80, min=15, max=25),
            Band("fair",        60, min=8,  max=15),
            Band("weak",        40, min=3,  max=8),
            Band("very_weak",   20, max=3),
        ),
        benchmark_text="Good: >15%",
        explanation="Well-run hotels earn strong operating margins during peak season; weak margins signal cost control problems.",
    ),

    # --- Growth --------------------------------------------------------------
    MetricRule(
        key="revenue_growth", display_name="Revenue Growth (YoY)", category="growth",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=10, max=20),
            Band("fair",        60, min=3,  max=10),
            Band("weak",        40, min=-10, max=3),
            Band("very_weak",   20, max=-10),
        ),
        benchmark_text="Good: >10% YoY",
        explanation="Revenue growth in hospitality depends on tourist arrivals and ARR; volatile but trend matters.",
    ),
    MetricRule(
        key="net_profit_growth", display_name="Net Profit Growth (YoY)", category="growth",
        weight=0.7, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=30),
            Band("good",        80, min=12, max=30),
            Band("fair",        60, min=0,  max=12),
            Band("weak",        40, min=-20, max=0),
            Band("very_weak",   20, max=-20),
        ),
        benchmark_text="Good: >12% YoY",
        explanation="Profit swings are amplified by operating leverage — small revenue moves produce large profit moves.",
    ),

    # --- Financial Risk ------------------------------------------------------
    MetricRule(
        key="debt_to_equity", display_name="Debt-to-Equity", category="financial_risk",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=0.6),
            Band("good",        80, min=0.6, max=1.2),
            Band("fair",        60, min=1.2, max=2.0),
            Band("weak",        40, min=2.0, max=3.0),
            Band("very_weak",   20, min=3.0),
        ),
        benchmark_text="Healthier: <1.2x | Stressed: >3x",
        explanation="Hotel-project debt loads can be crippling during off-season or shocks; lower D/E is safer.",
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
        explanation="How comfortably operating profit covers interest; hotels swing between comfortable and stressed with the tourism cycle.",
    ),
    MetricRule(
        key="current_ratio", display_name="Current Ratio", category="financial_risk",
        weight=0.4, unit="x", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=1.5),
            Band("good",        80, min=1.2, max=1.5),
            Band("fair",        60, min=1.0, max=1.2),
            Band("weak",        40, min=0.8, max=1.0),
            Band("very_weak",   20, max=0.8),
        ),
        benchmark_text="Good: >1.2x",
        explanation="Short-term liquidity cushion; hotels with poor liquidity can be squeezed during weak seasons.",
    ),

    # --- Operations ----------------------------------------------------------
    MetricRule(
        key="occupancy_rate", display_name="Occupancy Rate", category="operations",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=70),
            Band("good",        80, min=60, max=70),
            Band("fair",        60, min=50, max=60),
            Band("weak",        40, min=40, max=50),
            Band("very_weak",   20, max=40),
        ),
        benchmark_text="Good: >60%",
        explanation="Room-nights sold over room-nights available. The single most important hospitality KPI.",
    ),

    # --- Dividend ------------------------------------------------------------
    MetricRule(
        key="dividend_yield", display_name="Dividend Yield", category="dividend",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=5),
            Band("good",        80, min=3, max=5),
            Band("fair",        60, min=1.5, max=3),
            Band("weak",        40, min=0.3, max=1.5),
            Band("very_weak",   20, max=0.3),
        ),
        benchmark_text="Good: >3%",
        explanation="Total dividend (cash + bonus) relative to market price. Dividends often paused during weak years.",
    ),

    # --- Valuation -----------------------------------------------------------
    MetricRule(
        key="pe", display_name="P/E Ratio", category="valuation",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=15),
            Band("good",        80, min=15, max=22),
            Band("fair",        60, min=22, max=30),
            Band("weak",        40, min=30, max=45),
            Band("very_weak",   20, min=45),
        ),
        benchmark_text="Attractive: <22x | Expensive: >30x",
        explanation="Hospitality P/E can look distorted during transition periods; consider through-cycle earnings.",
    ),
    MetricRule(
        key="pb", display_name="P/B Ratio", category="valuation",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=1.5),
            Band("good",        80, min=1.5, max=2.5),
            Band("fair",        60, min=2.5, max=3.5),
            Band("weak",        40, min=3.5, max=5),
            Band("very_weak",   20, min=5),
        ),
        benchmark_text="Attractive: <2.5x | Expensive: >3.5x",
        explanation="P/B compares price to book value; useful for asset-heavy hotel companies.",
    ),
)


PROFILE_OVERRIDES: dict[str, dict[str, float]] = {
    "growth":    {"growth": 0.28, "profitability": 0.22, "valuation": 0.15,
                  "financial_risk": 0.17, "operations": 0.08, "dividend": 0.10},
    "dividend":  {"dividend": 0.25, "profitability": 0.20, "financial_risk": 0.18,
                  "valuation": 0.15, "operations": 0.10, "growth": 0.12},
    "risk":      {"financial_risk": 0.35, "profitability": 0.18, "valuation": 0.15,
                  "operations": 0.10, "dividend": 0.10, "growth": 0.12},
    "valuation": {"valuation": 0.38, "profitability": 0.18, "growth": 0.10,
                  "financial_risk": 0.18, "operations": 0.08, "dividend": 0.08},
    "quality":   {"profitability": 0.26, "financial_risk": 0.22, "operations": 0.12,
                  "growth": 0.12, "dividend": 0.12, "valuation": 0.16},
    "balanced":  {},
}


HOTELS_TOURISM_RULES = SectorRules(
    sector="Hotels And Tourism",
    methodology_version="1.0",
    categories=CATEGORIES,
    metrics=METRICS,
    profile_weight_overrides=PROFILE_OVERRIDES,
)
