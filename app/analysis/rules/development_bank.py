"""Development Bank scoring rules (methodology v1.0).

Development banks are structurally similar to commercial banks but usually
smaller in balance-sheet size, with slightly higher NPL and cost-of-fund
tolerance. NRB CAR floor is 11% (same as commercial banks). Thresholds below
are intentionally slightly wider than the commercial-bank bands where sector
practice supports it.
"""
from app.analysis.rules.base import (
    Band,
    CategoryDefinition,
    Direction,
    MetricRule,
    SectorRules,
)


CATEGORIES = (
    CategoryDefinition("profitability",     "Profitability",     weight=0.18, facet="quality"),
    CategoryDefinition("growth",            "Growth",            weight=0.15, facet="quality"),
    CategoryDefinition("asset_quality",     "Asset Quality",     weight=0.17, facet="quality"),
    CategoryDefinition("capital_strength",  "Capital Strength",  weight=0.12, facet="quality"),
    CategoryDefinition("efficiency",        "Efficiency",        weight=0.08, facet="quality"),
    CategoryDefinition("dividend",          "Dividend",          weight=0.05, facet="quality"),
    CategoryDefinition("valuation",         "Valuation",         weight=0.25, facet="valuation"),
)


METRICS = (
    # --- Profitability -------------------------------------------------------
    MetricRule(
        key="roe", display_name="Return on Equity", category="profitability",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=16),
            Band("good",        80, min=12, max=16),
            Band("fair",        60, min=8,  max=12),
            Band("weak",        40, min=5,  max=8),
            Band("very_weak",   20, max=5),
        ),
        benchmark_text="Good: >12% | Excellent: >16%",
        explanation="ROE measures how efficiently the bank generates profit from shareholder equity.",
    ),
    MetricRule(
        key="roa", display_name="Return on Assets", category="profitability",
        weight=0.7, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=1.6),
            Band("good",        80, min=1.2, max=1.6),
            Band("fair",        60, min=0.8, max=1.2),
            Band("weak",        40, min=0.4, max=0.8),
            Band("very_weak",   20, max=0.4),
        ),
        benchmark_text="Good: >1.2%",
        explanation="ROA reflects how efficiently total assets are turned into profit.",
    ),
    MetricRule(
        key="nim", display_name="Net Interest Margin", category="profitability",
        weight=0.6, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=5),
            Band("good",        80, min=4,   max=5),
            Band("fair",        60, min=3,   max=4),
            Band("weak",        40, min=2.2, max=3),
            Band("very_weak",   20, max=2.2),
        ),
        benchmark_text="Good: >4%",
        explanation="NIM is the spread between interest earned and interest paid; typically slightly higher than commercial banks.",
    ),

    # --- Growth --------------------------------------------------------------
    MetricRule(
        key="net_profit_growth", display_name="Net Profit Growth (YoY)", category="growth",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=10, max=20),
            Band("fair",        60, min=3,  max=10),
            Band("weak",        40, min=-8, max=3),
            Band("very_weak",   20, max=-8),
        ),
        benchmark_text="Good: >10% YoY",
        explanation="Sustained profit growth suggests business momentum.",
    ),
    MetricRule(
        key="eps_growth", display_name="EPS Growth (YoY)", category="growth",
        weight=0.9, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=18),
            Band("good",        80, min=8,  max=18),
            Band("fair",        60, min=2,  max=8),
            Band("weak",        40, min=-8, max=2),
            Band("very_weak",   20, max=-8),
        ),
        benchmark_text="Good: >8% YoY",
        explanation="EPS growth captures per-share earnings improvement — useful because share count changes via bonus/right issues.",
    ),

    # --- Asset Quality -------------------------------------------------------
    MetricRule(
        key="npl", display_name="Non-Performing Loans (NPL)", category="asset_quality",
        weight=1.0, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=2.5),
            Band("good",        80, min=2.5, max=4),
            Band("fair",        60, min=4,   max=6),
            Band("weak",        40, min=6,   max=8),
            Band("very_weak",   20, min=8),
        ),
        benchmark_text="Good: <4% | Excellent: <2.5%",
        explanation="Development banks typically run slightly higher NPL than commercial banks; watch trend as much as absolute level.",
    ),
    MetricRule(
        key="provision_coverage", display_name="Provision Coverage", category="asset_quality",
        weight=0.6, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=110),
            Band("good",        80, min=90,  max=110),
            Band("fair",        60, min=70,  max=90),
            Band("weak",        40, min=55,  max=70),
            Band("very_weak",   20, max=55),
        ),
        benchmark_text="Good: >90%",
        explanation="Higher provision coverage means more reserves against potential bad loans.",
    ),

    # --- Capital Strength ----------------------------------------------------
    MetricRule(
        key="car", display_name="Capital Adequacy Ratio (CAR)", category="capital_strength",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=14),
            Band("good",        80, min=12.5, max=14),
            Band("fair",        60, min=11.5, max=12.5),
            Band("weak",        40, min=11,   max=11.5),
            Band("very_weak",   20, max=11),
        ),
        benchmark_text="NRB floor ~11%; Good: >12.5%",
        explanation="CAR measures the capital cushion against risk-weighted assets.",
    ),
    MetricRule(
        key="cd_ratio", display_name="CD Ratio", category="capital_strength",
        weight=0.4, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=82),
            Band("good",        80, min=82, max=85),
            Band("fair",        60, min=85, max=88),
            Band("weak",        40, min=88, max=90),
            Band("very_weak",   20, min=90),
        ),
        benchmark_text="Regulatory ceiling ~90%",
        explanation="Lower CD ratio suggests more liquidity headroom.",
    ),

    # --- Efficiency ----------------------------------------------------------
    MetricRule(
        key="cost_of_fund", display_name="Cost of Fund", category="efficiency",
        weight=0.8, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=5),
            Band("good",        80, min=5,   max=6),
            Band("fair",        60, min=6,   max=7.5),
            Band("weak",        40, min=7.5, max=8.5),
            Band("very_weak",   20, min=8.5),
        ),
        benchmark_text="Good: <6%",
        explanation="Lower cost of funds improves interest spread.",
    ),
    MetricRule(
        key="base_rate", display_name="Base Rate", category="efficiency",
        weight=0.4, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=7),
            Band("good",        80, min=7,   max=8),
            Band("fair",        60, min=8,   max=9),
            Band("weak",        40, min=9,   max=10),
            Band("very_weak",   20, min=10),
        ),
        benchmark_text="Good: <8%",
        explanation="A lower base rate suggests cheaper funding.",
    ),

    # --- Dividend ------------------------------------------------------------
    MetricRule(
        key="dividend_yield", display_name="Dividend Yield", category="dividend",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=8),
            Band("good",        80, min=5,   max=8),
            Band("fair",        60, min=3,   max=5),
            Band("weak",        40, min=1,   max=3),
            Band("very_weak",   20, max=1),
        ),
        benchmark_text="Good: >5%",
        explanation="Total dividend (cash + bonus) relative to market price.",
    ),
    MetricRule(
        key="distributable_profit_per_share", display_name="Distributable Profit / Share", category="dividend",
        weight=0.8, unit="Rs", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=12, max=20),
            Band("fair",        60, min=6,  max=12),
            Band("weak",        40, min=2,  max=6),
            Band("very_weak",   20, max=2),
        ),
        benchmark_text="Good: >Rs 12",
        explanation="How much the company can realistically pay as dividend.",
    ),

    # --- Valuation -----------------------------------------------------------
    MetricRule(
        key="pe", display_name="P/E Ratio", category="valuation",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=10),
            Band("good",        80, min=10, max=15),
            Band("fair",        60, min=15, max=20),
            Band("weak",        40, min=20, max=25),
            Band("very_weak",   20, min=25),
        ),
        benchmark_text="Attractive: <15x | Expensive: >20x",
        explanation="Lower P/E generally indicates cheaper valuation relative to earnings.",
    ),
    MetricRule(
        key="pb", display_name="P/B Ratio", category="valuation",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=1.0),
            Band("good",        80, min=1.0, max=1.5),
            Band("fair",        60, min=1.5, max=2.2),
            Band("weak",        40, min=2.2, max=3.0),
            Band("very_weak",   20, min=3.0),
        ),
        benchmark_text="Attractive: <1.5x | Expensive: >2.2x",
        explanation="P/B compares market price to book value.",
    ),
)


PROFILE_OVERRIDES: dict[str, dict[str, float]] = {
    "growth":    {"growth": 0.30, "profitability": 0.22, "valuation": 0.15,
                  "asset_quality": 0.13, "capital_strength": 0.10, "efficiency": 0.05, "dividend": 0.05},
    "dividend":  {"dividend": 0.30, "profitability": 0.18, "asset_quality": 0.13, "capital_strength": 0.12,
                  "valuation": 0.15, "efficiency": 0.06, "growth": 0.06},
    "risk":      {"asset_quality": 0.28, "capital_strength": 0.22, "profitability": 0.15,
                  "valuation": 0.15, "efficiency": 0.08, "dividend": 0.06, "growth": 0.06},
    "valuation": {"valuation": 0.35, "profitability": 0.16, "growth": 0.12, "asset_quality": 0.13,
                  "capital_strength": 0.10, "efficiency": 0.07, "dividend": 0.07},
    "quality":   {"profitability": 0.22, "asset_quality": 0.22, "capital_strength": 0.16, "growth": 0.16,
                  "efficiency": 0.08, "dividend": 0.08, "valuation": 0.08},
    "balanced":  {},
}


DEVELOPMENT_BANK_RULES = SectorRules(
    sector="Development Banks",
    methodology_version="2.0",
    categories=CATEGORIES,
    metrics=METRICS,
    profile_weight_overrides=PROFILE_OVERRIDES,
)
