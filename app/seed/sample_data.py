"""First-boot seed.

Two stages:
  1. `seed_universe(db)` inserts every real NEPSE-listed security from the bundled
     `stockmap.json` snapshot (540 companies across 14 sectors). This runs even when
     the upstream data source is unavailable, so the app always has the real company
     list to browse.

  2. `seed_sample_financials(db)` attaches ILLUSTRATIVE financial metrics to a
     handful of commercial banks and hydropower companies so the scoring engine
     has something to demonstrate. These numbers are NOT real reporting-period
     values — they exist to exercise the analysis flow end-to-end. Replace with
     real data before any production use.

Both are idempotent: safe to run repeatedly.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.stockmap import seed_companies as seed_universe  # re-export
from app.models import (
    Company,
    Dividend,
    FinancialMetric,
    FinancialReport,
    MarketPrice,
)


SAMPLE_FINANCIALS: dict[str, dict] = {
    "NABIL": {
        "price": dict(ltp=524.0, previous_close=516.0, change=8.0, percent_change=1.55,
                      day_high=530.0, day_low=515.0, week52_high=780.0, week52_low=470.0,
                      volume=245321, turnover=128_532_000.0, trades=1120, market_cap=252_000_000_000.0),
        "metrics": {
            "eps": 35.42, "bvps": 244.5, "roe": 15.8, "roa": 1.6, "nim": 3.9,
            "net_profit_growth": 12.0, "eps_growth": 9.5,
            "npl": 2.7, "provision_coverage": 115.0, "car": 13.6, "cd_ratio": 84.5,
            "cost_of_fund": 5.4, "base_rate": 7.9,
            "dividend_yield": 5.6, "distributable_profit_per_share": 22.0,
        },
        "dividends": [
            dict(fiscal_year="2079/80", cash_dividend_percent=11.0, bonus_share_percent=5.5),
            dict(fiscal_year="2078/79", cash_dividend_percent=10.0, bonus_share_percent=8.0),
        ],
    },
    "NIMB": {
        "price": dict(ltp=205.0, previous_close=208.0, change=-3.0, percent_change=-1.44,
                      day_high=210.0, day_low=203.0, week52_high=290.0, week52_low=180.0,
                      volume=311000, turnover=63_755_000.0, trades=980, market_cap=138_000_000_000.0),
        "metrics": {
            "eps": 19.8, "bvps": 168.3, "roe": 10.9, "roa": 1.05, "nim": 3.3,
            "net_profit_growth": -3.5, "eps_growth": -6.8,
            "npl": 4.1, "provision_coverage": 92.0, "car": 12.2, "cd_ratio": 86.8,
            "cost_of_fund": 6.4, "base_rate": 8.6,
            "dividend_yield": 4.5, "distributable_profit_per_share": 8.5,
        },
        "dividends": [
            dict(fiscal_year="2079/80", cash_dividend_percent=6.5, bonus_share_percent=2.0),
            dict(fiscal_year="2078/79", cash_dividend_percent=8.0, bonus_share_percent=3.0),
        ],
    },
    "EBL": {
        "price": dict(ltp=635.0, previous_close=628.0, change=7.0, percent_change=1.11,
                      day_high=640.0, day_low=625.0, week52_high=790.0, week52_low=560.0,
                      volume=110450, turnover=70_235_000.0, trades=620, market_cap=118_500_000_000.0),
        "metrics": {
            "eps": 41.2, "bvps": 271.0, "roe": 16.4, "roa": 1.75, "nim": 4.2,
            "net_profit_growth": 15.5, "eps_growth": 12.1,
            "npl": 1.9, "provision_coverage": 128.0, "car": 14.1, "cd_ratio": 82.6,
            "cost_of_fund": 5.1, "base_rate": 7.5,
            "dividend_yield": 6.2, "distributable_profit_per_share": 28.5,
        },
        "dividends": [
            dict(fiscal_year="2079/80", cash_dividend_percent=13.0, bonus_share_percent=6.0),
            dict(fiscal_year="2078/79", cash_dividend_percent=11.0, bonus_share_percent=7.5),
        ],
    },
    "NICA": {
        "price": dict(ltp=395.0, previous_close=402.0, change=-7.0, percent_change=-1.74,
                      day_high=404.0, day_low=390.0, week52_high=560.0, week52_low=355.0,
                      volume=298400, turnover=118_400_000.0, trades=1350, market_cap=175_600_000_000.0),
        "metrics": {
            "eps": 24.6, "bvps": 190.4, "roe": 12.5, "roa": 1.2, "nim": 3.6,
            "net_profit_growth": 6.2, "eps_growth": 3.1,
            "npl": 3.4, "provision_coverage": 101.0, "car": 12.8, "cd_ratio": 88.9,
            "cost_of_fund": 6.1, "base_rate": 8.4,
            "dividend_yield": 3.8, "distributable_profit_per_share": 12.0,
        },
        "dividends": [
            dict(fiscal_year="2079/80", cash_dividend_percent=7.0, bonus_share_percent=4.0),
            dict(fiscal_year="2078/79", cash_dividend_percent=9.0, bonus_share_percent=5.0),
        ],
    },
    "SCB": {
        "price": dict(ltp=488.0, previous_close=484.0, change=4.0, percent_change=0.83,
                      day_high=490.0, day_low=482.0, week52_high=605.0, week52_low=430.0,
                      volume=52000, turnover=25_376_000.0, trades=310, market_cap=95_800_000_000.0),
        "metrics": {
            "eps": 34.8, "bvps": 258.0, "roe": 14.6, "roa": 2.1, "nim": 3.8,
            "net_profit_growth": 8.2, "eps_growth": 5.4,
            "npl": 1.4, "provision_coverage": 135.0, "car": 15.2, "cd_ratio": 76.4,
            "cost_of_fund": 4.2, "base_rate": 6.9,
            "dividend_yield": 4.0, "distributable_profit_per_share": 19.5,
        },
        "dividends": [
            dict(fiscal_year="2079/80", cash_dividend_percent=15.0, bonus_share_percent=0.0),
            dict(fiscal_year="2078/79", cash_dividend_percent=13.5, bonus_share_percent=0.0),
        ],
    },
}


SAMPLE_FINANCIALS.update({
    "UPPER": {
        "price": dict(ltp=98.0, previous_close=97.5, change=0.5, percent_change=0.51,
                      day_high=99.0, day_low=97.0, week52_high=140.0, week52_low=85.0,
                      volume=520000, turnover=50_960_000.0, trades=1420, market_cap=105_000_000_000.0),
        "metrics": {
            "eps": 5.6, "bvps": 71.0,
            "roe": 8.2, "roa": 3.1, "net_profit_margin": 34.0,
            "net_profit_growth": 6.5, "eps_growth": 4.8,
            "debt_to_equity": 2.4, "interest_coverage": 2.9,
            "plant_load_factor": 48.0,
            "dividend_yield": 4.5, "payout_ratio": 55.0,
        },
        "dividends": [
            dict(fiscal_year="2079/80", cash_dividend_percent=4.2, bonus_share_percent=0.2),
        ],
    },
    "CHCL": {
        "price": dict(ltp=520.0, previous_close=515.0, change=5.0, percent_change=0.97,
                      day_high=525.0, day_low=512.0, week52_high=690.0, week52_low=470.0,
                      volume=42000, turnover=21_840_000.0, trades=310, market_cap=44_500_000_000.0),
        "metrics": {
            "eps": 36.4, "bvps": 220.0,
            "roe": 18.5, "roa": 9.8, "net_profit_margin": 52.0,
            "net_profit_growth": 14.0, "eps_growth": 11.5,
            "debt_to_equity": 0.6, "interest_coverage": 8.5,
            "plant_load_factor": 62.0,
            "dividend_yield": 6.8, "payout_ratio": 70.0,
        },
        "dividends": [
            dict(fiscal_year="2079/80", cash_dividend_percent=25.0, bonus_share_percent=2.0),
            dict(fiscal_year="2078/79", cash_dividend_percent=22.0, bonus_share_percent=3.0),
        ],
    },
    "API": {
        "price": dict(ltp=185.0, previous_close=188.0, change=-3.0, percent_change=-1.60,
                      day_high=190.0, day_low=183.0, week52_high=260.0, week52_low=160.0,
                      volume=180000, turnover=33_300_000.0, trades=610, market_cap=14_800_000_000.0),
        "metrics": {
            "eps": 8.9, "bvps": 118.0,
            "roe": 11.2, "roa": 4.6, "net_profit_margin": 28.0,
            "net_profit_growth": 3.5, "eps_growth": 1.8,
            "debt_to_equity": 1.7, "interest_coverage": 3.4,
            "plant_load_factor": 46.0,
            "dividend_yield": 3.2, "payout_ratio": 35.0,
        },
        "dividends": [
            dict(fiscal_year="2079/80", cash_dividend_percent=3.0, bonus_share_percent=0.5),
        ],
    },
    "AHPC": {
        "price": dict(ltp=310.0, previous_close=308.0, change=2.0, percent_change=0.65,
                      day_high=314.0, day_low=306.0, week52_high=420.0, week52_low=270.0,
                      volume=64000, turnover=19_840_000.0, trades=380, market_cap=8_900_000_000.0),
        "metrics": {
            "eps": 18.5, "bvps": 152.0,
            "roe": 14.2, "roa": 6.8, "net_profit_margin": 41.0,
            "net_profit_growth": 9.5, "eps_growth": 7.0,
            "debt_to_equity": 1.1, "interest_coverage": 5.6,
            "plant_load_factor": 54.0,
            "dividend_yield": 5.4, "payout_ratio": 50.0,
        },
        "dividends": [
            dict(fiscal_year="2079/80", cash_dividend_percent=9.0, bonus_share_percent=1.0),
            dict(fiscal_year="2078/79", cash_dividend_percent=8.5, bonus_share_percent=1.5),
        ],
    },
    "AHL": {
        "price": dict(ltp=245.0, previous_close=248.0, change=-3.0, percent_change=-1.21,
                      day_high=250.0, day_low=242.0, week52_high=330.0, week52_low=210.0,
                      volume=41000, turnover=10_045_000.0, trades=220, market_cap=3_800_000_000.0),
        "metrics": {
            "eps": 9.2, "bvps": 122.0,
            "roe": 7.5, "roa": 2.6, "net_profit_margin": 24.0,
            "net_profit_growth": -4.0, "eps_growth": -6.5,
            "debt_to_equity": 2.8, "interest_coverage": 1.9,
            "plant_load_factor": 38.0,
            "dividend_yield": 1.8, "payout_ratio": 18.0,
        },
        "dividends": [
            dict(fiscal_year="2079/80", cash_dividend_percent=1.5, bonus_share_percent=0.0),
        ],
    },
})


def _unit_for(key: str) -> str:
    if key in {"eps", "bvps", "distributable_profit_per_share"}:
        return "Rs"
    if key in {"pe", "pb", "debt_to_equity", "interest_coverage"}:
        return "x"
    return "%"


def seed_sample_financials(db: Session) -> dict[str, int]:
    """Attach illustrative financials to the sample companies. Idempotent.

    Idempotency: skip a company if it already has any financial_report row.
    """
    attached = 0
    for symbol, payload in SAMPLE_FINANCIALS.items():
        company = db.scalar(select(Company).where(Company.symbol == symbol))
        if not company:
            continue  # not in stockmap for some reason — skip silently
        existing = db.scalar(
            select(FinancialReport).where(FinancialReport.company_id == company.id).limit(1)
        )
        if existing:
            continue

        db.add(MarketPrice(
            company_id=company.id,
            trading_date=datetime.utcnow().strftime("%Y-%m-%d"),
            source="sample",
            **payload["price"],
        ))

        report = FinancialReport(
            company_id=company.id,
            fiscal_year="2079/80",
            quarter="Annual",
            report_type="annual",
        )
        db.add(report)
        db.flush()
        for key, value in payload["metrics"].items():
            db.add(FinancialMetric(
                report_id=report.id,
                metric_key=key,
                metric_value=float(value),
                unit=_unit_for(key),
            ))
        for d in payload["dividends"]:
            db.add(Dividend(
                company_id=company.id,
                status="Announced",
                announcement_date="2024-09-01",
                book_closure_date="2024-10-15",
                agm_date="2024-11-30",
                **d,
            ))
        attached += 1

    db.commit()
    return {"sample_companies_attached": attached}


# Backwards-compat name used by main.py before this refactor.
def seed_if_empty(db: Session) -> None:
    seed_universe(db)
    seed_sample_financials(db)
