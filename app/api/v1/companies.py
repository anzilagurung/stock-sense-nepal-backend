from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.company import CompanyDetail, CompanySummary
from app.schemas.financials import DividendOut, FinancialReportOut, NoticeOut
from app.schemas.market import PriceSnapshot
from app.services import company_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanySummary])
def list_all(sector: str | None = None, db: Session = Depends(get_db)) -> list[CompanySummary]:
    return [CompanySummary.model_validate(c) for c in company_service.list_companies(db, sector)]


def _company_or_404(db: Session, symbol: str):
    c = company_service.get_company(db, symbol)
    if not c:
        raise HTTPException(status_code=404, detail=f"Company '{symbol}' not found")
    return c


@router.get("/{symbol}", response_model=CompanyDetail)
def get_one(symbol: str, db: Session = Depends(get_db)) -> CompanyDetail:
    return CompanyDetail.model_validate(_company_or_404(db, symbol))


@router.get("/{symbol}/price", response_model=PriceSnapshot)
def get_price(symbol: str, db: Session = Depends(get_db)) -> PriceSnapshot:
    company = _company_or_404(db, symbol)
    price = company_service.latest_price(db, company.id)
    if not price:
        raise HTTPException(status_code=404, detail=f"No price data for '{symbol}'")
    return PriceSnapshot.model_validate(price)


@router.get("/{symbol}/financials", response_model=list[FinancialReportOut])
def get_financials(symbol: str, db: Session = Depends(get_db)) -> list[FinancialReportOut]:
    company = _company_or_404(db, symbol)
    reports = company_service.all_reports(db, company.id)
    return [FinancialReportOut.model_validate(r) for r in reports]


@router.get("/{symbol}/dividends", response_model=list[DividendOut])
def get_dividends(symbol: str, db: Session = Depends(get_db)) -> list[DividendOut]:
    company = _company_or_404(db, symbol)
    return [DividendOut.model_validate(d) for d in company_service.dividends(db, company.id)]


@router.get("/{symbol}/notices", response_model=list[NoticeOut])
def get_notices(symbol: str, db: Session = Depends(get_db)) -> list[NoticeOut]:
    company = _company_or_404(db, symbol)
    return [NoticeOut.model_validate(n) for n in company_service.notices(db, company.id)]
