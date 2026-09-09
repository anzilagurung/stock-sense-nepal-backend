"""Assemble a rich snapshot (values + history + dividends + peer percentiles)
and hand it to the scoring engine.

Everything below is defensive: if history or dividends aren't ingested for a
company yet, the snapshot still contains enough for the raw score to run — the
verdict engine simply produces a lower-confidence verdict.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.analysis import peers as peers_mod
from app.analysis.derived import DividendRecord, HistoricalMetricPoint
from app.analysis.engine import MetricSnapshot, analyse, compare
from app.models import Company, Dividend, FinancialReport
from app.services import company_service


def _history_from_reports(reports: list[FinancialReport]) -> list[HistoricalMetricPoint]:
    """Flatten every metric across every historical report into a chronological list.

    Ordered oldest → newest so that trajectory computation can read them in
    order without further sorting.
    """
    ordered = sorted(reports, key=lambda r: (r.fiscal_year, r.quarter))
    out: list[HistoricalMetricPoint] = []
    for report in ordered:
        for m in report.metrics:
            if m.metric_value is None:
                continue
            out.append(HistoricalMetricPoint(
                fiscal_year=report.fiscal_year,
                quarter=report.quarter,
                metric_key=m.metric_key,
                value=m.metric_value,
            ))
    return out


def _dividend_records(dividends: list[Dividend]) -> list[DividendRecord]:
    return [
        DividendRecord(
            fiscal_year=d.fiscal_year,
            cash_percent=d.cash_dividend_percent,
            bonus_percent=d.bonus_share_percent,
        )
        for d in dividends
    ]


def _snapshot_for(db: Session, company: Company) -> MetricSnapshot:
    reports = company_service.all_reports(db, company.id)
    price = company_service.latest_price(db, company.id)
    dividends = company_service.dividends(db, company.id)

    values: dict[str, float] = {}
    latest_report = reports[-1] if reports else None
    if latest_report:
        for m in latest_report.metrics:
            if m.metric_value is not None:
                values[m.metric_key] = m.metric_value

    if price and price.ltp:
        eps = values.get("eps")
        bvps = values.get("bvps")
        if eps and eps > 0 and "pe" not in values:
            values["pe"] = price.ltp / eps
        if bvps and bvps > 0 and "pb" not in values:
            values["pb"] = price.ltp / bvps

    history = _history_from_reports(reports)
    div_records = _dividend_records(dividends)
    sector_percentiles = peers_mod.get_sector_percentiles(db, company.sector)

    return MetricSnapshot(
        company_symbol=company.symbol,
        company_name=company.name,
        sector=company.sector,
        values=values,
        history=history,
        dividends=div_records,
        listed_date=company.listed_date,
        sector_percentiles=sector_percentiles,
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
