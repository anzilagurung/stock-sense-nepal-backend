"""Microfinance (Laghubitta) scoring rules (methodology v1.0).

MFIs (Class D) in Nepal have a distinctive profile: very high yields on
small-ticket group lending, tight interest-spread caps set by NRB, and
elevated portfolio quality risk (PAR30) compared to banks. Valuation
multiples are typically the highest in the market — the sector often
trades at P/B > 3x for well-run names.

Metric keys used here map to standard indicators; where common banking
keys (roe, roa, npl, car) are reused, they carry MFI-appropriate bands.
Missing values (portfolio_at_risk, operational_self_sufficiency, etc.)
will surface as "unknown" in the UI until ingestion catches up.
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
    CategoryDefinition("growth",            "Growth",            weight=0.14, facet="quality"),
    CategoryDefinition("portfolio_quality", "Portfolio Quality", weight=0.20, facet="quality"),
    CategoryDefinition("capital_strength",  "Capital Strength",  weight=0.10, facet="quality"),
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
            Band("excellent",  100, min=22),
            Band("good",        80, min=15, max=22),
            Band("fair",        60, min=10, max=15),
            Band("weak",        40, min=5,  max=10),
            Band("very_weak",   20, max=5),
        ),
        benchmark_text="Good: >15% | Excellent: >22%",
        explanation="Well-run Nepali MFIs historically post very high ROE; anything below the banking benchmark is a concern given the higher risk profile.",
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
        explanation="MFI ROA is structurally higher than banks because lending yields are much higher.",
    ),
    MetricRule(
        key="operational_self_sufficiency", display_name="Operational Self-Sufficiency (OSS)", category="profitability",
        weight=0.5, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=140),
            Band("good",        80, min=120, max=140),
            Band("fair",        60, min=110, max=120),
            Band("weak",        40, min=100, max=110),
            Band("very_weak",   20, max=100),
        ),
        benchmark_text="Sustainable: >120%; Loss-making: <100%",
        explanation="OSS = operating revenue / (operating + financial + loan-loss expense). Below 100% the MFI cannot cover its costs from operations.",
    ),

    # --- Growth --------------------------------------------------------------
    MetricRule(
        key="net_profit_growth", display_name="Net Profit Growth (YoY)", category="growth",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=25),
            Band("good",        80, min=12, max=25),
            Band("fair",        60, min=3,  max=12),
            Band("weak",        40, min=-10, max=3),
            Band("very_weak",   20, max=-10),
        ),
        benchmark_text="Good: >12% YoY",
        explanation="MFI earnings can swing sharply with credit cycles; sustained growth is a positive signal.",
    ),
    MetricRule(
        key="eps_growth", display_name="EPS Growth (YoY)", category="growth",
        weight=0.9, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=20),
            Band("good",        80, min=8,  max=20),
            Band("fair",        60, min=0,  max=8),
            Band("weak",        40, min=-12, max=0),
            Band("very_weak",   20, max=-12),
        ),
        benchmark_text="Good: >8% YoY",
        explanation="EPS growth accounts for share-count changes from frequent bonus issues in this sector.",
    ),

    # --- Portfolio Quality ---------------------------------------------------
    MetricRule(
        key="npl", display_name="Non-Performing Loans (NPL)", category="portfolio_quality",
        weight=1.0, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=2),
            Band("good",        80, min=2,  max=4),
            Band("fair",        60, min=4,  max=6),
            Band("weak",        40, min=6,  max=9),
            Band("very_weak",   20, min=9),
        ),
        benchmark_text="Good: <4% | Danger: >9%",
        explanation="MFI portfolios are small-ticket unsecured group loans — NPL trending up is often the leading indicator of stress.",
    ),
    MetricRule(
        key="portfolio_at_risk", display_name="Portfolio at Risk (PAR30)", category="portfolio_quality",
        weight=0.9, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=2),
            Band("good",        80, min=2, max=4),
            Band("fair",        60, min=4, max=7),
            Band("weak",        40, min=7, max=10),
            Band("very_weak",   20, min=10),
        ),
        benchmark_text="Good: <4% | Danger: >10%",
        explanation="PAR30 is the share of the portfolio with any repayment overdue >30 days — the standard MFI portfolio-quality metric.",
    ),

    # --- Capital Strength ----------------------------------------------------
    MetricRule(
        key="car", display_name="Capital Adequacy Ratio (CAR)", category="capital_strength",
        weight=1.0, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=14),
            Band("good",        80, min=12,  max=14),
            Band("fair",        60, min=10,  max=12),
            Band("weak",        40, min=8,   max=10),
            Band("very_weak",   20, max=8),
        ),
        benchmark_text="NRB floor 8%; Good: >12%",
        explanation="MFI CAR floor is lower than banks, but a thicker cushion is still preferable given portfolio volatility.",
    ),

    # --- Efficiency ----------------------------------------------------------
    MetricRule(
        key="yield_on_portfolio", display_name="Yield on Portfolio", category="efficiency",
        weight=0.8, unit="%", direction=Direction.HIGHER_IS_BETTER,
        bands=(
            Band("excellent",  100, min=18),
            Band("good",        80, min=15, max=18),
            Band("fair",        60, min=12, max=15),
            Band("weak",        40, min=10, max=12),
            Band("very_weak",   20, max=10),
        ),
        benchmark_text="Good: >15% (subject to NRB caps)",
        explanation="Effective yield on loan portfolio; NRB caps the spread so this drifts with cost of fund.",
    ),
    MetricRule(
        key="cost_of_fund", display_name="Cost of Fund", category="efficiency",
        weight=0.5, unit="%", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=7),
            Band("good",        80, min=7,   max=8.5),
            Band("fair",        60, min=8.5, max=10),
            Band("weak",        40, min=10,  max=11.5),
            Band("very_weak",   20, min=11.5),
        ),
        benchmark_text="Good: <8.5%",
        explanation="MFI cost of fund is typically higher than commercial banks because most funding comes from wholesale sources.",
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
        explanation="Well-run MFIs return meaningful dividends despite reinvesting for growth.",
    ),

    # --- Valuation -----------------------------------------------------------
    MetricRule(
        key="pe", display_name="P/E Ratio", category="valuation",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=14),
            Band("good",        80, min=14, max=20),
            Band("fair",        60, min=20, max=28),
            Band("weak",        40, min=28, max=40),
            Band("very_weak",   20, min=40),
        ),
        benchmark_text="Attractive: <20x | Expensive: >28x",
        explanation="MFI P/E in Nepal typically runs higher than banks; the sector prices in growth expectations.",
    ),
    MetricRule(
        key="pb", display_name="P/B Ratio", category="valuation",
        weight=1.0, unit="x", direction=Direction.LOWER_IS_BETTER,
        bands=(
            Band("excellent",  100, max=2),
            Band("good",        80, min=2,   max=3),
            Band("fair",        60, min=3,   max=4.5),
            Band("weak",        40, min=4.5, max=6),
            Band("very_weak",   20, min=6),
        ),
        benchmark_text="Attractive: <3x | Expensive: >4.5x",
        explanation="P/B multiples in this sector are structurally elevated; use as a relative gauge rather than an absolute one.",
    ),
)


PROFILE_OVERRIDES: dict[str, dict[str, float]] = {
    "growth":    {"growth": 0.30, "profitability": 0.22, "valuation": 0.15,
                  "portfolio_quality": 0.15, "capital_strength": 0.08, "efficiency": 0.05, "dividend": 0.05},
    "dividend":  {"dividend": 0.28, "profitability": 0.18, "portfolio_quality": 0.15, "capital_strength": 0.12,
                  "valuation": 0.15, "efficiency": 0.06, "growth": 0.06},
    "risk":      {"portfolio_quality": 0.32, "capital_strength": 0.20, "profitability": 0.14,
                  "valuation": 0.14, "efficiency": 0.08, "dividend": 0.06, "growth": 0.06},
    "valuation": {"valuation": 0.35, "profitability": 0.16, "growth": 0.10, "portfolio_quality": 0.15,
                  "capital_strength": 0.10, "efficiency": 0.07, "dividend": 0.07},
    "quality":   {"profitability": 0.22, "portfolio_quality": 0.22, "capital_strength": 0.14, "growth": 0.16,
                  "efficiency": 0.10, "dividend": 0.08, "valuation": 0.08},
    "balanced":  {},
}


MICROFINANCE_RULES = SectorRules(
    sector="Microfinance",
    methodology_version="2.0",
    categories=CATEGORIES,
    metrics=METRICS,
    profile_weight_overrides=PROFILE_OVERRIDES,
)
