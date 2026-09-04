from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CompanyNotice(Base):
    __tablename__ = "company_notices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notice_type: Mapped[str] = mapped_column(String(60), default="General")
    published_at: Mapped[str] = mapped_column(String(30), index=True)
    source_url: Mapped[str | None] = mapped_column(String(400), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="notices")
