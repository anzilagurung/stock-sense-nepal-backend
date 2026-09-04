from sqlalchemy.orm import Session

from app.analysis.engine import MetricSnapshot, analyse, compare
from app.models import Company
from app.services import company_service


def _snapshot_for(db: Session, company: Company) -> MetricSnapshot:
    report = company_service.latest_report(db, company.id)
    price = company_service.latest_price(db, company.id)

    values: dict[str, float] = {}
    if report:
        for m in report.metrics:
            if m.metric_value is not None:
                values[m.metric_key] = m.metric_value

    # Derived valuation metrics from latest price if available.
    if price and price.ltp:
        eps = values.get("eps")
        bvps = values.get("bvps")
        if eps and eps > 0 and "pe" not in values:
            values["pe"] = price.ltp / eps
        if bvps and bvps > 0 and "pb" not in values:
            values["pb"] = price.ltp / bvps

    return MetricSnapshot(
        company_symbol=company.symbol,
        company_name=company.name,
        sector=company.sector,
        values=values,
    )


def analyse_symbol(db: Session, symbol: str, profile: str = "balanced"):
    company = company_service.get_company(db, symbol)
    if not company:
        return None
    snap = _snapshot_for(db, company)
    return analyse(snap, profile=profile)


def compare_symbols(db: Session, symbols: list[str], profile: str = "balanced"):
    companies = [company_service.get_company(db, s) for s in symbols]
    companies = [c for c in companies if c is not None]
    if len(companies) < 2:
        return None
    snapshots = [_snapshot_for(db, c) for c in companies]
    return compare(snapshots, profile=profile)
