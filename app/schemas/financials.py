from pydantic import BaseModel

from app.schemas.common import OrmModel


class FinancialMetricOut(OrmModel):
    metric_key: str
    metric_value: float | None
    unit: str | None = None


class FinancialReportOut(OrmModel):
    id: int
    fiscal_year: str
    quarter: str
    report_type: str
    metrics: list[FinancialMetricOut]


class DividendOut(OrmModel):
    fiscal_year: str
    cash_dividend_percent: float
    bonus_share_percent: float
    right_share_percent: float
    announcement_date: str | None = None
    book_closure_date: str | None = None
    agm_date: str | None = None
    status: str


class NoticeOut(OrmModel):
    id: int
    title: str
    description: str | None
    notice_type: str
    published_at: str
    source_url: str | None


class MetricTrendPoint(BaseModel):
    label: str
    value: float | None
