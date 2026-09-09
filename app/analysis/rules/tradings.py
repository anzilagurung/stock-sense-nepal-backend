"""Tradings sector scoring rules (methodology v1.0).

Only a handful of listed trading companies (e.g. petroleum distributors,
merchandising outfits). Financials look like thin-margin, high-turnover
businesses: modest operating margins, high asset turnover, and working
capital that swings meaningfully with commodity prices. Interest coverage
and leverage matter because inventory financing is a routine part of the
business.
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
    CategoryDefinition("financial_risk",  "Financial Risk",  weight=0.18, facet="quality"),
    CategoryDefinition("efficiency",      "Efficiency",      weight=0.12, facet="quality"),
    CategoryDefinition("dividend",        "Dividend",        weight=0.08, facet="quality"),
    CategoryDefinition("valuation",       "Valuation",       weight=0.30, facet="valuation"),
)


METRICS = (
    # --- Profitability -------------------------------------------------------
    MetricRule(
        key="roe", display_name="Return on Equity", category="profitability",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=16),
            Band("good",        80, min=11, max=16),
            Band("fair",        60, min=6,  max=11),
            Band("weak",        40, min=3,  max=6),
            Band("very_weak",   20, max=3),
        ),
        benchmark_text="Good: >11%",
        explanation="Trading businesses lean on high turnover to generate ROE despite thin margins.",
    ),
    MetricRule(
        key="operating_margin", display_name="Operating Margin", category="profitability",
        weight=0.8, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=8),
            Band("good",        80, min=5, max=8),
            Band("fair",        60, min=3, max=5),
            Band("weak",        40, min=1, max=3),
            Band("very_weak",   20, max=1),
        ),
        benchmark_text="Good: >5%",
        explanation="Trading margins are structurally thin; sustained margin above sector norms indicates pricing power or scale advantages.",
    ),
    MetricRule(
        key="net_profit_margin", display_name="Net Profit Margin", category="profitability",
        weight=0.5, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=5),
            Band("good",        80, min=3, max=5),
            Band("fair",        60, min=1.5, max=3),
            Band("weak",        40, min=0.5, max=1.5),
            Band("very_weak",   20, max=0.5),
        ),
        benchmark_text="Good: >3%",
        explanation="Bottom-line margin after all costs; thin margins are normal but negative margin is a serious red flag.",
    ),

    # --- Growth --------------------------------------------------------------
    MetricRule(
        key="revenue_growth", display_name="Revenue Growth (YoY)", category="growth",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=8,  max=20),
            Band("fair",        60, min=2,  max=8),
            Band("weak",        40, min=-8, max=2),
            Band("very_weak",   20, max=-8),
        ),
        benchmark_text="Good: >8% YoY",
        explanation="Revenue growth reflects volume + price; commodity price swings can dominate.",
    ),
    MetricRule(
        key="net_profit_growth", display_name="Net Profit Growth (YoY)", category="growth",
        weight=0.7, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=8,  max=20),
            Band("fair",        60, min=0,  max=8),
            Band("weak",        40, min=-15, max=0),
            Band("very_weak",   20, max=-15),
        ),
        benchmark_text="Good: >8% YoY",
        explanation="Profit growth can lag or lead revenue depending on inventory positioning and margin cycles.",
    ),

    # --- Financial Risk ------------------------------------------------------
    MetricRule(
        key="debt_to_equity", display_name="Debt-to-Equity", category="financial_risk",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=0.7),
            Band("good",        80, min=0.7, max=1.3),
            Band("fair",        60, min=1.3, max=2.0),
            Band("weak",        40, min=2.0, max=3.0),
            Band("very_weak",   20, min=3.0),
        ),
        benchmark_text="Healthier: <1.3x | Stressed: >3x",
        explanation="Trading firms use debt for inventory; moderate leverage is normal but excessive D/E raises refinance risk.",
    ),
    MetricRule(
        key="interest_coverage", display_name="Interest Coverage", category="financial_risk",
        weight=0.8, unit="x", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=6),
            Band("good",        80, min=4, max=6),
            Band("fair",        60, min=2.5, max=4),
            Band("weak",        40, min=1.5, max=2.5),
            Band("very_weak",   20, max=1.5),
        ),
        benchmark_text="Good: >4x | Danger: <1.5x",
        explanation="How comfortably operating profit covers interest; critical for inventory-financed businesses.",
    ),
    MetricRule(
        key="current_ratio", display_name="Current Ratio", category="financial_risk",
        weight=0.5, unit="x", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=1.6),
            Band("good",        80, min=1.3, max=1.6),
            Band("fair",        60, min=1.1, max=1.3),
            Band("weak",        40, min=0.9, max=1.1),
            Band("very_weak",   20, max=0.9),
        ),
        benchmark_text="Good: >1.3x",
        explanation="Short-term liquidity cushion; important given payable/receivable swings.",
    ),

    # --- Efficiency ----------------------------------------------------------
    MetricRule(
        key="asset_turnover", display_name="Asset Turnover", category="efficiency",
        weight=1.0, unit="x", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=2.5),
            Band("good",        80, min=1.7, max=2.5),
            Band("fair",        60, min=1.1, max=1.7),
            Band("weak",        40, min=0.7, max=1.1),
            Band("very_weak",   20, max=0.7),
        ),
        benchmark_text="Good: >1.7x",
        explanation="Trading businesses must recycle assets quickly to earn returns despite thin margins.",
    ),
    MetricRule(
        key="inventory_turnover", display_name="Inventory Turnover", category="efficiency",
        weight=0.6, unit="x", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=8),
            Band("good",        80, min=5, max=8),
            Band("fair",        60, min=3, max=5),
            Band("weak",        40, min=1.5, max=3),
            Band("very_weak",   20, max=1.5),
        ),
        benchmark_text="Good: >5x",
        explanation="How many times inventory turns over per year. Faster turnover means less capital tied up and less obsolescence risk.",
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
        explanation="Total dividend (cash + bonus) relative to market price.",
    ),

    # --- Valuation -----------------------------------------------------------
    MetricRule(
        key="pe", display_name="P/E Ratio", category="valuation",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=10),
            Band("good",        80, min=10, max=15),
            Band("fair",        60, min=15, max=22),
            Band("weak",        40, min=22, max=32),
            Band("very_weak",   20, min=32),
        ),
        benchmark_text="Attractive: <15x | Expensive: >22x",
        explanation="Trading multiples tend to be modest given thin margins and low growth.",
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
    "growth":    {"growth": 0.28, "profitability": 0.22, "valuation": 0.15,
                  "financial_risk": 0.15, "efficiency": 0.12, "dividend": 0.08},
    "dividend":  {"dividend": 0.28, "profitability": 0.20, "financial_risk": 0.15,
                  "valuation": 0.15, "efficiency": 0.10, "growth": 0.12},
    "risk":      {"financial_risk": 0.32, "profitability": 0.18, "valuation": 0.15,
                  "efficiency": 0.13, "dividend": 0.10, "growth": 0.12},
    "valuation": {"valuation": 0.38, "profitability": 0.18, "growth": 0.10,
                  "financial_risk": 0.16, "efficiency": 0.10, "dividend": 0.08},
    "quality":   {"profitability": 0.24, "financial_risk": 0.22, "efficiency": 0.18,
                  "growth": 0.12, "dividend": 0.10, "valuation": 0.14},
    "balanced":  {},
}


TRADINGS_RULES = SectorRules(
    sector="Tradings",
    methodology_version="2.0",
    categories=CATEGORIES,
    metrics=METRICS,
    profile_weight_overrides=PROFILE_OVERRIDES,
)
