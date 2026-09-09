from datetime import datetime

from pydantic import BaseModel


class TopPickTechnicals(BaseModel):
    ema20: float | None
    ema50: float | None
    atr14: float | None
    atr_pct: float | None
    volume: int
    avg_volume_20d: float | None
    volume_ratio: float | None
    week52_high: float
    week52_low: float
    distance_from_high_pct: float | None
    distance_from_low_pct: float | None
    trend: str  # uptrend / downtrend / sideways
    percent_change_week: float | None
    percent_change_month: float | None


class PriceProjection(BaseModel):
    """Rule-based forward price track for a pick.

    Not a prediction — a projection built from the stock's own recent
    momentum and volatility (ATR), damped week-over-week to respect
    regression-to-mean. Present in the 'shortterm' and 'longterm' buckets
    only; other buckets omit projections (`None`).
    """
    week1_price: float
    week1_percent: float
    week2_price: float
    week2_percent: float
    week3_price: float
    week3_percent: float
    week4_price: float
    week4_percent: float
    horizon_note: str  # e.g. "Short-term momentum projection · dampened by ATR"


class TopPick(BaseModel):
    symbol: str
    name: str
    sector: str
    ltp: float
    percent_change_day: float
    turnover: float
    score: float  # 0-100
    signal: str   # strong_buy / buy / watch
    reasons: list[str]
    technicals: TopPickTechnicals
    projection: PriceProjection | None = None


class TopPickBucket(BaseModel):
    key: str  # day / week / breakout / value
    title: str
    description: str
    picks: list[TopPick]


class TopPicksResponse(BaseModel):
    generated_at: datetime
    universe_size: int
    buckets: list[TopPickBucket]
    disclaimer: str = (
        "Rule-based technical ranking for educational purposes only. "
        "Not investment advice. Always do your own research."
    )
