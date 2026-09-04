from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Dividend(Base):
    __tablename__ = "dividends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    fiscal_year: Mapped[str] = mapped_column(String(20), index=True)
    cash_dividend_percent: Mapped[float] = mapped_column(Float, default=0.0)
    bonus_share_percent: Mapped[float] = mapped_column(Float, default=0.0)
    right_share_percent: Mapped[float] = mapped_column(Float, default=0.0)
    announcement_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    book_closure_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    agm_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Announced")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="dividends")
