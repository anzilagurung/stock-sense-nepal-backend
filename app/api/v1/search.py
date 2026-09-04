from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.company import CompanySummary
from app.services import company_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[CompanySummary])
def search(q: str = Query(min_length=1), db: Session = Depends(get_db)) -> list[CompanySummary]:
    return [CompanySummary.model_validate(c) for c in company_service.search_companies(db, q)]
