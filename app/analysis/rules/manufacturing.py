"""Manufacturing & Processing scoring rules (methodology v1.0).

Nepali listed manufacturers span cement, cables, distillery, foods, etc.
Common thread: cyclical earnings, meaningful capex, working-capital drag,
and leverage exposure. This methodology therefore weights profitability
(operating margin, ROE) and financial risk (D/E, interest coverage) heavily,
with growth and dividend as supporting inputs.
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
    CategoryDefinition("growth",          "Growth",          weight=0.14, facet="quality"),
    CategoryDefinition("financial_risk",  "Financial Risk",  weight=0.18, facet="quality"),
    CategoryDefinition("efficiency",      "Efficiency",      weight=0.10, facet="quality"),
    CategoryDefinition("dividend",        "Dividend",        weight=0.06, facet="quality"),
    CategoryDefinition("valuation",       "Valuation",       weight=0.30, facet="valuation"),
)


METRICS = (
    # --- Profitability -------------------------------------------------------
    MetricRule(
        key="roe", display_name="Return on Equity", category="profitability",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=18),
            Band("good",        80, min=13, max=18),
            Band("fair",        60, min=8,  max=13),
            Band("weak",        40, min=4,  max=8),
            Band("very_weak",   20, max=4),
        ),
        benchmark_text="Good: >13%",
        explanation="ROE is a headline test for capital efficiency; cyclical downturns compress it temporarily.",
    ),
    MetricRule(
        key="roa", display_name="Return on Assets", category="profitability",
        weight=0.6, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=8),
            Band("good",        80, min=5, max=8),
            Band("fair",        60, min=3, max=5),
            Band("weak",        40, min=1, max=3),
            Band("very_weak",   20, max=1),
        ),
        benchmark_text="Good: >5%",
        explanation="Manufacturing carries substantial fixed assets; ROA reflects how productively they generate profit.",
    ),
    MetricRule(
        key="operating_margin", display_name="Operating Margin", category="profitability",
        weight=0.8, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=13, max=20),
            Band("fair",        60, min=8,  max=13),
            Band("weak",        40, min=3,  max=8),
            Band("very_weak",   20, max=3),
        ),
        benchmark_text="Good: >13%",
        explanation="Operating margin isolates core business profitability from financing and tax noise.",
    ),
    MetricRule(
        key="net_profit_margin", display_name="Net Profit Margin", category="profitability",
        weight=0.5, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=15),
            Band("good",        80, min=10, max=15),
            Band("fair",        60, min=6,  max=10),
            Band("weak",        40, min=2,  max=6),
            Band("very_weak",   20, max=2),
        ),
        benchmark_text="Good: >10%",
        explanation="Bottom-line margin after all costs, interest, and tax.",
    ),

    # --- Growth --------------------------------------------------------------
    MetricRule(
        key="revenue_growth", display_name="Revenue Growth (YoY)", category="growth",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=18),
            Band("good",        80, min=8,  max=18),
            Band("fair",        60, min=2,  max=8),
            Band("weak",        40, min=-8, max=2),
            Band("very_weak",   20, max=-8),
        ),
        benchmark_text="Good: >8% YoY",
        explanation="Top-line growth reflects volume and pricing strength; cyclical dips are normal but sustained decline is a red flag.",
    ),
    MetricRule(
        key="net_profit_growth", display_name="Net Profit Growth (YoY)", category="growth",
        weight=0.8, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=25),
            Band("good",        80, min=10, max=25),
            Band("fair",        60, min=2,  max=10),
            Band("weak",        40, min=-15, max=2),
            Band("very_weak",   20, max=-15),
        ),
        benchmark_text="Good: >10% YoY",
        explanation="Manufacturing profit growth can swing sharply with input costs and demand cycles.",
    ),
    MetricRule(
        key="eps_growth", display_name="EPS Growth (YoY)", category="growth",
        weight=0.7, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=8,  max=20),
            Band("fair",        60, min=0,  max=8),
            Band("weak",        40, min=-15, max=0),
            Band("very_weak",   20, max=-15),
        ),
        benchmark_text="Good: >8% YoY",
        explanation="EPS growth captures per-share earnings improvement.",
    ),

    # --- Financial Risk ------------------------------------------------------
    MetricRule(
        key="debt_to_equity", display_name="Debt-to-Equity", category="financial_risk",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=0.5),
            Band("good",        80, min=0.5, max=1.0),
            Band("fair",        60, min=1.0, max=1.8),
            Band("weak",        40, min=1.8, max=2.5),
            Band("very_weak",   20, min=2.5),
        ),
        benchmark_text="Healthier: <1x | Stressed: >2.5x",
        explanation="Higher leverage amplifies both upside and downside; too much D/E leaves little cushion in downturns.",
    ),
    MetricRule(
        key="interest_coverage", display_name="Interest Coverage", category="financial_risk",
        weight=0.9, unit="x", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=8),
            Band("good",        80, min=5, max=8),
            Band("fair",        60, min=3, max=5),
            Band("weak",        40, min=1.5, max=3),
            Band("very_weak",   20, max=1.5),
        ),
        benchmark_text="Good: >5x | Danger: <1.5x",
        explanation="How many times operating profit covers interest expense. Below 1.5x the company is barely servicing its debt.",
    ),
    MetricRule(
        key="current_ratio", display_name="Current Ratio", category="financial_risk",
        weight=0.5, unit="x", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=2),
            Band("good",        80, min=1.5, max=2),
            Band("fair",        60, min=1.2, max=1.5),
            Band("weak",        40, min=1.0, max=1.2),
            Band("very_weak",   20, max=1.0),
        ),
        benchmark_text="Good: >1.5x | Weak: <1x",
        explanation="Current assets over current liabilities. Below 1x suggests short-term liquidity strain.",
    ),

    # --- Efficiency ----------------------------------------------------------
    MetricRule(
        key="asset_turnover", display_name="Asset Turnover", category="efficiency",
        weight=1.0, unit="x", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=1.2),
            Band("good",        80, min=0.9, max=1.2),
            Band("fair",        60, min=0.6, max=0.9),
            Band("weak",        40, min=0.4, max=0.6),
            Band("very_weak",   20, max=0.4),
        ),
        benchmark_text="Good: >0.9x",
        explanation="Revenue generated per unit of assets — a simple efficiency test for manufacturers.",
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
    MetricRule(
        key="payout_ratio", display_name="Payout Ratio", category="dividend",
        weight=0.4, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=40),
            Band("good",        80, min=25, max=40),
            Band("fair",        60, min=15, max=25),
            Band("weak",        40, min=5,  max=15),
            Band("very_weak",   20, max=5),
        ),
        benchmark_text="Good: >25%",
        explanation="Share of earnings paid as dividend. Very low payout is fine for growing capex-heavy firms.",
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
            Band("excellent",  100, max=1.5),
            Band("good",        80, min=1.5, max=2.5),
            Band("fair",        60, min=2.5, max=4),
            Band("weak",        40, min=4,   max=6),
            Band("very_weak",   20, min=6),
        ),
        benchmark_text="Attractive: <2.5x | Expensive: >4x",
        explanation="P/B compares market price to book value.",
    ),
)


PROFILE_OVERRIDES: dict[str, dict[str, float]] = {
    "growth":    {"growth": 0.28, "profitability": 0.22, "valuation": 0.15,
                  "financial_risk": 0.15, "efficiency": 0.10, "dividend": 0.10},
    "dividend":  {"dividend": 0.28, "profitability": 0.20, "financial_risk": 0.15,
                  "valuation": 0.15, "efficiency": 0.10, "growth": 0.12},
    "risk":      {"financial_risk": 0.32, "profitability": 0.18, "valuation": 0.15,
                  "efficiency": 0.12, "dividend": 0.10, "growth": 0.13},
    "valuation": {"valuation": 0.38, "profitability": 0.18, "growth": 0.12,
                  "financial_risk": 0.14, "efficiency": 0.08, "dividend": 0.10},
    "quality":   {"profitability": 0.28, "financial_risk": 0.20, "efficiency": 0.14,
                  "growth": 0.14, "dividend": 0.10, "valuation": 0.14},
    "balanced":  {},
}


MANUFACTURING_RULES = SectorRules(
    sector="Manufacturing And Processing",
    methodology_version="1.0",
    categories=CATEGORIES,
    metrics=METRICS,
    profile_weight_overrides=PROFILE_OVERRIDES,
)
