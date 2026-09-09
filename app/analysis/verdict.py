"""Verdict engine (methodology v2.0).

Combines the six layers of the methodology into a single, actionable tier plus
a confidence badge and a bulleted rationale.

Input:
    * overall_score, quality_score, valuation_score (from the sector engine)
    * triggered red flags
    * trajectory sentiment
    * stability tier
    * data completeness

Output: :class:`Verdict` — tier, confidence, headline, rationale bullets.

The verdict is deliberately conservative: red flags are hard caps, missing
data forces a lower confidence tier, and quality/valuation mismatches produce
a "Watchlist – wait for pullback" tier rather than a Buy.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.analysis.rules.base import RedFlag, cap_verdict


@dataclass(frozen=True)
class Verdict:
    tier: str                     # one of VERDICT_TIERS
    display_name: str
    confidence: str               # "high" | "medium" | "low"
    headline: str                 # one-line summary
    rationale: list[str]          # ordered bullets
    caps_applied: list[str]       # keys of red flags that capped the tier


_TIER_DISPLAY = {
    "strong_buy_candidate": "Strong Buy Candidate",
    "buy_candidate":        "Buy Candidate",
    "watchlist":            "Watchlist",
    "hold":                 "Hold",
    "caution":              "Caution",
    "avoid":                "Avoid",
    "insufficient_data":    "Insufficient Data",
}


def _base_tier_from_scores(
    overall: float,
    quality: float,
    valuation: float,
) -> tuple[str, str]:
    """Score → base tier before red flags / trajectory are applied.

    Returns (tier, headline_hint).
    """
    if overall >= 75 and quality >= 65:
        return "strong_buy_candidate", "Fundamentally strong and reasonably valued"
    if overall >= 65:
        # Quality-strong-but-expensive → Watchlist rather than Buy.
        if quality >= 65 and valuation < 55:
            return "watchlist", "Fundamentally strong but currently expensive — wait for pullback"
        return "buy_candidate", "Meets the methodology's buy thresholds"
    if overall >= 55:
        if quality >= 60 and valuation < 55:
            return "watchlist", "Quality holding up but valuation stretched"
        return "hold", "Mixed profile — no strong buy or sell signal"
    if overall >= 45:
        return "hold", "Below-average fundamentals — hold existing positions and avoid adding"
    return "avoid", "Fundamentals materially below sector norms"


def _apply_red_flag_caps(tier: str, flags: list[RedFlag]) -> tuple[str, list[str]]:
    """Cap the tier if any flag mandates it. Returns (new_tier, applied_keys)."""
    applied: list[str] = []
    for flag in flags:
        prev = tier
        tier = cap_verdict(tier, flag.severity)
        if tier != prev:
            applied.append(flag.key)
    return tier, applied


def _apply_trajectory(tier: str, sentiment: str) -> str:
    """Nudge Buy Candidate up (or down) based on the multi-metric trend."""
    if tier == "buy_candidate" and sentiment == "improving":
        return "strong_buy_candidate"
    if tier in ("strong_buy_candidate", "buy_candidate") and sentiment == "declining":
        return "watchlist"
    if tier == "hold" and sentiment == "improving":
        return "watchlist"
    return tier


def _confidence(data_completeness: float, has_history: bool) -> str:
    if data_completeness >= 0.70 and has_history:
        return "high"
    if data_completeness >= 0.55:
        return "medium"
    return "low"


def build(
    *,
    overall_score: float,
    quality_score: float,
    valuation_score: float,
    red_flags: list[RedFlag],
    trajectory_sentiment: str,
    stability_tier: str,
    data_completeness: float,
    has_history: bool,
    company_name: str,
) -> Verdict:
    """Roll every layer up into a single Verdict."""
    tier, headline = _base_tier_from_scores(overall_score, quality_score, valuation_score)

    tier_after_traj = _apply_trajectory(tier, trajectory_sentiment)
    tier_after_flags, capped_by = _apply_red_flag_caps(tier_after_traj, red_flags)

    confidence = _confidence(data_completeness, has_history)

    rationale: list[str] = []
    rationale.append(
        f"Overall {overall_score:.0f}/100 · Quality {quality_score:.0f} · "
        f"Valuation {valuation_score:.0f}"
    )
    if trajectory_sentiment in ("improving", "declining"):
        rationale.append(f"Multi-quarter trend is {trajectory_sentiment}")
    if stability_tier and stability_tier != "speculative":
        rationale.append(f"Stability: {stability_tier.replace('_', ' ').title()}")
    if capped_by:
        rationale.append(
            f"Verdict capped by {len(capped_by)} red flag(s): {', '.join(capped_by)}"
        )
    if data_completeness < 0.70:
        rationale.append(
            f"Data completeness only {int(data_completeness * 100)}% — confidence reduced"
        )

    display = _TIER_DISPLAY.get(tier_after_flags, tier_after_flags)

    if tier_after_flags == "insufficient_data":
        headline = "Insufficient data to make a call"
    elif capped_by:
        # Red flag messaging wins the headline when a cap fires.
        headline = f"{display} — {red_flags[-1].display_name.lower()}"

    return Verdict(
        tier=tier_after_flags,
        display_name=display,
        confidence=confidence,
        headline=f"{company_name}: {headline}",
        rationale=rationale,
        caps_applied=capped_by,
    )
