"""Investment company scoring rules (methodology v1.0).

Listed "Investment" companies in Nepal are typically holding vehicles whose
book is dominated by equity stakes in other companies (bank shares, promoter
stakes, subsidiaries). Their earnings are lumpy — driven by dividend income,
fair-value gains, and one-off disposals. Book value is the anchor and
discount/premium to NAV is often more informative than PE.
"""
from app.analysis.rules.base import (
    Band,
    CategoryDefinition,
    Direction,
    MetricRule,
    SectorRules,
)


CATEGORIES = (
    CategoryDefinition("profitability",   "Profitability",   weight=0.18, facet="quality"),
    CategoryDefinition("growth",          "Growth",          weight=0.12, facet="quality"),
    CategoryDefinition("balance_sheet",   "Balance Sheet",   weight=0.18, facet="quality"),
    CategoryDefinition("dividend",        "Dividend",        weight=0.12, facet="quality"),
    CategoryDefinition("valuation",       "Valuation",       weight=0.40, facet="valuation"),
)


METRICS = (
    # --- Profitability -------------------------------------------------------
    MetricRule(
        key="roe", display_name="Return on Equity", category="profitability",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=14),
            Band("good",        80, min=9,  max=14),
            Band("fair",        60, min=5,  max=9),
            Band("weak",        40, min=2,  max=5),
            Band("very_weak",   20, max=2),
        ),
        benchmark_text="Good: >9%",
        explanation="For investment holding companies, ROE swings with fair-value moves on the portfolio.",
    ),
    MetricRule(
        key="roa", display_name="Return on Assets", category="profitability",
        weight=0.5, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=6),
            Band("good",        80, min=4, max=6),
            Band("fair",        60, min=2, max=4),
            Band("weak",        40, min=0.5, max=2),
            Band("very_weak",   20, max=0.5),
        ),
        benchmark_text="Good: >4%",
        explanation="Returns on the underlying portfolio, net of holding-company costs.",
    ),

    # --- Growth --------------------------------------------------------------
    MetricRule(
        key="net_profit_growth", display_name="Net Profit Growth (YoY)", category="growth",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=25),
            Band("good",        80, min=10, max=25),
            Band("fair",        60, min=0,  max=10),
            Band("weak",        40, min=-20, max=0),
            Band("very_weak",   20, max=-20),
        ),
        benchmark_text="Good: >10% YoY",
        explanation="Profit growth is lumpy — one-off disposals or fair-value swings can dominate.",
    ),
    MetricRule(
        key="eps_growth", display_name="EPS Growth (YoY)", category="growth",
        weight=0.6, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=15),
            Band("good",        80, min=5, max=15),
            Band("fair",        60, min=-5, max=5),
            Band("weak",        40, min=-20, max=-5),
            Band("very_weak",   20, max=-20),
        ),
        benchmark_text="Good: >5% YoY",
        explanation="EPS growth captures per-share earnings improvement.",
    ),

    # --- Balance Sheet -------------------------------------------------------
    MetricRule(
        key="debt_to_equity", display_name="Debt-to-Equity", category="balance_sheet",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=0.3),
            Band("good",        80, min=0.3, max=0.7),
            Band("fair",        60, min=0.7, max=1.2),
            Band("weak",        40, min=1.2, max=2.0),
            Band("very_weak",   20, min=2.0),
        ),
        benchmark_text="Healthier: <0.7x",
        explanation="Investment companies with high leverage magnify portfolio moves in both directions — lower is safer.",
    ),
    MetricRule(
        key="bvps", display_name="Book Value / Share", category="balance_sheet",
        weight=0.6, unit="Rs", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=200),
            Band("good",        80, min=140, max=200),
            Band("fair",        60, min=100, max=140),
            Band("weak",        40, min=70,  max=100),
            Band("very_weak",   20, max=70),
        ),
        benchmark_text="Good: >Rs 140",
        explanation="Book value per share; the anchor of intrinsic value for holding companies.",
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
        explanation="Holding-company dividends often mirror dividend income from the underlying portfolio.",
    ),
    MetricRule(
        key="payout_ratio", display_name="Payout Ratio", category="dividend",
        weight=0.4, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=50),
            Band("good",        80, min=30, max=50),
            Band("fair",        60, min=15, max=30),
            Band("weak",        40, min=5,  max=15),
            Band("very_weak",   20, max=5),
        ),
        benchmark_text="Good: >30%",
        explanation="Share of earnings paid as dividend.",
    ),

    # --- Valuation -----------------------------------------------------------
    MetricRule(
        key="pb", display_name="P/B Ratio", category="valuation",
        weight=1.2, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=0.8),
            Band("good",        80, min=0.8, max=1.2),
            Band("fair",        60, min=1.2, max=1.8),
            Band("weak",        40, min=1.8, max=2.5),
            Band("very_weak",   20, min=2.5),
        ),
        benchmark_text="Attractive: <1.2x | Expensive: >1.8x",
        explanation="Investment holdings often trade at a discount to book. P/B < 1 may signal value; > 1.5 requires clear justification.",
    ),
    MetricRule(
        key="pe", display_name="P/E Ratio", category="valuation",
        weight=0.8, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=10),
            Band("good",        80, min=10, max=15),
            Band("fair",        60, min=15, max=20),
            Band("weak",        40, min=20, max=30),
            Band("very_weak",   20, min=30),
        ),
        benchmark_text="Attractive: <15x | Expensive: >20x",
        explanation="PE can be distorted by fair-value gains; use as a secondary check to P/B.",
    ),
)


PROFILE_OVERRIDES: dict[str, dict[str, float]] = {
    "growth":    {"growth": 0.24, "profitability": 0.22, "valuation": 0.24,
                  "balance_sheet": 0.15, "dividend": 0.15},
    "dividend":  {"dividend": 0.30, "profitability": 0.18, "balance_sheet": 0.17,
                  "valuation": 0.25, "growth": 0.10},
    "risk":      {"balance_sheet": 0.32, "profitability": 0.16, "valuation": 0.20,
                  "dividend": 0.16, "growth": 0.16},
    "valuation": {"valuation": 0.48, "profitability": 0.16, "balance_sheet": 0.15,
                  "dividend": 0.12, "growth": 0.09},
    "quality":   {"profitability": 0.26, "balance_sheet": 0.22, "dividend": 0.18,
                  "growth": 0.14, "valuation": 0.20},
    "balanced":  {},
}


INVESTMENT_RULES = SectorRules(
    sector="Investment",
    methodology_version="1.0",
    categories=CATEGORIES,
    metrics=METRICS,
    profile_weight_overrides=PROFILE_OVERRIDES,
)
