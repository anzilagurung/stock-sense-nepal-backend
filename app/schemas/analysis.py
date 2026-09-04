from datetime import datetime

from pydantic import BaseModel


class MetricEvaluation(BaseModel):
    metric_key: str
    display_name: str
    value: float | None
    unit: str | None = None
    rating: str  # excellent / good / fair / weak / very_weak / unknown
    score: float  # normalised 0-100
    weight: float
    weighted_contribution: float
    benchmark: str
    explanation: str
    category: str


class CategoryScore(BaseModel):
    category: str
    display_name: str
    score: float  # 0-100
    weight: float
    weighted_contribution: float
    rating: str
    metric_count: int


class AnalysisConclusion(BaseModel):
    headline: str
    summary: str
    strengths: list[str]
    concerns: list[str]


class AnalysisResult(BaseModel):
    company_symbol: str
    company_name: str
    sector: str
    methodology_version: str
    profile: str  # balanced / growth / dividend / risk / valuation / quality

    overall_score: float
    overall_rating: str
    company_quality_score: float
    valuation_score: float

    categories: list[CategoryScore]
    metrics: list[MetricEvaluation]
    conclusion: AnalysisConclusion

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
    categories: dict[str, float]  # category -> score
    highlight_rating: dict[str, str]  # category -> rating (for the coloured cell)


class ComparisonResult(BaseModel):
    sector: str
    methodology_version: str
    profile: str
    ranked: list[ComparisonRow]
    conclusion: str
    generated_at: datetime
