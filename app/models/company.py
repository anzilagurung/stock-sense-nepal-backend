from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sector: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    security_type: Mapped[str] = mapped_column(String(40), default="Equity")
    status: Mapped[str] = mapped_column(String(20), default="Listed")
    listed_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    website: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    market_prices = relationship("MarketPrice", back_populates="company", cascade="all,delete-orphan")
    reports = relationship("FinancialReport", back_populates="company", cascade="all,delete-orphan")
    dividends = relationship("Dividend", back_populates="company", cascade="all,delete-orphan")
    notices = relationship("CompanyNotice", back_populates="company", cascade="all,delete-orphan")
