"""The scoring engine.

Input: a MetricSnapshot (metric_key -> value) + a sector name + a profile.
Output: an AnalysisResult with per-metric evaluations, category scores, overall score,
strengths, concerns, and an explanation for every number.

The engine is deliberately transparent: it never invents scores. Every number surfaced
is derived from a rule + a value.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.analysis.rules import get_rules_for_sector
from app.analysis.rules.base import (
    Band,
    CategoryDefinition,
    MetricRule,
    SectorRules,
    rating_from_score,
)
from app.schemas.analysis import (
    AnalysisConclusion,
    AnalysisResult,
    CategoryScore,
    ComparisonResult,
    ComparisonRow,
    MetricEvaluation,
)


@dataclass
class MetricSnapshot:
    """Latest metric values for a single company. metric_key -> raw numeric value."""
    company_symbol: str
    company_name: str
    sector: str
    values: dict[str, float]


def _band_for(rule: MetricRule, value: float) -> Band | None:
    for band in rule.bands:
        if band.contains(value):
            return band
    return None


def _evaluate_metric(rule: MetricRule, value: float | None) -> MetricEvaluation:
    if value is None:
        return MetricEvaluation(
            metric_key=rule.key,
            display_name=rule.display_name,
            value=None,
            unit=rule.unit,
            rating="unknown",
            score=50.0,  # neutral default when data missing — reflected in the UI
            weight=rule.weight,
            weighted_contribution=0.0,
            benchmark=rule.benchmark_text,
            explanation=rule.explanation + " (Data not available — treated as neutral.)",
            category=rule.category,
        )

    band = _band_for(rule, value)
    score = band.score if band else 50.0
    rating = band.rating if band else "unknown"

    return MetricEvaluation(
        metric_key=rule.key,
        display_name=rule.display_name,
        value=round(value, 4),
        unit=rule.unit,
        rating=rating,
        score=score,
        weight=rule.weight,
        weighted_contribution=0.0,  # filled in later once category weights normalise
        benchmark=rule.benchmark_text,
        explanation=rule.explanation,
        category=rule.category,
    )


def _category_weights(rules: SectorRules, profile: str) -> dict[str, float]:
    override = rules.profile_weight_overrides.get(profile, {})
    if override:
        # normalise defensively
        total = sum(override.values()) or 1.0
        return {k: v / total for k, v in override.items()}
    base = {c.key: c.weight for c in rules.categories}
    total = sum(base.values()) or 1.0
    return {k: v / total for k, v in base.items()}


def _build_conclusion(
    company_name: str,
    overall: float,
    quality_score: float,
    valuation_score: float,
    metrics: list[MetricEvaluation],
) -> AnalysisConclusion:
    strengths = [
        f"{m.display_name}: {_format_value(m)} — {m.rating.replace('_', ' ')}"
        for m in metrics if m.rating in ("excellent", "good") and m.value is not None
    ][:5]

    concerns = [
        f"{m.display_name}: {_format_value(m)} — {m.rating.replace('_', ' ')}"
        for m in metrics if m.rating in ("weak", "very_weak") and m.value is not None
    ][:5]

    overall_rating = rating_from_score(overall)
    quality_rating = rating_from_score(quality_score)
    val_rating = rating_from_score(valuation_score)

    if quality_score >= 70 and valuation_score < 55:
        headline = f"{company_name}: Fundamentally strong but currently expensive"
        summary = (
            f"Based on the methodology, {company_name} scores {quality_score:.0f}/100 on company quality "
            f"but only {valuation_score:.0f}/100 on valuation. Waiting for a better entry price may improve the risk/reward."
        )
    elif quality_score >= 70 and valuation_score >= 70:
        headline = f"{company_name}: Fundamentally strong and reasonably valued"
        summary = (
            f"{company_name} shows strong company quality ({quality_score:.0f}/100) with valuation "
            f"currently at {valuation_score:.0f}/100. Combination looks attractive on the current methodology."
        )
    elif quality_score < 55:
        headline = f"{company_name}: Fundamental concerns present"
        summary = (
            f"Several quality indicators are below acceptable bands. Overall score {overall:.0f}/100 ({overall_rating})."
        )
    else:
        headline = f"{company_name}: Mixed profile — see breakdown"
        summary = (
            f"Overall {overall:.0f}/100 ({overall_rating}), quality {quality_rating}, valuation {val_rating}. "
            f"Review category scores for a fuller picture."
        )

    return AnalysisConclusion(
        headline=headline,
        summary=summary,
        strengths=strengths,
        concerns=concerns,
    )


def _format_value(m: MetricEvaluation) -> str:
    if m.value is None:
        return "n/a"
    if m.unit == "%":
        return f"{m.value:.2f}%"
    if m.unit == "x":
        return f"{m.value:.2f}x"
    if m.unit == "Rs":
        return f"Rs {m.value:.2f}"
    return f"{m.value:.2f}"


def analyse(snapshot: MetricSnapshot, profile: str = "balanced") -> AnalysisResult:
    rules = get_rules_for_sector(snapshot.sector)
    if rules is None:
        raise ValueError(f"No sector rules configured for '{snapshot.sector}'")

    category_weights = _category_weights(rules, profile)
    evaluations: list[MetricEvaluation] = []
    category_scores: dict[str, tuple[float, int]] = {}  # cat_key -> (weighted_sum, weight_used)

    # Group metrics by category for normalised in-category weighting.
    for cat in rules.categories:
        cat_metrics = rules.metrics_in(cat.key)
        if not cat_metrics:
            continue
        cat_weight_total = sum(m.weight for m in cat_metrics) or 1.0

        cat_weighted_score = 0.0
        for rule in cat_metrics:
            raw = snapshot.values.get(rule.key)
            ev = _evaluate_metric(rule, raw)
            in_cat_weight = rule.weight / cat_weight_total
            weighted = ev.score * in_cat_weight
            cat_weighted_score += weighted
            ev = ev.model_copy(update={"weighted_contribution": round(weighted, 2)})
            evaluations.append(ev)

        category_scores[cat.key] = (round(cat_weighted_score, 2), len(cat_metrics))

    # Overall score = sum(category_score * category_weight)
    overall = 0.0
    quality_num, quality_den = 0.0, 0.0
    valuation_num, valuation_den = 0.0, 0.0

    category_out: list[CategoryScore] = []
    for cat in rules.categories:
        if cat.key not in category_scores:
            continue
        score, count = category_scores[cat.key]
        cw = category_weights.get(cat.key, 0.0)
        contribution = score * cw
        overall += contribution
        if cat.facet == "quality":
            quality_num += score * cw
            quality_den += cw
        elif cat.facet == "valuation":
            valuation_num += score * cw
            valuation_den += cw

        category_out.append(CategoryScore(
            category=cat.key,
            display_name=cat.display_name,
            score=round(score, 1),
            weight=round(cw, 3),
            weighted_contribution=round(contribution, 2),
            rating=rating_from_score(score),
            metric_count=count,
        ))

    quality_score = round(quality_num / quality_den, 1) if quality_den else 0.0
    valuation_score = round(valuation_num / valuation_den, 1) if valuation_den else 0.0
    overall = round(overall, 1)

    return AnalysisResult(
        company_symbol=snapshot.company_symbol,
        company_name=snapshot.company_name,
        sector=snapshot.sector,
        methodology_version=rules.methodology_version,
        profile=profile,
        overall_score=overall,
        overall_rating=rating_from_score(overall),
        company_quality_score=quality_score,
        valuation_score=valuation_score,
        categories=category_out,
        metrics=evaluations,
        conclusion=_build_conclusion(snapshot.company_name, overall, quality_score, valuation_score, evaluations),
        generated_at=datetime.utcnow(),
    )


def compare(snapshots: list[MetricSnapshot], profile: str = "balanced") -> ComparisonResult:
    if not snapshots:
        raise ValueError("compare() needs at least one snapshot")

    sector = snapshots[0].sector
    if any(s.sector != sector for s in snapshots):
        raise ValueError("All companies in a comparison must belong to the same sector")

    results = [analyse(s, profile=profile) for s in snapshots]
    results.sort(key=lambda r: r.overall_score, reverse=True)

    rows: list[ComparisonRow] = []
    for r in results:
        categories = {c.category: c.score for c in r.categories}
        highlight = {c.category: c.rating for c in r.categories}
        rows.append(ComparisonRow(
            company_symbol=r.company_symbol,
            company_name=r.company_name,
            overall_score=r.overall_score,
            company_quality_score=r.company_quality_score,
            valuation_score=r.valuation_score,
            categories=categories,
            highlight_rating=highlight,
        ))

    winner = rows[0]
    conclusion = (
        f"{winner.company_name} ({winner.company_symbol}) ranks highest on the '{profile}' profile "
        f"with an overall score of {winner.overall_score:.1f}/100. "
        "Result is derived from the current methodology and is not a prediction of future returns."
    )

    return ComparisonResult(
        sector=sector,
        methodology_version=get_rules_for_sector(sector).methodology_version,
        profile=profile,
        ranked=rows,
        conclusion=conclusion,
        generated_at=datetime.utcnow(),
    )
