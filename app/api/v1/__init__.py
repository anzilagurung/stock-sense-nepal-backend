from fastapi import APIRouter

from app.api.v1 import admin, analysis, companies, market, search

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(market.router)
api_router.include_router(companies.router)
api_router.include_router(search.router)
api_router.include_router(analysis.router)
api_router.include_router(admin.router)
