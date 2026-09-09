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
]


def _signal(score: float) -> str:
    if score >= 70:
        return "strong_buy"
    if score >= 50:
        return "buy"
    return "watch"


def _to_pick(s: _Snapshot, score: float, reasons: list[str]) -> TopPick:
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
        picks = [_to_pick(s, sc, rs) for sc, rs, s in scored[:limit]]
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
