"""Commercial Bank scoring rules (methodology v1.0).

These thresholds are a starting reference informed by common Nepalese banking indicators
(NRB CAR floor, typical NPL bands, industry norms for ROE/ROA/NIM, etc.). They are
INTENTIONALLY configurable so the methodology can be refined without code changes.

Nothing here should be treated as an official regulatory recommendation.
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
    CategoryDefinition("asset_quality",     "Asset Quality",     weight=0.15, facet="quality"),
    CategoryDefinition("capital_strength",  "Capital Strength",  weight=0.12, facet="quality"),
    CategoryDefinition("efficiency",        "Efficiency",        weight=0.08, facet="quality"),
    CategoryDefinition("dividend",          "Dividend",          weight=0.07, facet="quality"),
    CategoryDefinition("valuation",         "Valuation",         weight=0.25, facet="valuation"),
)


METRICS = (
    # --- Profitability -------------------------------------------------------
    MetricRule(
        key="roe", display_name="Return on Equity", category="profitability",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=18),
            Band("good",        80, min=14, max=18),
            Band("fair",        60, min=10, max=14),
            Band("weak",        40, min=6,  max=10),
            Band("very_weak",   20, max=6),
        ),
        benchmark_text="Good: >14% | Excellent: >18%",
        explanation="ROE measures how efficiently the bank generates profit from shareholder equity. Higher is generally better.",
    ),
    MetricRule(
        key="roa", display_name="Return on Assets", category="profitability",
        weight=0.7, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=1.8),
            Band("good",        80, min=1.4, max=1.8),
            Band("fair",        60, min=1.0, max=1.4),
            Band("weak",        40, min=0.6, max=1.0),
            Band("very_weak",   20, max=0.6),
        ),
        benchmark_text="Good: >1.4% | Excellent: >1.8%",
        explanation="ROA shows how efficiently total assets are turned into profit — a broader efficiency measure than ROE.",
    ),
    MetricRule(
        key="nim", display_name="Net Interest Margin", category="profitability",
        weight=0.6, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=4.5),
            Band("good",        80, min=3.5, max=4.5),
            Band("fair",        60, min=2.8, max=3.5),
            Band("weak",        40, min=2.2, max=2.8),
            Band("very_weak",   20, max=2.2),
        ),
        benchmark_text="Good: >3.5%",
        explanation="Net Interest Margin reflects the spread between interest earned on loans and interest paid on deposits.",
    ),

    # --- Growth --------------------------------------------------------------
    MetricRule(
        key="net_profit_growth", display_name="Net Profit Growth (YoY)", category="growth",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=10, max=20),
            Band("fair",        60, min=3,  max=10),
            Band("weak",        40, min=-5, max=3),
            Band("very_weak",   20, max=-5),
        ),
        benchmark_text="Good: >10% YoY",
        explanation="Sustained profit growth suggests business momentum and can support future dividends and reinvestment.",
    ),
    MetricRule(
        key="eps_growth", display_name="EPS Growth (YoY)", category="growth",
        weight=0.9, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=18),
            Band("good",        80, min=8,  max=18),
            Band("fair",        60, min=2,  max=8),
            Band("weak",        40, min=-5, max=2),
            Band("very_weak",   20, max=-5),
        ),
        benchmark_text="Good: >8% YoY",
        explanation="EPS growth captures per-share earnings improvement — useful because share count can change via bonus/right issues.",
    ),

    # --- Asset Quality -------------------------------------------------------
    MetricRule(
        key="npl", display_name="Non-Performing Loans (NPL)", category="asset_quality",
        weight=1.0, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=2),
            Band("good",        80, min=2, max=3),
            Band("fair",        60, min=3, max=5),
            Band("weak",        40, min=5, max=6),
            Band("very_weak",   20, min=6),
        ),
        benchmark_text="Good: <3% | Excellent: <2%",
        explanation="Lower NPL indicates healthier loan books. High NPL forces additional provisioning and hurts distributable profit.",
    ),
    MetricRule(
        key="provision_coverage", display_name="Provision Coverage", category="asset_quality",
        weight=0.6, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=120),
            Band("good",        80, min=100, max=120),
            Band("fair",        60, min=80,  max=100),
            Band("weak",        40, min=60,  max=80),
            Band("very_weak",   20, max=60),
        ),
        benchmark_text="Good: >100%",
        explanation="Higher provision coverage means the bank has set aside more reserves against potentially bad loans.",
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
        explanation="CAR measures capital cushion against risk-weighted assets. Values close to the NRB floor leave little buffer.",
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
        benchmark_text="Regulatory ceiling ~90%; healthier well below",
        explanation="Lower CD ratio suggests more liquidity headroom and less pressure to raise expensive deposits.",
    ),

    # --- Efficiency ----------------------------------------------------------
    MetricRule(
        key="cost_of_fund", display_name="Cost of Fund", category="efficiency",
        weight=0.8, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=4.5),
            Band("good",        80, min=4.5, max=5.5),
            Band("fair",        60, min=5.5, max=6.5),
            Band("weak",        40, min=6.5, max=7.5),
            Band("very_weak",   20, min=7.5),
        ),
        benchmark_text="Good: <5.5%",
        explanation="Lower cost of funds improves the interest spread and supports profitability.",
    ),
    MetricRule(
        key="base_rate", display_name="Base Rate", category="efficiency",
        weight=0.4, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=6.5),
            Band("good",        80, min=6.5, max=7.5),
            Band("fair",        60, min=7.5, max=8.5),
            Band("weak",        40, min=8.5, max=9.5),
            Band("very_weak",   20, min=9.5),
        ),
        benchmark_text="Good: <7.5%",
        explanation="A lower base rate suggests cheaper funding and typically supports loan competitiveness.",
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
        explanation="Dividend yield relates total dividend (cash + bonus) to market price. Meaningful for income-focused investors.",
    ),
    MetricRule(
        key="distributable_profit_per_share", display_name="Distributable Profit / Share", category="dividend",
        weight=0.8, unit="Rs", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=25),
            Band("good",        80, min=15, max=25),
            Band("fair",        60, min=8,  max=15),
            Band("weak",        40, min=2,  max=8),
            Band("very_weak",   20, max=2),
        ),
        benchmark_text="Good: >Rs 15",
        explanation="Distributable profit per share indicates how much the company can realistically pay as dividend.",
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
        explanation="Lower P/E generally indicates cheaper valuation relative to earnings, subject to growth and risk.",
    ),
    MetricRule(
        key="pb", display_name="P/B Ratio", category="valuation",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=1.2),
            Band("good",        80, min=1.2, max=1.8),
            Band("fair",        60, min=1.8, max=2.5),
            Band("weak",        40, min=2.5, max=3.2),
            Band("very_weak",   20, min=3.2),
        ),
        benchmark_text="Attractive: <1.8x | Expensive: >2.5x",
        explanation="P/B compares market price to book value. Very high P/B may indicate the stock is optimistically priced.",
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
    "quality":   {"profitability": 0.22, "asset_quality": 0.20, "capital_strength": 0.16, "growth": 0.16,
                  "efficiency": 0.10, "dividend": 0.08, "valuation": 0.08},
    "balanced":  {},  # default weights
}


COMMERCIAL_BANK_RULES = SectorRules(
    sector="Commercial Banks",
    methodology_version="1.0",
    categories=CATEGORIES,
    metrics=METRICS,
    profile_weight_overrides=PROFILE_OVERRIDES,
)
