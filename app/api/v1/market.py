from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.market import MarketOverview
from app.schemas.top_picks import TopPicksResponse
from app.services.market_service import build_overview
from app.services.top_picks_service import build_top_picks

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/overview", response_model=MarketOverview)
def market_overview(db: Session = Depends(get_db)) -> MarketOverview:
    return build_overview(db)


@router.get("/top-picks", response_model=TopPicksResponse)
def market_top_picks(
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
) -> TopPicksResponse:
    return build_top_picks(db, limit=limit)
