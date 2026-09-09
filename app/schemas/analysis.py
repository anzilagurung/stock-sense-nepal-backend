from datetime import datetime

from pydantic import BaseModel

METHODOLOGY_ENGINE_VERSION = "2.0"


class MetricEvaluation(BaseModel):
    metric_key: str
    display_name: str
    value: float | None
    unit: str | None = None
    rating: str          # excellent / good / fair / weak / very_weak / unknown
    score: float
    weight: float
    weighted_contribution: float
    benchmark: str
    explanation: str
    category: str

    # v2.0 overlays — informational, do NOT change the raw score.
    percentile_band: str | None = None   # top_quartile / above_median / below_median / bottom_quartile
    trajectory: str | None = None        # improving / stable / declining / unknown
    is_derived: bool = False             # true for PEG, dividend coverage, etc.


class CategoryScore(BaseModel):
    category: str
    display_name: str
    score: float
    weight: float
    weighted_contribution: float
    rating: str
    metric_count: int


class AnalysisConclusion(BaseModel):
    headline: str
    summary: str
    strengths: list[str]
    concerns: list[str]


# --- v2.0 additions ---------------------------------------------------------

class RedFlagInfo(BaseModel):
    key: str
    display_name: str
    severity: str          # caution / avoid / insufficient_data
    explanation: str


class StabilityInfo(BaseModel):
    tier: str              # blue_chip / established / emerging / speculative
    display_name: str
    reasons: list[str]


class TrajectoryInfo(BaseModel):
    sentiment: str         # improving / stable / declining / unknown
    improving_count: int
    stable_count: int
    declining_count: int
    unknown_count: int


class VerdictInfo(BaseModel):
    tier: str              # strong_buy_candidate / buy_candidate / watchlist / hold / caution / avoid / insufficient_data
    display_name: str
    confidence: str        # high / medium / low
    headline: str
    rationale: list[str]
    caps_applied: list[str]


class DerivedMetricInfo(BaseModel):
    """Non-scored, informational derived metric surfaced in the response."""
    key: str
    display_name: str
    value: float | None
    unit: str
    interpretation: str    # short one-liner (e.g. "PEG below 1.5 is attractive")


class AnalysisResult(BaseModel):
    company_symbol: str
    company_name: str
    sector: str
    methodology_version: str          # sector calibration version (per rule file)
    engine_version: str = METHODOLOGY_ENGINE_VERSION
    profile: str                      # balanced / growth / dividend / risk / valuation / quality

    overall_score: float
    overall_rating: str
    company_quality_score: float
    valuation_score: float

    categories: list[CategoryScore]
    metrics: list[MetricEvaluation]
    conclusion: AnalysisConclusion

    # v2.0 additions
    verdict: VerdictInfo | None = None
    stability: StabilityInfo | None = None
    trajectory: TrajectoryInfo | None = None
    red_flags: list[RedFlagInfo] = []
    derived_metrics: list[DerivedMetricInfo] = []
    data_completeness: float = 1.0    # 0-1 fraction

    generated_at: datetime
    disclaimer: str = (
        "This is an automated methodology-based assessment for informational and educational purposes only. "
        "It is not investment advice and does not guarantee any future return."
    )


class ComparisonRow(BaseModel):
    company_symbol: str
    company_name: str
    overall_score: float
    company_quality_score: float
    valuation_score: float
    categories: dict[str, float]
    highlight_rating: dict[str, str]

    # v2.0 additions surfaced to comparison view
    verdict_tier: str | None = None
    verdict_display_name: str | None = None
    stability_tier: str | None = None
    stability_display_name: str | None = None
    red_flag_count: int = 0


class ComparisonResult(BaseModel):
    sector: str
    methodology_version: str
    engine_version: str = METHODOLOGY_ENGINE_VERSION
    profile: str
    ranked: list[ComparisonRow]
    conclusion: str
    generated_at: datetime
