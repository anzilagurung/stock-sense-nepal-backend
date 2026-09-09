"""The scoring engine (methodology v2.0).

Input: a :class:`MetricSnapshot` (metric values + optional history / dividends /
peer percentiles / company metadata) + a profile.

Output: an :class:`AnalysisResult` with every layer surfaced:

* Category scores (unchanged from v1.x — pure sector-band roll-up)
* Overall / Quality / Valuation scores
* Per-metric evaluation (with new percentile + trajectory overlays)
* Derived metrics (PEG, dividend coverage, dividend streak, earnings volatility)
* Red flags triggered
* Trajectory sentiment
* Stability tier
* Verdict (tier + confidence + rationale)
* Data completeness

Design invariant kept from v1: every number in the response can be traced back
to a rule + a value. The verdict layer only *interprets* those numbers, it
does not invent scores.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.analysis import derived as derived_mod
from app.analysis import peers as peers_mod
from app.analysis import red_flags as red_flags_mod
from app.analysis import stability as stability_mod
from app.analysis import trajectory as trajectory_mod
from app.analysis import verdict as verdict_mod
from app.analysis.derived import DividendRecord, HistoricalMetricPoint
from app.analysis.rules import SECTOR_RULES, get_rules_for_sector
from app.analysis.rules.base import (
    Band,
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
    DerivedMetricInfo,
    MetricEvaluation,
    RedFlagInfo,
    StabilityInfo,
    TrajectoryInfo,
    VerdictInfo,
)


class SectorNotSupportedError(Exception):
    """Raised when a company's sector has no scoring rules configured yet."""

    def __init__(self, sector: str):
        self.sector = sector
        self.supported = sorted(SECTOR_RULES.keys())
        super().__init__(
            f"Analysis for sector '{sector}' is not available yet. "
            f"Currently supported: {', '.join(self.supported)}."
        )


@dataclass
class MetricSnapshot:
    """Everything the engine needs to score a single company.

    ``values`` is the primary input; the optional fields let the v2.0 layers
    (trajectory, stability, red flags) do their job. Missing optional fields
    degrade gracefully — the engine still produces a result, just with lower
    confidence and no trajectory overlay.
    """
    company_symbol: str
    company_name: str
    sector: str
    values: dict[str, float]
    history: list[HistoricalMetricPoint] = field(default_factory=list)
    dividends: list[DividendRecord] = field(default_factory=list)
    listed_date: str | None = None
    sector_percentiles: dict[str, dict[str, float]] = field(default_factory=dict)


# --- Per-metric evaluation ---------------------------------------------------

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
            score=50.0,
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
        weighted_contribution=0.0,
        benchmark=rule.benchmark_text,
        explanation=rule.explanation,
        category=rule.category,
    )


def _category_weights(rules: SectorRules, profile: str) -> dict[str, float]:
    override = rules.profile_weight_overrides.get(profile, {})
    if override:
        total = sum(override.values()) or 1.0
        return {k: v / total for k, v in override.items()}
    base = {c.key: c.weight for c in rules.categories}
    total = sum(base.values()) or 1.0
    return {k: v / total for k, v in base.items()}


# --- Conclusion (legacy, kept for backward compatibility) -------------------

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

    if quality_score >= 70 and valuation_score < 55:
        headline = f"{company_name}: Fundamentally strong but currently expensive"
        summary = (
            f"{company_name} scores {quality_score:.0f}/100 on company quality but only "
            f"{valuation_score:.0f}/100 on valuation. Waiting for a better entry price may "
            "improve the risk/reward."
        )
    elif quality_score >= 70 and valuation_score >= 70:
        headline = f"{company_name}: Fundamentally strong and reasonably valued"
        summary = (
            f"{company_name} shows strong quality ({quality_score:.0f}/100) with valuation "
            f"currently at {valuation_score:.0f}/100."
        )
    elif quality_score < 55:
        headline = f"{company_name}: Fundamental concerns present"
        summary = (
            f"Several quality indicators are below acceptable bands. Overall "
            f"{overall:.0f}/100 ({overall_rating})."
        )
    else:
        headline = f"{company_name}: Mixed profile — see breakdown"
        summary = (
            f"Overall {overall:.0f}/100 ({overall_rating}), quality {quality_score:.0f}, "
            f"valuation {valuation_score:.0f}. Review category scores for detail."
        )

    return AnalysisConclusion(
        headline=headline, summary=summary, strengths=strengths, concerns=concerns,
    )


# --- Derived metrics for the response ---------------------------------------

def _derived_metric_infos(
    values: dict[str, float | None],
    dividend_streak: int,
    earnings_volatility: float | None,
) -> list[DerivedMetricInfo]:
    infos: list[DerivedMetricInfo] = []

    peg = values.get("peg_ratio")
    if peg is not None:
        interp = (
            "Below 1.5 is generally attractive; above 3 is stretched." if peg < 1.5
            else "Around 1.5–3: fair for the growth on offer." if peg < 3
            else "Above 3: growth already priced in — small misses hurt."
        )
        infos.append(DerivedMetricInfo(
            key="peg_ratio", display_name="PEG Ratio",
            value=round(peg, 2), unit="x", interpretation=interp,
        ))

    cov = values.get("dividend_coverage")
    if cov is not None:
        interp = (
            "Comfortably covered (EPS > 2.5x dividend)." if cov >= 2.5
            else "Adequately covered." if cov >= 1.5
            else "Thinly covered — dividend at risk if earnings dip."
        )
        infos.append(DerivedMetricInfo(
            key="dividend_coverage", display_name="Dividend Coverage",
            value=round(cov, 2), unit="x", interpretation=interp,
        ))

    if dividend_streak > 0:
        infos.append(DerivedMetricInfo(
            key="dividend_streak_years", display_name="Dividend Streak",
            value=float(dividend_streak), unit="years",
            interpretation=(
                "Long, unbroken dividend history — signals management commitment."
                if dividend_streak >= 5 else
                "Consistent recent payer."
            ),
        ))

    if earnings_volatility is not None:
        interp = (
            "Very stable earnings." if earnings_volatility < 0.15
            else "Moderate earnings variability." if earnings_volatility < 0.35
            else "Volatile earnings — expect year-to-year swings."
        )
        infos.append(DerivedMetricInfo(
            key="earnings_volatility", display_name="Earnings Volatility",
            value=round(earnings_volatility, 2), unit="cv",
            interpretation=interp,
        ))

    return infos


# --- Main entry point --------------------------------------------------------

def analyse(snapshot: MetricSnapshot, profile: str = "balanced") -> AnalysisResult:
    rules = get_rules_for_sector(snapshot.sector)
    if rules is None:
        raise SectorNotSupportedError(snapshot.sector)

    # ---- Layer 1a: derived metrics (merged into values for downstream use) --
    values: dict[str, float | None] = dict(snapshot.values)  # copy
    values["peg_ratio"] = derived_mod.compute_peg(values)
    values["dividend_coverage"] = derived_mod.compute_dividend_coverage(values)
    dividend_streak = derived_mod.compute_dividend_streak(snapshot.dividends)
    values["dividend_streak_years"] = float(dividend_streak) if dividend_streak else None
    earnings_vol = derived_mod.compute_earnings_volatility(snapshot.history)
    values["earnings_volatility"] = earnings_vol
    values["consecutive_loss_quarters"] = float(
        derived_mod.compute_consecutive_loss_quarters(snapshot.history)
    )

    # ---- Layer 1b: category / metric scoring (unchanged formula) -----------
    category_weights = _category_weights(rules, profile)
    evaluations: list[MetricEvaluation] = []
    category_scores: dict[str, tuple[float, int]] = {}

    for cat in rules.categories:
        cat_metrics = rules.metrics_in(cat.key)
        if not cat_metrics:
            continue
        cat_weight_total = sum(m.weight for m in cat_metrics) or 1.0

        cat_weighted_score = 0.0
        for rule in cat_metrics:
            raw = values.get(rule.key)
            ev = _evaluate_metric(rule, raw)
            in_cat_weight = rule.weight / cat_weight_total
            weighted = ev.score * in_cat_weight
            cat_weighted_score += weighted
            ev = ev.model_copy(update={"weighted_contribution": round(weighted, 2)})
            evaluations.append(ev)

        category_scores[cat.key] = (round(cat_weighted_score, 2), len(cat_metrics))

    overall = 0.0
    quality_num = quality_den = 0.0
    valuation_num = valuation_den = 0.0
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
            category=cat.key, display_name=cat.display_name,
            score=round(score, 1), weight=round(cw, 3),
            weighted_contribution=round(contribution, 2),
            rating=rating_from_score(score), metric_count=count,
        ))

    quality_score = round(quality_num / quality_den, 1) if quality_den else 0.0
    valuation_score = round(valuation_num / valuation_den, 1) if valuation_den else 0.0
    overall = round(overall, 1)

    # Feed quality score back into values so red flags can reason about it.
    values["company_quality_score"] = quality_score

    # ---- Layer 2: trajectory scoring (needs history) -----------------------
    trajectory_report = trajectory_mod.compute(snapshot.sector, snapshot.history)
    trajectory_info = TrajectoryInfo(
        sentiment=trajectory_report.sentiment,
        improving_count=trajectory_report.improving_count,
        stable_count=trajectory_report.stable_count,
        declining_count=trajectory_report.declining_count,
        unknown_count=trajectory_report.unknown_count,
    )

    # Attach trajectory badge to each metric evaluation.
    if trajectory_report.per_metric:
        for i, ev in enumerate(evaluations):
            t = trajectory_report.per_metric.get(ev.metric_key)
            if t is not None:
                evaluations[i] = ev.model_copy(update={"trajectory": t.direction})

    # ---- Layer 3: peer-relative overlay -----------------------------------
    if snapshot.sector_percentiles:
        for i, ev in enumerate(evaluations):
            if ev.value is None:
                continue
            higher_is_better = peers_mod.is_higher_is_better(snapshot.sector, ev.metric_key)
            if higher_is_better is None:
                continue
            band = peers_mod.percentile_band_for(
                ev.value, ev.metric_key, snapshot.sector_percentiles, higher_is_better,
            )
            if band is not None:
                evaluations[i] = ev.model_copy(update={"percentile_band": band})

    # ---- Layer 4: red-flag evaluation ----------------------------------------
    expected_keys = tuple(m.key for m in rules.metrics)
    completeness = derived_mod.compute_data_completeness(
        values, expected_keys, rules.critical_metric_keys,
    )
    values["data_completeness"] = completeness

    triggered = red_flags_mod.evaluate_flags(snapshot.sector, values)
    red_flag_infos = [
        RedFlagInfo(
            key=f.key, display_name=f.display_name,
            severity=f.severity, explanation=f.explanation,
        )
        for f in triggered
    ]

    # ---- Layer 5: stability classification --------------------------------
    average_roe = derived_mod.compute_average_over_history(snapshot.history, "roe")
    if average_roe is None:
        average_roe = values.get("roe")
    years_listed = derived_mod.compute_years_listed(snapshot.listed_date)
    stability_tier, stability_reasons = stability_mod.classify(
        stability_mod.StabilityInputs(
            years_listed=years_listed,
            dividend_streak_years=dividend_streak,
            average_roe=average_roe,
            market_cap_percentile=None,  # populated when market-cap peer data is available
            data_completeness=completeness,
        )
    )
    stability_info = StabilityInfo(
        tier=stability_tier,
        display_name=stability_mod.display_name(stability_tier),
        reasons=stability_reasons,
    )

    # ---- Layer 6: verdict -------------------------------------------------
    verdict = verdict_mod.build(
        overall_score=overall,
        quality_score=quality_score,
        valuation_score=valuation_score,
        red_flags=triggered,
        trajectory_sentiment=trajectory_report.sentiment,
        stability_tier=stability_tier,
        data_completeness=completeness,
        has_history=bool(snapshot.history),
        company_name=snapshot.company_name,
    )
    verdict_info = VerdictInfo(
        tier=verdict.tier, display_name=verdict.display_name,
        confidence=verdict.confidence, headline=verdict.headline,
        rationale=verdict.rationale, caps_applied=verdict.caps_applied,
    )

    derived_infos = _derived_metric_infos(values, dividend_streak, earnings_vol)

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
        conclusion=_build_conclusion(
            snapshot.company_name, overall, quality_score, valuation_score, evaluations,
        ),
        verdict=verdict_info,
        stability=stability_info,
        trajectory=trajectory_info,
        red_flags=red_flag_infos,
        derived_metrics=derived_infos,
        data_completeness=completeness,
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
            verdict_tier=r.verdict.tier if r.verdict else None,
            verdict_display_name=r.verdict.display_name if r.verdict else None,
            stability_tier=r.stability.tier if r.stability else None,
            stability_display_name=r.stability.display_name if r.stability else None,
            red_flag_count=len(r.red_flags),
        ))

    winner = rows[0]
    verdict_hint = (
        f" — {winner.verdict_display_name}" if winner.verdict_display_name else ""
    )
    conclusion = (
        f"{winner.company_name} ({winner.company_symbol}) ranks highest on the '{profile}' "
        f"profile with an overall score of {winner.overall_score:.1f}/100{verdict_hint}. "
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
