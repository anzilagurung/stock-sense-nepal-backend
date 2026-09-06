"""Sharesansar data source.

Concrete implementation of `NepseDataSource` that scrapes the "Today Share Price"
page at `https://www.sharesansar.com/today-share-price`. The page is fully
server-rendered, ships one table (`#headFixed`) with ~340 rows covering the
whole tradeable universe in a single request.

Why we scrape:
- The unofficial community API (surajrimal) is unreliable and non-commercial.
- Sharesansar is a public financial data portal serving human readers; we hit
  it at most once per refresh and identify ourselves in the User-Agent.

Design:
- One HTTP fetch per source instance, cached under an asyncio lock. The runner
  calls `fetch_prices` / `fetch_top_gainers` / `fetch_top_losers` /
  `fetch_summary` concurrently — all four hit the same cached parse.
- Top gainers / losers / summary are derived from the parsed price list; no
  extra HTTP calls needed.
- If the fetch or parse fails, the exception propagates and the runner's
  `_safe` wrapper records it in the FetchReport without aborting the run.
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from app.ingestion.source import MarketSummary, PriceQuote

DEFAULT_URL = "https://www.sharesansar.com/today-share-price"
DEFAULT_TIMEOUT = 20.0
USER_AGENT = (
    "stock-sense-nepal/0.1 (+https://github.com/anzilagurung/stock-sense-nepal) "
    "personal decision-support tool"
)

# Column indices into the sharesansar tbody row (0-based, after S.No).
# Header order (verified 2026-09):
# 0: S.No  1: Symbol  2: Conf.  3: Open  4: High  5: Low  6: Close  7: LTP
# 8: Close-LTP  9: Close-LTP%  10: VWAP  11: Vol  12: Prev.Close
# 13: Turnover  14: Trans.  ...
COL_SYMBOL = 1
COL_OPEN = 3
COL_HIGH = 4
COL_LOW = 5
COL_LTP = 7
COL_CLOSE_LTP = 8
COL_CLOSE_LTP_PCT = 9
COL_VOL = 11
COL_PREV_CLOSE = 12
COL_TURNOVER = 13
COL_TRANS = 14


def _num(cell: str, default: float = 0.0) -> float:
    """Parse '710,976.00' or '-' into a float."""
    if not cell:
        return default
    s = cell.replace(",", "").strip()
    if s in {"", "-", "N/A"}:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _int(cell: str, default: int = 0) -> int:
    return int(_num(cell, float(default)))


class SharesansarSource:
    name = "sharesansar"

    def __init__(self, url: str = DEFAULT_URL, timeout: float = DEFAULT_TIMEOUT):
        self.url = url
        self.timeout = timeout
        self._cache: list[PriceQuote] | None = None
        self._lock = asyncio.Lock()

    async def _get_all(self) -> list[PriceQuote]:
        async with self._lock:
            if self._cache is None:
                self._cache = await self._fetch_and_parse()
            return self._cache

    async def _fetch_and_parse(self) -> list[PriceQuote]:
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
            follow_redirects=True,
        ) as client:
            r = await client.get(self.url)
            r.raise_for_status()
        return _parse_share_price_html(r.text)

    async def fetch_prices(self) -> list[PriceQuote]:
        return await self._get_all()

    async def fetch_top_gainers(self) -> list[PriceQuote]:
        quotes = await self._get_all()
        movers = [q for q in quotes if q.percent_change > 0]
        return sorted(movers, key=lambda q: q.percent_change, reverse=True)[:20]

    async def fetch_top_losers(self) -> list[PriceQuote]:
        quotes = await self._get_all()
        movers = [q for q in quotes if q.percent_change < 0]
        return sorted(movers, key=lambda q: q.percent_change)[:20]

    async def fetch_summary(self) -> MarketSummary:
        quotes = await self._get_all()
        traded = [q for q in quotes if q.volume > 0]
        return MarketSummary(
            total_turnover=sum(q.turnover for q in traded),
            total_traded_shares=sum(q.volume for q in traded),
            total_transactions=sum(q.trades for q in traded),
            total_scrips_traded=len(traded),
            raw={"scraped_at": datetime.utcnow().isoformat(), "source_url": self.url},
        )


def _parse_share_price_html(html: str) -> list[PriceQuote]:
    """Extract PriceQuote rows from the sharesansar today-share-price page.

    Isolated so it can be tested against saved HTML fixtures without network.
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="headFixed") or soup.find("table")
    if table is None:
        raise ValueError("sharesansar: could not locate price table")

    quotes: list[PriceQuote] = []
    for tr in table.find("tbody").find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) <= COL_TRANS:
            continue

        symbol_a = cells[COL_SYMBOL].find("a")
        symbol = (symbol_a.get_text(strip=True) if symbol_a else cells[COL_SYMBOL].get_text(strip=True)).upper()
        if not symbol:
            continue

        ltp = _num(cells[COL_LTP].get_text(strip=True))
        if ltp <= 0:
            # Not traded today — skip. Keeps the "traded scrips" count honest.
            continue

        prev_close = _num(cells[COL_PREV_CLOSE].get_text(strip=True))
        change = _num(cells[COL_CLOSE_LTP].get_text(strip=True))
        pct = _num(cells[COL_CLOSE_LTP_PCT].get_text(strip=True))

        # Some rows report change/pct as 0 when unchanged; that's fine.
        # Derive change/pct if the page cells are blank but we have prev_close.
        if change == 0.0 and prev_close > 0:
            change = round(ltp - prev_close, 2)
        if pct == 0.0 and prev_close > 0:
            pct = round((ltp - prev_close) / prev_close * 100, 2)

        quotes.append(PriceQuote(
            symbol=symbol,
            ltp=ltp,
            previous_close=prev_close,
            change=change,
            percent_change=pct,
            day_high=_num(cells[COL_HIGH].get_text(strip=True)),
            day_low=_num(cells[COL_LOW].get_text(strip=True)),
            volume=_int(cells[COL_VOL].get_text(strip=True)),
            turnover=_num(cells[COL_TURNOVER].get_text(strip=True)),
            trades=_int(cells[COL_TRANS].get_text(strip=True)),
        ))

    return quotes
