from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import OrmModel


class PriceSnapshot(OrmModel):
    ltp: float
    previous_close: float
    change: float
    percent_change: float
    day_high: float
    day_low: float
    week52_high: float
    week52_low: float
    volume: int
    turnover: float
    trades: int
    market_cap: float
    updated_at: datetime
    source: str


class MarketRow(BaseModel):
    symbol: str
    name: str
    sector: str
    ltp: float
    change: float
    percent_change: float
    turnover: float
    volume: int


class MarketOverview(BaseModel):
    total_symbols: int
    total_turnover: float
    total_volume: int
    advancers: int
    decliners: int
    unchanged: int
    top_gainers: list[MarketRow]
    top_losers: list[MarketRow]
    most_traded: list[MarketRow]
    updated_at: datetime
    # NEPSE-level snapshot. `nepse_index` is a turnover-weighted proxy
    # (baseline * (1 + weighted_change)) rather than the true NRB-published
    # index — labelled as an estimate in the client. `nepse_change_percent`
    # is the turnover-weighted daily change across all traded symbols, which
    # tracks direction reliably even if the level is approximate.
    nepse_index: float | None = None
    nepse_change: float | None = None
    nepse_change_percent: float | None = None
    market_status: str = "unknown"  # open / closed / pre_open / unknown
    market_status_label: str = ""   # human-readable e.g. "Closed — reopens Sun 11:00 NPT"
