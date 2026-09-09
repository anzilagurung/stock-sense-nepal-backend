from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, MarketPrice
from app.schemas.market import MarketOverview, MarketRow


# NEPSE cash-market sessions: Sun-Thu, 11:00-15:00 Nepal time (UTC+05:45).
# Fri & Sat closed. Public holidays are not modelled here — the client just
# reports "closed" for those days too based on the last update timestamp.
_NPT = timezone(timedelta(hours=5, minutes=45))
_OPEN_HOUR = 11
_CLOSE_HOUR = 15
_TRADING_WEEKDAYS = {6, 0, 1, 2, 3}  # Sun=6, Mon=0 ... Thu=3 (Python weekday())

# Proxy baseline for the NEPSE index level. We don't ingest the true NRB
# index yet, so we anchor to a recent published level and apply the
# turnover-weighted daily change on top. Direction is accurate; the level
# is an estimate and is flagged as such in the client.
_NEPSE_BASELINE = 2200.0


def _latest_price_per_company(db: Session) -> list[tuple[Company, MarketPrice]]:
    rows = db.execute(
        select(Company, MarketPrice)
        .join(MarketPrice, MarketPrice.company_id == Company.id)
        .order_by(MarketPrice.trading_date.desc(), MarketPrice.id.desc())
    ).all()

    latest: dict[int, tuple[Company, MarketPrice]] = {}
    for company, price in rows:
        if company.id not in latest:
            latest[company.id] = (company, price)
    return list(latest.values())


def _market_status(now_utc: datetime) -> tuple[str, str]:
    """Return (status, human_label) for the NEPSE cash market.

    Weekday map: Python's `weekday()` returns Mon=0..Sun=6. NEPSE trades
    Sun-Thu, so the allow-list is {6, 0, 1, 2, 3}.
    """
    now_npt = now_utc.astimezone(_NPT)
    weekday = now_npt.weekday()
    hour = now_npt.hour
    minute = now_npt.minute

    if weekday not in _TRADING_WEEKDAYS:
        return "closed", "Closed — weekend. Trading resumes Sun 11:00 NPT."
    if hour < _OPEN_HOUR:
        return "pre_open", f"Pre-open — trading starts at {_OPEN_HOUR:02d}:00 NPT."
    if hour >= _CLOSE_HOUR:
        return "closed", "Closed for the day — trading resumes 11:00 NPT next session."
    return "open", f"Open — closes at {_CLOSE_HOUR:02d}:00 NPT ({_CLOSE_HOUR - hour}h {60 - minute if minute else 0}m left)."


def _index_snapshot(rows: list[MarketRow]) -> tuple[float | None, float | None, float | None]:
    """Turnover-weighted proxy for the NEPSE daily direction.

    Returns (level, change, percent_change) where `level` is baseline *
    (1 + weighted_pct / 100) — approximate but honest about direction.
    """
    traded = [r for r in rows if r.turnover > 0]
    if not traded:
        return None, None, None
    total_turnover = sum(r.turnover for r in traded)
    if total_turnover <= 0:
        return None, None, None
    weighted_pct = sum(r.percent_change * r.turnover for r in traded) / total_turnover
    level = round(_NEPSE_BASELINE * (1 + weighted_pct / 100), 2)
    change = round(level - _NEPSE_BASELINE, 2)
    return level, change, round(weighted_pct, 3)


def build_overview(db: Session) -> MarketOverview:
    pairs = _latest_price_per_company(db)

    def row(company: Company, price: MarketPrice) -> MarketRow:
        return MarketRow(
            symbol=company.symbol,
            name=company.name,
            sector=company.sector,
            ltp=price.ltp,
            change=price.change,
            percent_change=price.percent_change,
            turnover=price.turnover,
            volume=price.volume,
        )

    rows = [row(c, p) for c, p in pairs]
    advancers = sum(1 for r in rows if r.change > 0)
    decliners = sum(1 for r in rows if r.change < 0)
    unchanged = sum(1 for r in rows if r.change == 0)

    top_gainers = sorted(rows, key=lambda r: r.percent_change, reverse=True)[:5]
    top_losers = sorted(rows, key=lambda r: r.percent_change)[:5]
    most_traded = sorted(rows, key=lambda r: r.turnover, reverse=True)[:5]

    total_turnover = sum(r.turnover for r in rows)
    total_volume = sum(r.volume for r in rows)

    now = datetime.now(timezone.utc)
    status, status_label = _market_status(now)
    nepse_level, nepse_change, nepse_pct = _index_snapshot(rows)

    return MarketOverview(
        total_symbols=len(rows),
        total_turnover=total_turnover,
        total_volume=total_volume,
        advancers=advancers,
        decliners=decliners,
        unchanged=unchanged,
        top_gainers=top_gainers,
        top_losers=top_losers,
        most_traded=most_traded,
        updated_at=datetime.utcnow(),
        nepse_index=nepse_level,
        nepse_change=nepse_change,
        nepse_change_percent=nepse_pct,
        market_status=status,
        market_status_label=status_label,
    )
