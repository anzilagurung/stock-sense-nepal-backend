from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.market import MarketOverview
from app.services.market_service import build_overview

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/overview", response_model=MarketOverview)
def market_overview(db: Session = Depends(get_db)) -> MarketOverview:
    return build_overview(db)
