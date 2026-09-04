from datetime import datetime

from app.schemas.common import OrmModel


class CompanyBase(OrmModel):
    symbol: str
    name: str
    sector: str
    security_type: str = "Equity"
    status: str = "Listed"


class CompanySummary(CompanyBase):
    id: int
    listed_date: str | None = None


class CompanyDetail(CompanyBase):
    id: int
    listed_date: str | None = None
    website: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime
