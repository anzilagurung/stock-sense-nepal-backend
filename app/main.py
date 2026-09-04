from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.seed.sample_data import seed_sample_financials, seed_universe


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        # Both seeds are idempotent, so we run them every boot. `seed_universe`
        # upserts every entry in the bundled stockmap — existing rows get their
        # name/sector refreshed, new NEPSE listings are inserted. `seed_sample_financials`
        # skips any bank that already has a financial_report.
        seed_universe(db)
        seed_sample_financials(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "REST API for a NEPSE fundamental investment-analysis application. "
        "Serves normalised company/market data plus a rule-based, explainable scoring engine. "
        "This is an analysis/decision-support tool — not investment advice."
    ),
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["meta"])
def root():
    return {
        "app": settings.app_name,
        "env": settings.app_env,
        "methodology_version": settings.methodology_version,
        "docs": "/docs",
    }


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
