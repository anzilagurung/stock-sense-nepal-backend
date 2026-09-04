from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Company,
    CompanyNotice,
    Dividend,
    FinancialReport,
    MarketPrice,
)


def list_companies(db: Session, sector: str | None = None) -> list[Company]:
    stmt = select(Company).order_by(Company.symbol)
    if sector:
        stmt = stmt.where(Company.sector == sector)
    return list(db.scalars(stmt))


def get_company(db: Session, symbol: str) -> Company | None:
    return db.scalar(select(Company).where(Company.symbol == symbol.upper()))


def latest_price(db: Session, company_id: int) -> MarketPrice | None:
    return db.scalar(
        select(MarketPrice)
        .where(MarketPrice.company_id == company_id)
        .order_by(MarketPrice.trading_date.desc(), MarketPrice.id.desc())
    )


def latest_report(db: Session, company_id: int) -> FinancialReport | None:
    return db.scalar(
        select(FinancialReport)
        .where(FinancialReport.company_id == company_id)
        .options(selectinload(FinancialReport.metrics))
        .order_by(FinancialReport.fiscal_year.desc(), FinancialReport.id.desc())
    )


def all_reports(db: Session, company_id: int) -> list[FinancialReport]:
    return list(db.scalars(
        select(FinancialReport)
        .where(FinancialReport.company_id == company_id)
        .options(selectinload(FinancialReport.metrics))
        .order_by(FinancialReport.fiscal_year.asc())
    ))


def dividends(db: Session, company_id: int) -> list[Dividend]:
    return list(db.scalars(
        select(Dividend)
        .where(Dividend.company_id == company_id)
        .order_by(Dividend.fiscal_year.desc())
    ))


def notices(db: Session, company_id: int, limit: int = 20) -> list[CompanyNotice]:
    return list(db.scalars(
        select(CompanyNotice)
        .where(CompanyNotice.company_id == company_id)
        .order_by(CompanyNotice.published_at.desc())
        .limit(limit)
    ))


def search_companies(db: Session, q: str) -> list[Company]:
    q_norm = f"%{q.strip().upper()}%"
    return list(db.scalars(
        select(Company).where(
            (Company.symbol.ilike(q_norm)) | (Company.name.ilike(q_norm))
        ).order_by(Company.symbol)
    ))
