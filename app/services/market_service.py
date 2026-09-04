from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, MarketPrice
from app.schemas.market import MarketOverview, MarketRow


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
    )
