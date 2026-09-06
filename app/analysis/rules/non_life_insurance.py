"""Non-Life Insurance scoring rules (methodology v1.0).

Non-life (general) insurers are underwriting-driven: the combined ratio
(claim + expense) determines whether the book itself is profitable, and
investment income is a secondary earnings source. Reserves are short-duration
so growth flows through to earnings faster than life insurance. NIA solvency
floor is 150%.
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
    CategoryDefinition("premium_growth",  "Premium Growth",  weight=0.14, facet="quality"),
    CategoryDefinition("underwriting",    "Underwriting",    weight=0.20, facet="quality"),
    CategoryDefinition("investment",      "Investment",      weight=0.10, facet="quality"),
    CategoryDefinition("solvency",        "Solvency",        weight=0.10, facet="quality"),
    CategoryDefinition("dividend",        "Dividend",        weight=0.05, facet="quality"),
    CategoryDefinition("valuation",       "Valuation",       weight=0.25, facet="valuation"),
)


METRICS = (
    # --- Profitability -------------------------------------------------------
    MetricRule(
        key="roe", display_name="Return on Equity", category="profitability",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=16),
            Band("good",        80, min=11, max=16),
            Band("fair",        60, min=7,  max=11),
            Band("weak",        40, min=4,  max=7),
            Band("very_weak",   20, max=4),
        ),
        benchmark_text="Good: >11%",
        explanation="Non-life ROE is driven by underwriting profit plus investment income on float.",
    ),
    MetricRule(
        key="roa", display_name="Return on Assets", category="profitability",
        weight=0.6, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=3),
            Band("good",        80, min=2,   max=3),
            Band("fair",        60, min=1.2, max=2),
            Band("weak",        40, min=0.5, max=1.2),
            Band("very_weak",   20, max=0.5),
        ),
        benchmark_text="Good: >2%",
        explanation="Non-life balance sheets are smaller than life, so ROA is naturally higher.",
    ),

    # --- Premium Growth ------------------------------------------------------
    MetricRule(
        key="gross_premium_growth", display_name="Gross Premium Growth (YoY)", category="premium_growth",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=18),
            Band("good",        80, min=8,  max=18),
            Band("fair",        60, min=2,  max=8),
            Band("weak",        40, min=-6, max=2),
            Band("very_weak",   20, max=-6),
        ),
        benchmark_text="Good: >8% YoY",
        explanation="Non-life premium growth tracks GDP + insurance penetration; sustained growth is a franchise signal.",
    ),
    MetricRule(
        key="retention_ratio", display_name="Retention Ratio", category="premium_growth",
        weight=0.5, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=70),
            Band("good",        80, min=55, max=70),
            Band("fair",        60, min=40, max=55),
            Band("weak",        40, min=25, max=40),
            Band("very_weak",   20, max=25),
        ),
        benchmark_text="Good: >55%",
        explanation="Share of gross premium retained after reinsurance. Higher retention means the insurer keeps more risk (and reward) on its own book.",
    ),

    # --- Underwriting --------------------------------------------------------
    MetricRule(
        key="combined_ratio", display_name="Combined Ratio", category="underwriting",
        weight=1.0, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=85),
            Band("good",        80, min=85, max=95),
            Band("fair",        60, min=95, max=100),
            Band("weak",        40, min=100, max=110),
            Band("very_weak",   20, min=110),
        ),
        benchmark_text="Underwriting profit: <100% | Danger: >110%",
        explanation="Claim ratio + expense ratio. Below 100% the book is profitable before investment income; above 100% the insurer is paying out more than it collects.",
    ),
    MetricRule(
        key="loss_ratio", display_name="Loss Ratio", category="underwriting",
        weight=0.8, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=45),
            Band("good",        80, min=45, max=60),
            Band("fair",        60, min=60, max=70),
            Band("weak",        40, min=70, max=80),
            Band("very_weak",   20, min=80),
        ),
        benchmark_text="Good: <60% | Concerning: >80%",
        explanation="Net claims paid over net premium earned. Sustained high loss ratios point to pricing or risk-selection problems.",
    ),
    MetricRule(
        key="expense_ratio_insurance", display_name="Expense Ratio", category="underwriting",
        weight=0.5, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=25),
            Band("good",        80, min=25, max=32),
            Band("fair",        60, min=32, max=40),
            Band("weak",        40, min=40, max=50),
            Band("very_weak",   20, min=50),
        ),
        benchmark_text="Good: <32%",
        explanation="Operating expenses over premium. Non-life expense ratios are typically higher than life.",
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
        explanation="Return on the investment portfolio; provides earnings support even when underwriting is soft.",
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
            Band("excellent",  100, max=12),
            Band("good",        80, min=12, max=18),
            Band("fair",        60, min=18, max=25),
            Band("weak",        40, min=25, max=35),
            Band("very_weak",   20, min=35),
        ),
        benchmark_text="Attractive: <18x | Expensive: >25x",
        explanation="Non-life P/E is typically lower than life because earnings emerge faster.",
    ),
    MetricRule(
        key="pb", display_name="P/B Ratio", category="valuation",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=1.5),
            Band("good",        80, min=1.5, max=2.2),
            Band("fair",        60, min=2.2, max=3),
            Band("weak",        40, min=3,   max=4),
            Band("very_weak",   20, min=4),
        ),
        benchmark_text="Attractive: <2.2x | Expensive: >3x",
        explanation="P/B compares market price to book value.",
    ),
)


PROFILE_OVERRIDES: dict[str, dict[str, float]] = {
    "growth":    {"premium_growth": 0.26, "profitability": 0.20, "valuation": 0.15,
                  "underwriting": 0.16, "investment": 0.08, "solvency": 0.10, "dividend": 0.05},
    "dividend":  {"dividend": 0.25, "profitability": 0.18, "underwriting": 0.18, "solvency": 0.12,
                  "valuation": 0.15, "investment": 0.08, "premium_growth": 0.04},
    "risk":      {"solvency": 0.24, "underwriting": 0.26, "profitability": 0.14,
                  "valuation": 0.14, "investment": 0.08, "dividend": 0.06, "premium_growth": 0.08},
    "valuation": {"valuation": 0.35, "profitability": 0.16, "premium_growth": 0.10, "underwriting": 0.16,
                  "solvency": 0.08, "investment": 0.08, "dividend": 0.07},
    "quality":   {"underwriting": 0.24, "profitability": 0.20, "solvency": 0.14, "premium_growth": 0.14,
                  "investment": 0.10, "dividend": 0.08, "valuation": 0.10},
    "balanced":  {},
}


NON_LIFE_INSURANCE_RULES = SectorRules(
    sector="Non Life Insurance",
    methodology_version="1.0",
    categories=CATEGORIES,
    metrics=METRICS,
    profile_weight_overrides=PROFILE_OVERRIDES,
)
