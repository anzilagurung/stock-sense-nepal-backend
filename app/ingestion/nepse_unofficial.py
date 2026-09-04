"""Unofficial NEPSE data source.

Concrete implementation of `NepseDataSource` targeting the community-run REST API at
`https://nepseapi.surajrimal.dev` (or a self-hosted mirror configured via env).

Endpoint contracts follow surajrimal07/NepseAPI-Unofficial (MIT) — see the bundled
snapshot in `_reference/server.py`.

**Licensing note:** the upstream service is strictly non-commercial and provides no
uptime SLA. This client is intentionally short-timeout and always fails soft — a
downed upstream must never bring down our own backend.
"""
from __future__ import annotations

import httpx

from app.ingestion.source import MarketSummary, NepseDataSource, PriceQuote

DEFAULT_BASE = "https://nepseapi.surajrimal.dev"
DEFAULT_TIMEOUT = 8.0  # seconds — kept short so failures don't block user requests


def _f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _i(v, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


class NepseUnofficialSource:
    name = "nepse_unofficial"

    def __init__(self, base_url: str = DEFAULT_BASE, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _get(self, path: str):
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": "stock-sense-nepal/0.1 (+dev)"},
        ) as client:
            r = await client.get(f"{self.base_url}{path}")
            r.raise_for_status()
            return r.json()

    async def fetch_prices(self) -> list[PriceQuote]:
        data = await self._get("/PriceVolume")
        out: list[PriceQuote] = []
        for row in data or []:
            symbol = row.get("symbol") or row.get("scrip")
            if not symbol:
                continue
            ltp = _f(row.get("lastTradedPrice") or row.get("ltp"))
            prev = _f(row.get("previousClose"))
            change = ltp - prev if ltp and prev else _f(row.get("pointChange"))
            pct = (change / prev * 100) if prev else _f(row.get("percentageChange"))
            out.append(PriceQuote(
                symbol=symbol,
                ltp=ltp,
                previous_close=prev,
                change=change,
                percent_change=pct,
                day_high=_f(row.get("highPrice")),
                day_low=_f(row.get("lowPrice")),
                volume=_i(row.get("totalTradedQuantity") or row.get("shareTraded")),
                turnover=_f(row.get("totalTradedValue") or row.get("turnover")),
                trades=_i(row.get("totalTrades")),
                updated_at=row.get("lastUpdatedDateTime") or row.get("businessDate"),
            ))
        return out

    async def _movers(self, path: str) -> list[PriceQuote]:
        data = await self._get(path)
        out: list[PriceQuote] = []
        for row in data or []:
            symbol = row.get("symbol")
            if not symbol:
                continue
            ltp = _f(row.get("ltp"))
            change = _f(row.get("pointChange"))
            pct = _f(row.get("percentageChange"))
            prev = ltp - change if ltp and change else 0.0
            out.append(PriceQuote(
                symbol=symbol,
                ltp=ltp,
                previous_close=prev,
                change=change,
                percent_change=pct,
            ))
        return out

    async def fetch_top_gainers(self) -> list[PriceQuote]:
        return await self._movers("/TopGainers")

    async def fetch_top_losers(self) -> list[PriceQuote]:
        return await self._movers("/TopLosers")

    async def fetch_summary(self) -> MarketSummary:
        raw = await self._get("/Summary")
        # /Summary returns { "Total Turnover Rs:": <n>, "Total Traded Shares": <n>, ... }
        if not isinstance(raw, dict):
            raw = {}
        return MarketSummary(
            total_turnover=_f(raw.get("Total Turnover Rs:")),
            total_traded_shares=_i(raw.get("Total Traded Shares")),
            total_transactions=_i(raw.get("Total Transactions")),
            total_scrips_traded=_i(raw.get("Total Scrips Traded")),
            raw=raw,
        )


# Sanity check that this class matches the Protocol at type-check time.
_check: NepseDataSource = NepseUnofficialSource()  # noqa: F841
