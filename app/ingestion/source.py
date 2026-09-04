"""Abstract data-source contract.

A `NepseDataSource` returns typed dicts for the pieces of the market we care about.
Concrete implementations exist in this package. The rest of the ingestion pipeline
never depends on any particular provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class PriceQuote:
    symbol: str
    ltp: float
    previous_close: float
    change: float
    percent_change: float
    day_high: float = 0.0
    day_low: float = 0.0
    volume: int = 0
    turnover: float = 0.0
    trades: int = 0
    updated_at: str | None = None


@dataclass
class MarketSummary:
    total_turnover: float = 0.0
    total_traded_shares: int = 0
    total_transactions: int = 0
    total_scrips_traded: int = 0
    raw: dict = field(default_factory=dict)


@dataclass
class FetchReport:
    provider: str
    ok: bool
    prices: int = 0
    top_movers: int = 0
    summary_ok: bool = False
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


class NepseDataSource(Protocol):
    name: str

    async def fetch_prices(self) -> list[PriceQuote]: ...

    async def fetch_top_gainers(self) -> list[PriceQuote]: ...

    async def fetch_top_losers(self) -> list[PriceQuote]: ...

    async def fetch_summary(self) -> MarketSummary: ...
