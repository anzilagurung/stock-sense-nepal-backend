from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FinancialReport(Base):
    __tablename__ = "financial_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    fiscal_year: Mapped[str] = mapped_column(String(20), index=True)
    quarter: Mapped[str] = mapped_column(String(10), default="Annual")
    report_type: Mapped[str] = mapped_column(String(20), default="annual")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="reports")
    metrics = relationship("FinancialMetric", back_populates="report", cascade="all,delete-orphan")


class FinancialMetric(Base):
    """Sector-flexible metric row.

    Rather than forcing every possible field (NPL, CAR, PPA, solvency ratio, etc.)
    into one wide table, each metric is stored as a key/value row so any sector can
    add its own fields without a schema change.
    """
    __tablename__ = "financial_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("financial_reports.id", ondelete="CASCADE"), index=True)
    metric_key: Mapped[str] = mapped_column(String(80), index=True)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    report = relationship("FinancialReport", back_populates="metrics")
