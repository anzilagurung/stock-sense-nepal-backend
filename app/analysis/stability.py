"""Stability classifier (methodology v2.0).

Turns years-listed, dividend streak, average ROE, and (when available) market
capitalisation percentile into a discrete tier:

* ``blue_chip``    — long track record, top-of-sector, dependable dividends
* ``established``  — solid track record but not sector-leading
* ``emerging``     — younger listings still building the record
* ``speculative``  — very young or lacking a track record entirely

The tier is displayed as a badge next to the company name and is one of the
inputs to the verdict engine. It does *not* change the raw score.
"""
from __future__ import annotations

from dataclasses import dataclass


TIER_ORDER = ("speculative", "emerging", "established", "blue_chip")


@dataclass(frozen=True)
class StabilityInputs:
    years_listed: int | None
    dividend_streak_years: int
    average_roe: float | None
    market_cap_percentile: float | None  # 0-100 within sector
    data_completeness: float


def classify(inputs: StabilityInputs) -> tuple[str, list[str]]:
    """Return (tier, reasoning_bullets).

    Reasoning is a small list of human-readable strings used by the verdict
    engine's rationale so the user sees WHY the tier was assigned.
    """
    reasons: list[str] = []

    # Blue Chip: all of the strictest thresholds must hold.
    if (
        (inputs.years_listed is not None and inputs.years_listed >= 10)
        and inputs.dividend_streak_years >= 5
        and (inputs.average_roe is not None and inputs.average_roe >= 12)
        and (
            inputs.market_cap_percentile is None
            or inputs.market_cap_percentile >= 80
        )
        and inputs.data_completeness >= 0.60
    ):
        reasons.append(f"{inputs.years_listed}+ years listed")
        reasons.append(f"{inputs.dividend_streak_years} consecutive dividend years")
        reasons.append(f"Avg ROE {inputs.average_roe:.1f}%")
        return "blue_chip", reasons

    # Established: middle thresholds.
    if (
        (inputs.years_listed is not None and inputs.years_listed >= 5)
        and inputs.dividend_streak_years >= 3
        and (inputs.average_roe is None or inputs.average_roe >= 8)
        and (
            inputs.market_cap_percentile is None
            or inputs.market_cap_percentile >= 50
        )
        and inputs.data_completeness >= 0.45
    ):
        reasons.append(f"{inputs.years_listed}+ years listed")
        reasons.append(f"{inputs.dividend_streak_years} recent dividend years")
        if inputs.average_roe is not None:
            reasons.append(f"Avg ROE {inputs.average_roe:.1f}%")
        return "established", reasons

    # Emerging: at least on-exchange and not entirely dark.
    if inputs.years_listed is not None and inputs.years_listed >= 2:
        reasons.append(f"{inputs.years_listed} years listed")
        if inputs.dividend_streak_years > 0:
            reasons.append(f"{inputs.dividend_streak_years} dividend year(s)")
        return "emerging", reasons

    # Everything else: not enough of a record to lean on.
    if inputs.years_listed is not None:
        reasons.append(f"{inputs.years_listed} year(s) listed")
    else:
        reasons.append("Listing date not on file")
    if inputs.dividend_streak_years == 0:
        reasons.append("No recent dividend history")
    return "speculative", reasons


def display_name(tier: str) -> str:
    return {
        "blue_chip": "Blue Chip",
        "established": "Established",
        "emerging": "Emerging",
        "speculative": "Speculative",
    }.get(tier, tier)
