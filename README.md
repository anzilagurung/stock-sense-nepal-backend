# NEPSE Investment Analysis Backend

FastAPI + SQLAlchemy backend for the **Stock Sense Nepal** Flutter app.
Serves normalised company/market data plus a rule-based, explainable scoring engine.

**Important:** this is a decision-support tool for research and education. It is not investment advice and does not guarantee any return.

## Layout

```
nepse_backend/
├── app/
│   ├── main.py                 FastAPI entry (auto-seeds on first run)
│   ├── config.py               Environment settings
│   ├── database.py             SQLAlchemy engine + session
│   ├── models/                 SQLAlchemy models (Company, MarketPrice, FinancialReport, ...)
│   ├── schemas/                Pydantic response schemas
│   ├── api/v1/                 REST endpoints (market, companies, search, analysis, admin)
│   ├── analysis/
│   │   ├── engine.py           The scoring engine (transparent, rule-driven)
│   │   └── rules/
│   │       ├── base.py         Rule/Band/Category dataclasses
│   │       └── commercial_bank.py    Commercial Bank methodology v1.0
│   ├── services/               Repository-style services (market, company, analysis)
│   ├── ingestion/
│   │   ├── source.py                 NepseDataSource Protocol + typed DTOs
│   │   ├── nepse_unofficial.py       Community-API implementation (surajrimal07)
│   │   ├── stockmap.py               Bundled full-universe seed loader
│   │   ├── runner.py                 Orchestration + graceful fallback
│   │   └── _reference/stockmap.json  540-company NEPSE universe snapshot
│   └── seed/sample_data.py     Bundled seed: 540-company universe + 5 sample bank financials
├── requirements.txt
├── run.py                      Convenience entry: `python run.py`
└── .env.example
```

## Getting started (local)

Uses SQLite by default so no external DB is needed.

```powershell
# 1. Create a venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install deps
pip install -r requirements.txt

# 3. (optional) copy env template
copy .env.example .env

# 4. Run
python run.py
```

Server starts on **http://127.0.0.1:8000**. Interactive docs at **http://127.0.0.1:8000/docs**.

On first launch the SQLite DB is created and seeded in two passes:

1. **Universe** — 540 NEPSE-listed securities across 14 sectors (Commercial Banks, Hydro, Microfinance, ...) loaded from a bundled snapshot at `app/ingestion/_reference/stockmap.json`. Non-tradeable Promoter Shares are filtered out, leaving ~408 real companies visible in the app.
2. **Sample financials** — illustrative metrics for 5 commercial banks (NABIL, NIMB, EBL, NICA, SCB) so the scoring engine has something to demonstrate immediately. These numbers are placeholders; replace with real data before production.

## Endpoints (v1)

| Method | Path | Purpose |
|-------|------|---------|
| GET | `/api/v1/market/overview` | Market summary, top gainers/losers/most traded |
| GET | `/api/v1/companies` | All companies (optional `?sector=`) |
| GET | `/api/v1/companies/{symbol}` | Company profile |
| GET | `/api/v1/companies/{symbol}/price` | Latest price snapshot |
| GET | `/api/v1/companies/{symbol}/financials` | Full financial history |
| GET | `/api/v1/companies/{symbol}/dividends` | Dividend history |
| GET | `/api/v1/companies/{symbol}/notices` | Announcements |
| GET | `/api/v1/search?q=` | Search companies |
| GET | `/api/v1/companies/{symbol}/analysis?profile=balanced` | Full analysis result |
| GET | `/api/v1/compare?symbols=NABIL,NIMB,EBL&profile=balanced` | Sector comparison |
| POST | `/api/v1/admin/refresh/prices` | Pull latest prices from upstream (fails soft on outage) |
| POST | `/api/v1/admin/refresh/companies` | Re-run stockmap seed (idempotent) |

Valid profiles: `balanced`, `quality`, `growth`, `dividend`, `risk`, `valuation`.

## Ingestion architecture

```
              upstream (unofficial NEPSE community API)
                                │
                                ▼
              ┌────────────────────────────────────┐
              │  NepseUnofficialSource             │  ← app/ingestion/nepse_unofficial.py
              │  (implements NepseDataSource)      │
              └────────────┬───────────────────────┘
                           │  short 8s timeout, always fails soft
                           ▼
              ┌────────────────────────────────────┐
              │  run_ingestion() runner            │  ← app/ingestion/runner.py
              │  gathers prices/gainers/losers,    │
              │  upserts by (company, trading_date)│
              └────────────┬───────────────────────┘
                           ▼
                     PostgreSQL / SQLite
                           ▲
                           │  independently populated
              ┌────────────────────────────────────┐
              │  stockmap.seed_companies()         │  ← runs on first boot
              │  540 real NEPSE securities         │
              │  from bundled snapshot             │
              └────────────────────────────────────┘
```

Key design decisions:

- **Universe is always available.** The bundled stockmap seed runs even when no upstream is reachable, so the app always shows the full company list. Price data is best-effort on top.
- **Fail-soft everywhere.** `/admin/refresh/prices` always returns 200. Downstream failures are captured in the response's `errors[]`, not raised as 5xx. Flutter treats an outage as "keep showing current data."
- **Provider abstraction.** `NepseDataSource` in `app/ingestion/source.py` is a Protocol. Swap providers (an official paid feed later) without touching call sites.

### Upstream data source & licensing

Live prices come from **surajrimal07/NepseAPI-Unofficial** (`https://nepseapi.surajrimal.dev`). Read carefully:

- **Strictly non-commercial** — the upstream project's licence prohibits commercial or production use.
- **No uptime SLA** — the service is community-run and free. Frequent outages (Cloudflare 522 etc.) are normal. That is exactly why our ingestion is fail-soft and why the bundled stockmap seed is not derived from it at request time.
- **For any commercial deployment, replace `NepseUnofficialSource` with an official licensed feed** (Nepal Stock Exchange or an authorised data provider).

## Scoring engine

The engine is **rule-driven and transparent** — no hard-coded scoring per metric.

Flow:

```
raw metrics  →  band lookup (rule)  →  metric score (0–100)
                                    ↓
                    weighted inside category
                                    ↓
                      category score (0–100)
                                    ↓
        weighted by profile → overall + quality + valuation
                                    ↓
        strengths / concerns / conclusion (all with explanations)
```

Each metric response carries: current value, rating band, benchmark, weight, and a plain-language explanation.

To adjust the methodology for Commercial Banks, edit
`app/analysis/rules/commercial_bank.py`. To add a new sector:

1. Create `app/analysis/rules/<sector>.py` with categories + metrics.
2. Register it in `app/analysis/rules/__init__.py::SECTOR_RULES`.
3. Populate seed metrics for companies in that sector.

Bump `methodology_version` when you change scoring rules — historical analyses embed the version used.

## Data note

- The **company universe** (names/symbols/sectors) is real, taken from the bundled `stockmap.json` snapshot.
- The **sample financial metrics** for the 5 demo banks in `app/seed/sample_data.py` are **illustrative** — they exist to make the scoring engine demo-able without a working ingestion pipeline. Replace with real data before any production use.
- **Live prices** flow through the ingestion pipeline described above and land in `market_prices`. When upstream is unreachable, whatever we last cached stays visible.

Future work: a periodic scheduler (APScheduler / cron) that calls `run_ingestion` at market open + every N minutes during trading hours. The manual `/admin/refresh/prices` endpoint is already suitable for a cron pinger.

## Connecting the Flutter client

- Windows/desktop/iOS simulator: uses `http://127.0.0.1:8000` automatically.
- Android emulator: uses `http://10.0.2.2:8000` automatically.
- Physical Android device on your LAN:
  ```
  flutter run --dart-define=API_BASE=http://192.168.x.x:8000
  ```
  and make sure the backend is bound to `0.0.0.0` (it already is, via `run.py`).
