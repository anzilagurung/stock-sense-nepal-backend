"""Sharesansar historical daily-price scraper.

Uses the same DataTables JSON endpoint the sharesansar company page uses at
``POST /company-price-history``. Each response is one full history for the
requested symbol (typically 3000+ rows going back years), so a single request
per company is enough to populate ~1 year of daily OHLCV.

Flow per symbol:

1. GET ``/company/<slug>`` to obtain the CSRF ``_token`` meta and the numeric
   ``#companyid`` element the page's JS reads.
2. POST ``/company-price-history`` with DataTables-style params + the CSRF
   token in ``X-CSRF-Token``.
3. Parse the JSON and yield :class:`HistoricalPrice` records.

Kept intentionally separate from the *live* :class:`SharesansarSource` so the
live pipeline stays a single cheap request. This scraper is only used by the
one-shot backfill.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

import httpx

USER_AGENT = (
    "stock-sense-nepal/0.1 (+https://github.com/anzilagurung/stock-sense-nepal) "
    "personal decision-support tool"
)
BASE = "https://www.sharesansar.com"
DEFAULT_TIMEOUT = 25.0

_TOKEN_RE = re.compile(r'<meta\s+name="_token"\s+content="([^"]+)"')
_COMPANYID_RE = re.compile(r'id="companyid"[^>]*>([^<]+)<')


@dataclass(frozen=True)
class HistoricalPrice:
    """One daily bar for a symbol."""
    symbol: str
    published_date: str   # "YYYY-MM-DD"
    open: float
    high: float
    low: float
    close: float
    volume: int
    turnover: float


def _num(v, default: float = 0.0) -> float:
    if v is None:
        return default
    s = str(v).replace(",", "").strip()
    if s in {"", "-", "N/A"}:
        return default
    try:
        return float(s)
    except ValueError:
        return default


class SharesansarHistoryClient:
    """Async client with reusable session + polite pacing.

    Reuses the httpx client across all calls so cookies (session, CSRF) persist,
    which cuts the round-trip needed to establish state for every symbol.

    ``request_delay`` is a floor between consecutive requests; keeps us well
    inside sharesansar's tolerance and avoids their WAF getting cross with us.
    """

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        request_delay: float = 0.35,
    ):
        self.timeout = timeout
        self.request_delay = request_delay
        self._client: httpx.AsyncClient | None = None
        self._token: str | None = None  # cached CSRF token from any recent GET

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._client is not None:
            await self._client.aclose()
        self._client = None

    async def _get_company_meta(self, slug: str) -> tuple[str, str]:
        """Return (csrf_token, company_id) for a sharesansar company slug."""
        assert self._client is not None
        r = await self._client.get(f"{BASE}/company/{slug.lower()}")
        r.raise_for_status()
        html = r.text
        tok = _TOKEN_RE.search(html)
        cid = _COMPANYID_RE.search(html)
        if not tok or not cid:
            raise ValueError(
                f"sharesansar company page missing token or companyid for '{slug}'"
            )
        self._token = tok.group(1)
        return self._token, cid.group(1).strip()

    async def fetch_history(
        self,
        symbol: str,
        max_rows: int = 400,
    ) -> list[HistoricalPrice]:
        """Fetch the last ``max_rows`` daily bars for ``symbol``.

        ~400 rows comfortably covers a full trading year (Sun-Thu ≈ 250
        sessions) plus a buffer. Values above sharesansar's DataTables cap
        (usually 1000) are truncated by the server; we don't force it.
        """
        assert self._client is not None
        try:
            token, company_id = await self._get_company_meta(symbol)
        except (httpx.HTTPError, ValueError):
            return []

        # Be polite: sleep between requests to avoid drumming the site.
        await asyncio.sleep(self.request_delay)

        data = {
            "company": company_id,
            "draw": "1",
            "columns[0][data]": "0",
            "columns[0][name]": "",
            "columns[0][searchable]": "true",
            "columns[0][orderable]": "true",
            "order[0][column]": "0",
            "order[0][dir]": "desc",
            "start": "0",
            "length": str(max_rows),
            "search[value]": "",
            "search[regex]": "false",
        }
        try:
            r = await self._client.post(
                f"{BASE}/company-price-history",
                data=data,
                headers={
                    "X-CSRF-Token": token,
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": f"{BASE}/company/{symbol.lower()}",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                },
            )
            r.raise_for_status()
            payload = r.json()
        except (httpx.HTTPError, ValueError):
            return []

        out: list[HistoricalPrice] = []
        for row in payload.get("data", []):
            date = row.get("published_date")
            close = _num(row.get("close"))
            if not date or close <= 0:
                continue
            out.append(HistoricalPrice(
                symbol=symbol.upper(),
                published_date=date,
                open=_num(row.get("open")),
                high=_num(row.get("high")),
                low=_num(row.get("low")),
                close=close,
                volume=int(_num(row.get("traded_quantity"))),
                turnover=_num(row.get("traded_amount")),
            ))
        # Sort oldest → newest so downstream can walk chronologically and
        # populate previous_close from the previous row.
        out.sort(key=lambda p: p.published_date)
        return out
