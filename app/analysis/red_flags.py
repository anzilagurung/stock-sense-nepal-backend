"""Sector-specific red-flag rules (methodology v2.0).

A red flag caps the verdict tier when triggered — it does NOT change the raw
0-100 scores. The point is to surface hard-stop concerns that a blended average
would otherwise hide (a bank with 25% NPL can still score decently on P/E
alone, but any prudent screen should refuse to call it a buy candidate).

Each rule is a :class:`RedFlag` with a small callable that reads the merged
values dict (raw + derived) and returns True when the flag fires.

Rules are grouped by sector name (matching ``SECTOR_RULES`` keys). Universal
rules (data completeness, value-trap) live in ``UNIVERSAL_FLAGS`` and are
evaluated for every sector.
"""
from __future__ import annotations

from app.analysis.rules.base import RedFlag


def _val(values: dict[str, float | None], key: str) -> float | None:
    v = values.get(key)
    return v if isinstance(v, (int, float)) else None


def _gt(values: dict[str, float | None], key: str, threshold: float) -> bool:
    v = _val(values, key)
    return v is not None and v > threshold


def _lt(values: dict[str, float | None], key: str, threshold: float) -> bool:
    v = _val(values, key)
    return v is not None and v < threshold


# -- Universal flags (applied to every sector) --------------------------------

UNIVERSAL_FLAGS: tuple[RedFlag, ...] = (
    RedFlag(
        key="insufficient_data",
        display_name="Insufficient data",
        severity="insufficient_data",
        condition=lambda v: _lt(v, "data_completeness", 0.40),
        explanation="Less than 40% of the sector's key metrics have data. Score is not reliable enough to act on — treat as a research target rather than a decision.",
    ),
    RedFlag(
        key="consecutive_losses",
        display_name="Consecutive quarterly losses",
        severity="avoid",
        condition=lambda v: _gt(v, "consecutive_loss_quarters", 1.5),
        explanation="Two or more consecutive quarters of losses. The business is not currently earning — wait for a return to profitability before treating this as investable.",
    ),
    RedFlag(
        key="value_trap",
        display_name="Possible value trap",
        severity="caution",
        condition=lambda v: _lt(v, "pe", 12) and _lt(v, "company_quality_score", 55),
        explanation="Price/Earnings looks cheap, but company quality is below sector norms. Cheap valuation combined with weak fundamentals often means the market is pricing in a real problem — investigate before assuming it's a bargain.",
    ),
    RedFlag(
        key="peg_stretched",
        display_name="Growth-adjusted valuation stretched",
        severity="caution",
        condition=lambda v: _gt(v, "peg_ratio", 3.0),
        explanation="P/E is high relative to earnings growth (PEG > 3). Even good businesses become risky at these levels — small growth disappointments can trigger sharp re-rating.",
    ),
    RedFlag(
        key="dividend_uncovered",
        display_name="Dividend not comfortably covered",
        severity="caution",
        condition=lambda v: _val(v, "dividend_yield") is not None
        and (_val(v, "dividend_yield") or 0) > 4
        and _lt(v, "dividend_coverage", 1.2),
        explanation="A meaningful dividend is being paid without adequate earnings coverage (EPS/DPS below 1.2x). The dividend may not be sustainable if earnings dip.",
    ),
)


# -- Bank-family flags (Commercial, Development, Finance) ---------------------

_BANK_FLAGS: tuple[RedFlag, ...] = (
    RedFlag(
        key="npl_critical",
        display_name="NPL above safe ceiling",
        severity="avoid",
        condition=lambda v: _gt(v, "npl", 7.0),
        explanation="Non-performing loans above 7% is a hard-stop concern. Additional provisioning obligations will suppress distributable profit and can force capital raises.",
    ),
    RedFlag(
        key="npl_elevated",
        display_name="NPL elevated",
        severity="caution",
        condition=lambda v: _gt(v, "npl", 5.0) and not _gt(v, "npl", 7.0),
        explanation="NPL between 5% and 7% is above what the sector's best-run peers show. Watch the trend closely before treating profitability as sustainable.",
    ),
    RedFlag(
        key="car_thin",
        display_name="Capital buffer near NRB floor",
        severity="caution",
        condition=lambda v: _lt(v, "car", 11.2),
        explanation="Capital adequacy ratio is within 0.2% of NRB's regulatory floor (11%). Very little cushion against unexpected losses or growth in risk-weighted assets.",
    ),
)


# -- Microfinance flags -------------------------------------------------------

_MFI_FLAGS: tuple[RedFlag, ...] = (
    RedFlag(
        key="par30_critical",
        display_name="Portfolio at Risk above safe ceiling",
        severity="avoid",
        condition=lambda v: _gt(v, "portfolio_at_risk", 7.0) or _gt(v, "par30", 7.0),
        explanation="PAR30 above 7% signals a materially deteriorated loan book — provisioning obligations will suppress earnings and can force distress recovery.",
    ),
    RedFlag(
        key="npl_elevated",
        display_name="NPL elevated",
        severity="caution",
        condition=lambda v: _gt(v, "npl", 5.0),
        explanation="NPL above 5% is elevated even for the MFI class. Watch the trend before treating the yield as sustainable.",
    ),
)


# -- Insurance flags ----------------------------------------------------------

_INSURANCE_FLAGS: tuple[RedFlag, ...] = (
    RedFlag(
        key="solvency_thin",
        display_name="Solvency near regulator floor",
        severity="caution",
        condition=lambda v: _lt(v, "solvency_ratio", 155),
        explanation="Solvency ratio within 5% of Nepal Insurance Authority's 150% floor. Little headroom to absorb an adverse loss year or asset write-down.",
    ),
    RedFlag(
        key="combined_ratio_over_100",
        display_name="Underwriting unprofitable",
        severity="caution",
        condition=lambda v: _gt(v, "combined_ratio", 100),
        explanation="Combined ratio above 100% means claims + expenses exceed premium — the book itself is losing money and only investment income keeps it afloat.",
    ),
)


# -- Leverage-heavy sectors (Hydro, Manufacturing, Hotels) --------------------

_LEVERAGED_FLAGS: tuple[RedFlag, ...] = (
    RedFlag(
        key="interest_uncovered",
        display_name="Interest not covered",
        severity="avoid",
        condition=lambda v: _lt(v, "interest_coverage", 1.0),
        explanation="Operating profit does not cover interest expense. Debt service is being funded from cash reserves or new borrowing — a critical risk if continued.",
    ),
    RedFlag(
        key="leverage_stretched",
        display_name="Leverage stretched",
        severity="caution",
        condition=lambda v: _gt(v, "debt_to_equity", 3.0) and _lt(v, "interest_coverage", 2.0),
        explanation="High debt (D/E > 3x) combined with thin interest coverage (< 2x). Small operating hiccups can quickly cascade into default risk.",
    ),
)


# -- Hydro-specific -----------------------------------------------------------

_HYDRO_FLAGS: tuple[RedFlag, ...] = _LEVERAGED_FLAGS + (
    RedFlag(
        key="plf_collapsed",
        display_name="Plant Load Factor very low",
        severity="caution",
        condition=lambda v: _lt(v, "plant_load_factor", 25),
        explanation="PLF below 25% is far below typical Nepali run-of-river ranges (40–60%). Could be dry-season timing or an operational problem — verify before assuming this is a normal quarter.",
    ),
)


# -- Sector registry ----------------------------------------------------------

SECTOR_RED_FLAGS: dict[str, tuple[RedFlag, ...]] = {
    "Commercial Banks":            _BANK_FLAGS,
    "Development Banks":           _BANK_FLAGS,
    "Finance":                     _BANK_FLAGS,
    "Microfinance":                _MFI_FLAGS,
    "Life Insurance":              _INSURANCE_FLAGS,
    "Non Life Insurance":          _INSURANCE_FLAGS,
    "Hydro Power":                 _HYDRO_FLAGS,
    "Hotels And Tourism":          _LEVERAGED_FLAGS,
    "Manufacturing And Processing": _LEVERAGED_FLAGS,
    "Tradings":                    _LEVERAGED_FLAGS,
    "Others":                      (),
    "Investment":                  (),
    "Mutual Fund":                 (),
}


def flags_for_sector(sector: str) -> tuple[RedFlag, ...]:
    """All flags (universal + sector-specific) that should be evaluated."""
    return UNIVERSAL_FLAGS + SECTOR_RED_FLAGS.get(sector, ())


def evaluate_flags(
    sector: str,
    values: dict[str, float | None],
) -> list[RedFlag]:
    """Return every flag whose condition currently fires. Order preserved."""
    triggered: list[RedFlag] = []
    for flag in flags_for_sector(sector):
        try:
            if flag.condition(values):
                triggered.append(flag)
        except (KeyError, TypeError, ValueError):
            # A malformed value dict never crashes the flag layer — the flag
            # just doesn't fire.
            continue
    return triggered
