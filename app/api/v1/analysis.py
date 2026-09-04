from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analysis import AnalysisResult, ComparisonResult
from app.services import analysis_service

router = APIRouter(tags=["analysis"])

VALID_PROFILES = {"balanced", "growth", "dividend", "risk", "valuation", "quality"}


def _validate_profile(profile: str) -> str:
    p = profile.lower()
    if p not in VALID_PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown profile '{profile}'. Valid: {sorted(VALID_PROFILES)}")
    return p


@router.get("/companies/{symbol}/analysis", response_model=AnalysisResult)
def get_analysis(
    symbol: str,
    profile: str = Query("balanced"),
    db: Session = Depends(get_db),
) -> AnalysisResult:
    result = analysis_service.analyse_symbol(db, symbol, profile=_validate_profile(profile))
    if not result:
        raise HTTPException(status_code=404, detail=f"Company '{symbol}' not found or has no analysable data")
    return result


@router.get("/compare", response_model=ComparisonResult)
def get_comparison(
    symbols: str = Query(description="Comma-separated symbols, e.g. NABIL,NIMB,EBL"),
    profile: str = Query("balanced"),
    db: Session = Depends(get_db),
) -> ComparisonResult:
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if len(symbol_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least two symbols to compare")
    result = analysis_service.compare_symbols(db, symbol_list, profile=_validate_profile(profile))
    if not result:
        raise HTTPException(status_code=404, detail="Not enough valid companies to compare")
    return result
