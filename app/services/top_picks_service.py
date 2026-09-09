"""Top-picks scoring engine.

Ranks all listed companies across several time-horizon buckets using
technical factors (EMA20/50, ATR14, volume ratio, distance from 52-week
band, short-term trend) that are all derivable from the `market_prices`
table we already ingest daily.

Everything is pure functions over an in-memory list of quotes for one
symbol — no per-symbol DB roundtrips in the hot loop.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, MarketPrice
from app.schemas.top_picks import (
    PriceProjection,
    TopPick,
    TopPickBucket,
    TopPickTechnicals,
    TopPicksResponse,
)


# --- data loading -----------------------------------------------------------


@dataclass(slots=True)
class _Series:
    company: Company
    prices: list[MarketPrice]  # oldest → newest


def _load_series(db: Session, lookback_rows: int = 260) -> list[_Series]:
    """Load the last `lookback_rows` price rows per company (~1 trading year)."""
    # One query, sorted, then bucketed in Python — cheap for a few hundred
    # symbols and avoids N+1.
    rows = db.execute(
        select(Company, MarketPrice)
        .join(MarketPrice, MarketPrice.company_id == Company.id)
        .order_by(Company.id.asc(), MarketPrice.trading_date.asc(), MarketPrice.id.asc())
    ).all()

    grouped: dict[int, _Series] = {}
    for company, price in rows:
        s = grouped.get(company.id)
        if s is None:
            s = _Series(company=company, prices=[])
            grouped[company.id] = s
        s.prices.append(price)

    # Trim each series to the last N rows so subsequent math stays bounded.
    for s in grouped.values():
        if len(s.prices) > lookback_rows:
            s.prices = s.prices[-lookback_rows:]

    return list(grouped.values())


# --- indicators -------------------------------------------------------------


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period or period <= 0:
        return None
    k = 2 / (period + 1)
    # Seed with SMA of the first `period` values.
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema


def _atr(prices: list[MarketPrice], period: int = 14) -> float | None:
    if len(prices) < period + 1:
        return None
    trs: list[float] = []
    for i in range(1, len(prices)):
        p = prices[i]
        prev_close = prices[i - 1].ltp
        hi = p.day_high or p.ltp
        lo = p.day_low or p.ltp
        tr = max(hi - lo, abs(hi - prev_close), abs(lo - prev_close))
        trs.append(tr)
    # Wilder's smoothing.
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def _pct_change_over(prices: list[MarketPrice], lookback_days: int) -> float | None:
    if len(prices) <= lookback_days:
        return None
    then = prices[-1 - lookback_days].ltp
    now = prices[-1].ltp
    if not then:
        return None
    return (now / then - 1) * 100


def _avg_volume(prices: list[MarketPrice], period: int) -> float | None:
    if len(prices) < period:
        return None
    tail = prices[-period:]
    total = sum(p.volume for p in tail)
    return total / period if period else None


def _trend(latest: float, ema20: float | None, ema50: float | None) -> str:
    if ema20 is None or ema50 is None:
        return "sideways"
    if latest > ema20 > ema50:
        return "uptrend"
    if latest < ema20 < ema50:
        return "downtrend"
    return "sideways"


# --- per-symbol snapshot ----------------------------------------------------


@dataclass(slots=True)
class _Snapshot:
    series: _Series
    ltp: float
    percent_change_day: float
    percent_change_week: float | None
    percent_change_month: float | None
    ema20: float | None
    ema50: float | None
    atr14: float | None
    atr_pct: float | None  # ATR as % of price — a normalised volatility gauge
    volume: int
    avg_volume_20d: float | None
    volume_ratio: float | None  # today's volume / 20-day avg
    week52_high: float
    week52_low: float
    distance_from_high_pct: float | None  # positive = below high
    distance_from_low_pct: float | None   # positive = above low
    trend: str

    @property
    def technicals(self) -> TopPickTechnicals:
        return TopPickTechnicals(
            ema20=self.ema20,
            ema50=self.ema50,
            atr14=self.atr14,
            atr_pct=self.atr_pct,
            volume=self.volume,
            avg_volume_20d=self.avg_volume_20d,
            volume_ratio=self.volume_ratio,
            week52_high=self.week52_high,
            week52_low=self.week52_low,
            distance_from_high_pct=self.distance_from_high_pct,
            distance_from_low_pct=self.distance_from_low_pct,
            trend=self.trend,
            percent_change_week=self.percent_change_week,
            percent_change_month=self.percent_change_month,
        )


def _snapshot(series: _Series) -> _Snapshot | None:
    prices = series.prices
    if not prices:
        return None
    latest = prices[-1]
    if not latest.ltp:
        return None

    ltps = [p.ltp for p in prices if p.ltp]
    ema20 = _ema(ltps, 20)
    ema50 = _ema(ltps, 50)
    atr14 = _atr(prices, 14)
    atr_pct = (atr14 / latest.ltp * 100) if (atr14 and latest.ltp) else None

    avg_vol_20 = _avg_volume(prices, 20)
    vol_ratio = (latest.volume / avg_vol_20) if (avg_vol_20 and avg_vol_20 > 0) else None

    hi = latest.week52_high or max((p.day_high or p.ltp for p in prices), default=latest.ltp)
    lo = latest.week52_low or min(
        (p.day_low or p.ltp for p in prices if (p.day_low or p.ltp)),
        default=latest.ltp,
    )
    dist_high = ((hi - latest.ltp) / hi * 100) if hi else None
    dist_low = ((latest.ltp - lo) / lo * 100) if lo else None

    return _Snapshot(
        series=series,
        ltp=latest.ltp,
        percent_change_day=latest.percent_change,
        percent_change_week=_pct_change_over(prices, 5),
        percent_change_month=_pct_change_over(prices, 20),
        ema20=ema20,
        ema50=ema50,
        atr14=atr14,
        atr_pct=atr_pct,
        volume=latest.volume,
        avg_volume_20d=avg_vol_20,
        volume_ratio=vol_ratio,
        week52_high=hi,
        week52_low=lo,
        distance_from_high_pct=dist_high,
        distance_from_low_pct=dist_low,
        trend=_trend(latest.ltp, ema20, ema50),
    )


# --- bucket scorers ---------------------------------------------------------

# Each scorer returns (score, reasons) for a snapshot, or `None` if the
# snapshot doesn't qualify for that bucket. Scores are on a 0-100-ish scale
# — they don't need to be strictly bounded, we only sort by them.


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _score_day(s: _Snapshot) -> tuple[float, list[str]] | None:
    # Needs positive intraday move; volume backing helps but isn't required
    # for stocks that are structurally low-volume.
    if s.percent_change_day <= 0.3:
        return None
    # Filter noise — a stock with zero turnover today isn't a real momentum
    # candidate even if the printed %chg is high.
    if s.series.prices[-1].turnover <= 0 or s.volume <= 0:
        return None
    reasons: list[str] = []
    score = _clip(s.percent_change_day, 0, 10) * 6  # up to ~60 from %chg
    reasons.append(f"Up {s.percent_change_day:.2f}% today")

    if s.volume_ratio and s.volume_ratio > 1.2:
        score += _clip((s.volume_ratio - 1) * 15, 0, 25)
        reasons.append(f"Volume {s.volume_ratio:.1f}x its 20-day average")

    if s.trend == "uptrend":
        score += 10
        reasons.append("Trading above both EMA20 and EMA50")
    elif s.trend == "downtrend":
        score -= 15
        reasons.append("Still under both EMA20 and EMA50 — early bounce")

    # Only flag proximity to 52-week high when we have a real range to
    # compare against (otherwise this is a data artifact, not a signal).
    if (
        s.distance_from_high_pct is not None
        and s.distance_from_high_pct < 5
        and s.week52_high > s.week52_low * 1.02
    ):
        score += 5
        reasons.append(f"Within {s.distance_from_high_pct:.1f}% of 52-week high")

    return score, reasons


def _score_week(s: _Snapshot) -> tuple[float, list[str]] | None:
    pw = s.percent_change_week
    if pw is None or pw <= 1:
        return None
    reasons: list[str] = []
    score = _clip(pw, 0, 20) * 3  # up to ~60
    reasons.append(f"Up {pw:.2f}% over the last 5 sessions")

    if s.trend == "uptrend":
        score += 15
        reasons.append("Uptrend confirmed: price > EMA20 > EMA50")
    elif s.trend == "downtrend":
        score -= 20

    if s.volume_ratio and s.volume_ratio > 1.0:
        score += _clip((s.volume_ratio - 1) * 10, 0, 15)
        reasons.append(f"Volume support ({s.volume_ratio:.1f}x avg)")

    if s.atr_pct is not None and s.atr_pct < 4:
        score += 5
        reasons.append(f"Moderate volatility (ATR {s.atr_pct:.1f}%)")

    return score, reasons


def _score_breakout(s: _Snapshot) -> tuple[float, list[str]] | None:
    d = s.distance_from_high_pct
    if d is None or d > 10:
        return None
    if s.trend == "downtrend":
        return None
    # Skip stocks with a collapsed 52-week range — usually means we only have
    # one price row and hi == lo == ltp, which makes every distance metric 0.
    if s.week52_high <= s.week52_low * 1.02:
        return None
    reasons: list[str] = []
    score = _clip(10 - d, 0, 10) * 5  # closer to high scores higher (up to 50)
    reasons.append(f"Only {d:.1f}% below its 52-week high")

    if s.trend == "uptrend":
        score += 20
        reasons.append("Confirmed uptrend on EMA stack")

    if s.volume_ratio and s.volume_ratio > 1.3:
        score += _clip((s.volume_ratio - 1) * 15, 0, 20)
        reasons.append(f"Breakout volume {s.volume_ratio:.1f}x average")

    pw = s.percent_change_week or 0
    if pw > 0:
        score += _clip(pw, 0, 10)
        reasons.append(f"Weekly momentum +{pw:.1f}%")

    return score, reasons


def _score_value(s: _Snapshot) -> tuple[float, list[str]] | None:
    d = s.distance_from_low_pct
    if d is None or d > 20:
        return None
    # Skip collapsed ranges (see breakout scorer for context).
    if s.week52_high <= s.week52_low * 1.02:
        return None
    # A true "value" candidate needs to actually be beaten down — at least
    # 15% off its yearly high — otherwise every rangebound stock qualifies.
    if s.distance_from_high_pct is None or s.distance_from_high_pct < 15:
        return None
    # Require a reversal signal — either today green or weekly not falling hard.
    reversal_ok = s.percent_change_day > 0 or (s.percent_change_week and s.percent_change_week > -2)
    if not reversal_ok:
        return None
    reasons: list[str] = []
    score = _clip(20 - d, 0, 20) * 2  # closer to low scores higher (up to 40)
    reasons.append(f"Only {d:.1f}% above its 52-week low")

    if s.percent_change_day > 0:
        score += _clip(s.percent_change_day, 0, 5) * 3
        reasons.append(f"Bouncing today (+{s.percent_change_day:.2f}%)")

    if s.trend != "downtrend":
        score += 10
        reasons.append(f"Trend no longer bearish ({s.trend})")
    else:
        score -= 10

    if s.atr_pct is not None and s.atr_pct < 5:
        score += 5
        reasons.append(f"Contained volatility (ATR {s.atr_pct:.1f}%)")

    if s.volume_ratio and s.volume_ratio > 1.0:
        score += _clip((s.volume_ratio - 1) * 8, 0, 12)
        reasons.append(f"Volume picking up ({s.volume_ratio:.1f}x)")

    return score, reasons


def _score_shortterm(s: _Snapshot) -> tuple[float, list[str]] | None:
    """Rank names suited to a 1–4 week horizon.

    Filters aim to reject stocks that already ran too hard (< 3% off the
    52-week high often has no room), or that are structurally too volatile
    to project cleanly. Score rewards trend confirmation, moderate weekly
    momentum, and volume support.
    """
    pw = s.percent_change_week
    if pw is None:
        return None
    # Need a healthy trend or an early up-move to be considered.
    if s.trend == "downtrend":
        return None
    # Skip stocks with a collapsed / one-row 52-week range.
    if s.week52_high <= s.week52_low * 1.02:
        return None
    # No thin-air names — must actually trade.
    if s.series.prices[-1].turnover <= 0 or s.volume <= 0:
        return None
    # If it's already parabolic (up >15% this week) skip — too late to enter.
    if pw > 15:
        return None
    # Need some upside room vs 52-week high — arbitrarily > 3%.
    if s.distance_from_high_pct is not None and s.distance_from_high_pct < 3:
        return None
    # Reject very illiquid names via ATR-pct sanity (extreme volatility ⇒
    # projection would be meaningless).
    if s.atr_pct is not None and s.atr_pct > 8:
        return None

    reasons: list[str] = []
    score = 0.0

    # Trend anchor.
    if s.trend == "uptrend":
        score += 30
        reasons.append("EMA20 > EMA50 uptrend — direction confirmed")
    else:
        score += 12
        reasons.append("Sideways structure — waiting for continuation")

    # Weekly momentum band: reward 1–8% moves, penalise weakness.
    if pw >= 1:
        score += _clip(pw, 0, 8) * 3
        reasons.append(f"Weekly momentum +{pw:.2f}%")
    elif pw >= -1:
        score += 4  # small credit for sideways-not-falling
    else:
        return None  # weekly loss disqualifies short-term entry

    # Volume backing.
    if s.volume_ratio and s.volume_ratio > 1.0:
        score += _clip((s.volume_ratio - 1) * 12, 0, 18)
        reasons.append(f"Volume {s.volume_ratio:.1f}x its 20-day average")

    # Room-to-run vs 52-week high.
    if s.distance_from_high_pct is not None:
        room = s.distance_from_high_pct
        if 3 <= room <= 20:
            score += _clip(20 - room, 0, 15)
            reasons.append(f"Room to move — {room:.1f}% below 52w high")

    # Prefer moderate volatility (2–5% ATR); punish extremes.
    if s.atr_pct is not None:
        if 1.5 <= s.atr_pct <= 5:
            score += 8
        elif s.atr_pct < 1.5:
            score += 3  # too tight, weaker projected move
        else:
            score -= 5

    return score, reasons


def _score_longterm(s: _Snapshot) -> tuple[float, list[str]] | None:
    """Rank names suited to gradual accumulation over months.

    We favour steady up-trending stocks with low-to-moderate volatility,
    consistent uptrend structure, at least modest 1-month strength, and a
    price that hasn't collapsed toward the 52-week low. This is a
    technical proxy for "quality accumulation candidate" — the Analysis
    screen still has the final fundamental say.
    """
    if s.trend != "uptrend":
        return None
    if s.week52_high <= s.week52_low * 1.02:
        return None
    if s.series.prices[-1].turnover <= 0 or s.volume <= 0:
        return None
    # Long-horizon names should be relatively calm.
    if s.atr_pct is None or s.atr_pct > 5.5:
        return None
    # Must be well above the 52-week low (not a falling-knife).
    if s.distance_from_low_pct is None or s.distance_from_low_pct < 15:
        return None
    pm = s.percent_change_month
    if pm is None or pm < -3:
        return None  # sliding-hard names don't belong in accumulation
    # Skip parabolic entries — long-term accumulation prefers pullbacks.
    if s.distance_from_high_pct is not None and s.distance_from_high_pct < 2:
        return None

    reasons: list[str] = []
    score = 40  # base credit for passing filters

    # Uptrend firmness (how far above EMA50).
    if s.ema50 and s.ltp:
        above_ema50 = (s.ltp / s.ema50 - 1) * 100
        if 0 < above_ema50 <= 15:
            score += _clip(above_ema50, 0, 15)
            reasons.append(f"Trading {above_ema50:.1f}% above EMA50 — durable uptrend")

    # Monthly performance credit.
    if pm >= 0:
        score += _clip(pm, 0, 12) * 1.5
        reasons.append(f"One-month strength +{pm:.1f}%")

    # Low volatility bonus.
    if s.atr_pct <= 3:
        score += 10
        reasons.append(f"Low volatility (ATR {s.atr_pct:.1f}%) — suits accumulation")
    elif s.atr_pct <= 5:
        score += 5

    # Volume presence (need real liquidity for gradual buys).
    if s.volume_ratio and s.volume_ratio >= 0.8:
        score += _clip((s.volume_ratio - 0.5) * 6, 0, 12)
        reasons.append(f"Volume {s.volume_ratio:.1f}x avg — enough liquidity to accumulate")

    # Distance-from-low: reward mid-range names (not too close to top).
    d_low = s.distance_from_low_pct
    if 20 <= d_low <= 60:
        score += 6
        reasons.append(f"{d_low:.0f}% above 52w low — established recovery")

    return score, reasons


_BUCKETS = [
    (
        "day",
        "Today's Momentum",
        "Stocks moving up today with volume and trend backing.",
        _score_day,
    ),
    (
        "week",
        "Weekly Leaders",
        "Sustained 5-session gainers with a healthy EMA trend.",
        _score_week,
    ),
    (
        "breakout",
        "52-Week Breakout",
        "Trading close to their yearly high on strong volume — momentum plays.",
        _score_breakout,
    ),
    (
        "value",
        "Value Near 52-Week Low",
        "Beaten-down names showing early reversal signs from the low.",
        _score_value,
    ),
    (
        "shortterm",
        "Short-term (1–4 weeks)",
        "Trend-aligned names with room to run over the next few weeks. "
        "Projected prices use recent momentum dampened by ATR volatility.",
        _score_shortterm,
    ),
    (
        "longterm",
        "Long-term Accumulation",
        "Steady up-trending names with low-to-moderate volatility — suited to "
        "adding shares in tranches (5/10/50 at a time) over months.",
        _score_longterm,
    ),
]

_BUCKETS_WITH_PROJECTION = {"shortterm", "longterm"}


def _projection_for(s: _Snapshot, bucket_key: str) -> PriceProjection | None:
    """Build a 4-week price track for a pick.

    Short-term bucket blends weekly momentum with an ATR-derived expected
    move, then dampens week-over-week (weeks 2–4 add progressively less)
    to respect regression-to-mean. Long-term bucket uses a much muter,
    monthly-anchored trajectory: it exists so the UI can compare, but the
    numbers are small and clearly framed as "gradual accumulation".
    """
    if s.ltp <= 0:
        return None

    atr_expected_weekly = s.atr_pct * 1.5 if s.atr_pct else 1.5  # ~1σ over a week
    pw = s.percent_change_week or 0
    pm = s.percent_change_month or 0

    if bucket_key == "shortterm":
        # Blend: 40% of last week's move + 30% of ATR-implied weekly move.
        base_weekly = 0.4 * max(0.0, pw) + 0.3 * atr_expected_weekly
        base_weekly = _clip(base_weekly, 0.4, 6.0)  # keep projections sane
        weekly_pcts = [
            round(base_weekly * 1.0, 2),
            round(base_weekly * 1.7, 2),
            round(base_weekly * 2.2, 2),
            round(base_weekly * 2.6, 2),
        ]
        note = (
            "Short-term projection: 40% of last week's momentum + "
            "ATR-implied expected move, dampened week over week."
        )
    elif bucket_key == "longterm":
        # Long-term accumulation: convert monthly strength to a small
        # weekly drift; keep the trajectory shallow (accumulation buyers
        # don't chase). Floor at 0.3% weekly so it stays informative.
        monthly = max(0.0, pm) / 4.0  # per-week share of monthly move
        base_weekly = _clip(0.5 * monthly + 0.15 * atr_expected_weekly, 0.3, 2.5)
        weekly_pcts = [
            round(base_weekly * 1.0, 2),
            round(base_weekly * 1.9, 2),
            round(base_weekly * 2.7, 2),
            round(base_weekly * 3.4, 2),
        ]
        note = (
            "Long-term projection: monthly trend + volatility floor, "
            "shallow by design — good for staged buying, not swing trades."
        )
    else:
        return None

    def px(pct: float) -> float:
        return round(s.ltp * (1 + pct / 100), 2)

    return PriceProjection(
        week1_price=px(weekly_pcts[0]),
        week1_percent=weekly_pcts[0],
        week2_price=px(weekly_pcts[1]),
        week2_percent=weekly_pcts[1],
        week3_price=px(weekly_pcts[2]),
        week3_percent=weekly_pcts[2],
        week4_price=px(weekly_pcts[3]),
        week4_percent=weekly_pcts[3],
        horizon_note=note,
    )


def _signal(score: float) -> str:
    if score >= 70:
        return "strong_buy"
    if score >= 50:
        return "buy"
    return "watch"


def _to_pick(
    s: _Snapshot, score: float, reasons: list[str], bucket_key: str,
) -> TopPick:
    projection = (
        _projection_for(s, bucket_key)
        if bucket_key in _BUCKETS_WITH_PROJECTION
        else None
    )
    return TopPick(
        symbol=s.series.company.symbol,
        name=s.series.company.name,
        sector=s.series.company.sector,
        ltp=s.ltp,
        percent_change_day=s.percent_change_day,
        turnover=s.series.prices[-1].turnover,
        score=round(_clip(score, 0, 100), 1),
        signal=_signal(score),
        reasons=reasons,
        technicals=s.technicals,
        projection=projection,
    )


def build_top_picks(db: Session, limit: int = 5) -> TopPicksResponse:
    all_series = _load_series(db)
    snapshots: list[_Snapshot] = []
    for series in all_series:
        snap = _snapshot(series)
        if snap:
            snapshots.append(snap)

    buckets: list[TopPickBucket] = []
    for key, title, description, scorer in _BUCKETS:
        scored: list[tuple[float, list[str], _Snapshot]] = []
        for s in snapshots:
            result = scorer(s)
            if result is None:
                continue
            score, reasons = result
            scored.append((score, reasons, s))
        scored.sort(key=lambda t: t[0], reverse=True)
        picks = [_to_pick(s, sc, rs, key) for sc, rs, s in scored[:limit]]
        buckets.append(TopPickBucket(
            key=key,
            title=title,
            description=description,
            picks=picks,
        ))

    return TopPicksResponse(
        generated_at=datetime.utcnow(),
        universe_size=len(snapshots),
        buckets=buckets,
    )
