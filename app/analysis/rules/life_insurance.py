"""Life Insurance scoring rules (methodology v1.0).

Life insurers' financials are dominated by long-duration policy liabilities,
investment income on the reserve pool, and premium growth. Solvency ratio
(Nepal Insurance Authority floor 150%) is the regulatory anchor. Traditional
banking ratios (NPL, CAR) don't apply; instead we look at premium growth,
claim experience, investment yield, and solvency headroom.
"""
from app.analysis.rules.base import (
    Band,
    CategoryDefinition,
    Direction,
    MetricRule,
    SectorRules,
)


CATEGORIES = (
    CategoryDefinition("profitability",   "Profitability",   weight=0.16, facet="quality"),
    CategoryDefinition("premium_growth",  "Premium Growth",  weight=0.16, facet="quality"),
    CategoryDefinition("underwriting",    "Underwriting",    weight=0.14, facet="quality"),
    CategoryDefinition("investment",      "Investment",      weight=0.12, facet="quality"),
    CategoryDefinition("solvency",        "Solvency",        weight=0.12, facet="quality"),
    CategoryDefinition("dividend",        "Dividend",        weight=0.05, facet="quality"),
    CategoryDefinition("valuation",       "Valuation",       weight=0.25, facet="valuation"),
)


METRICS = (
    # --- Profitability -------------------------------------------------------
    MetricRule(
        key="roe", display_name="Return on Equity", category="profitability",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=15),
            Band("good",        80, min=10, max=15),
            Band("fair",        60, min=7,  max=10),
            Band("weak",        40, min=4,  max=7),
            Band("very_weak",   20, max=4),
        ),
        benchmark_text="Good: >10%",
        explanation="Life insurers earn ROE more slowly than banks — long policy durations mean profits emerge over years.",
    ),
    MetricRule(
        key="roa", display_name="Return on Assets", category="profitability",
        weight=0.6, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=1.8),
            Band("good",        80, min=1.2, max=1.8),
            Band("fair",        60, min=0.7, max=1.2),
            Band("weak",        40, min=0.3, max=0.7),
            Band("very_weak",   20, max=0.3),
        ),
        benchmark_text="Good: >1.2%",
        explanation="Life insurers hold large investment pools; ROA is naturally compressed by asset base.",
    ),

    # --- Premium Growth ------------------------------------------------------
    MetricRule(
        key="gross_premium_growth", display_name="Gross Premium Growth (YoY)", category="premium_growth",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=10, max=20),
            Band("fair",        60, min=3,  max=10),
            Band("weak",        40, min=-5, max=3),
            Band("very_weak",   20, max=-5),
        ),
        benchmark_text="Good: >10% YoY",
        explanation="Top-line premium growth is the primary indicator of franchise health for a life insurer.",
    ),
    MetricRule(
        key="net_premium_growth", display_name="Net Premium Growth (YoY)", category="premium_growth",
        weight=0.7, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=18),
            Band("good",        80, min=8,  max=18),
            Band("fair",        60, min=2,  max=8),
            Band("weak",        40, min=-6, max=2),
            Band("very_weak",   20, max=-6),
        ),
        benchmark_text="Good: >8% YoY",
        explanation="Net premium strips out reinsurance; sustained growth suggests real book-building.",
    ),

    # --- Underwriting --------------------------------------------------------
    MetricRule(
        key="claim_ratio", display_name="Claim Ratio", category="underwriting",
        weight=1.0, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=55),
            Band("good",        80, min=55, max=65),
            Band("fair",        60, min=65, max=75),
            Band("weak",        40, min=75, max=85),
            Band("very_weak",   20, min=85),
        ),
        benchmark_text="Good: <65% | Concerning: >85%",
        explanation="Ratio of net claims paid to net premiums earned. Higher ratios erode underwriting profit.",
    ),
    MetricRule(
        key="expense_ratio_insurance", display_name="Expense Ratio", category="underwriting",
        weight=0.6, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=15),
            Band("good",        80, min=15, max=22),
            Band("fair",        60, min=22, max=30),
            Band("weak",        40, min=30, max=40),
            Band("very_weak",   20, min=40),
        ),
        benchmark_text="Good: <22%",
        explanation="Operating expenses relative to premiums; tighter is better for underwriting profit.",
    ),

    # --- Investment ----------------------------------------------------------
    MetricRule(
        key="investment_yield", display_name="Investment Yield", category="investment",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=8),
            Band("good",        80, min=6.5, max=8),
            Band("fair",        60, min=5,   max=6.5),
            Band("weak",        40, min=3.5, max=5),
            Band("very_weak",   20, max=3.5),
        ),
        benchmark_text="Good: >6.5%",
        explanation="Return on the investment pool that backs policy reserves. Regulatory restrictions cap the asset mix.",
    ),

    # --- Solvency ------------------------------------------------------------
    MetricRule(
        key="solvency_ratio", display_name="Solvency Ratio", category="solvency",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=250),
            Band("good",        80, min=200, max=250),
            Band("fair",        60, min=170, max=200),
            Band("weak",        40, min=150, max=170),
            Band("very_weak",   20, max=150),
        ),
        benchmark_text="NIA floor 150%; Good: >200%",
        explanation="Available solvency margin vs required. Below the 150% floor triggers regulatory action.",
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
            Band("excellent",  100, max=15),
            Band("good",        80, min=15, max=22),
            Band("fair",        60, min=22, max=30),
            Band("weak",        40, min=30, max=40),
            Band("very_weak",   20, min=40),
        ),
        benchmark_text="Attractive: <22x | Expensive: >30x",
        explanation="Life insurer P/E tends to be elevated because earnings emerge slowly relative to embedded value.",
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
        explanation="Book value understates franchise value for life insurers; use alongside embedded-value context when available.",
    ),
)


PROFILE_OVERRIDES: dict[str, dict[str, float]] = {
    "growth":    {"premium_growth": 0.28, "profitability": 0.18, "valuation": 0.15,
                  "underwriting": 0.14, "investment": 0.10, "solvency": 0.10, "dividend": 0.05},
    "dividend":  {"dividend": 0.25, "profitability": 0.18, "underwriting": 0.14, "solvency": 0.14,
                  "valuation": 0.15, "investment": 0.10, "premium_growth": 0.04},
    "risk":      {"solvency": 0.28, "underwriting": 0.20, "profitability": 0.14,
                  "valuation": 0.14, "investment": 0.10, "dividend": 0.06, "premium_growth": 0.08},
    "valuation": {"valuation": 0.35, "profitability": 0.16, "premium_growth": 0.12, "underwriting": 0.12,
                  "solvency": 0.10, "investment": 0.08, "dividend": 0.07},
    "quality":   {"profitability": 0.20, "underwriting": 0.20, "solvency": 0.16, "premium_growth": 0.16,
                  "investment": 0.10, "dividend": 0.08, "valuation": 0.10},
    "balanced":  {},
}


LIFE_INSURANCE_RULES = SectorRules(
    sector="Life Insurance",
    methodology_version="2.0",
    categories=CATEGORIES,
    metrics=METRICS,
    profile_weight_overrides=PROFILE_OVERRIDES,
)
