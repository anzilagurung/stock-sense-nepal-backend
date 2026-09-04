from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    trading_date: Mapped[str] = mapped_column(String(20), index=True)

    ltp: Mapped[float] = mapped_column(Float, default=0.0)
    previous_close: Mapped[float] = mapped_column(Float, default=0.0)
    change: Mapped[float] = mapped_column(Float, default=0.0)
    percent_change: Mapped[float] = mapped_column(Float, default=0.0)
    day_high: Mapped[float] = mapped_column(Float, default=0.0)
    day_low: Mapped[float] = mapped_column(Float, default=0.0)
    week52_high: Mapped[float] = mapped_column(Float, default=0.0)
    week52_low: Mapped[float] = mapped_column(Float, default=0.0)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    turnover: Mapped[float] = mapped_column(Float, default=0.0)
    trades: Mapped[int] = mapped_column(Integer, default=0)
    market_cap: Mapped[float] = mapped_column(Float, default=0.0)

    source: Mapped[str] = mapped_column(String(40), default="seed")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="market_prices")
