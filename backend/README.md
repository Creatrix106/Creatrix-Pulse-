# Creatrix Pulse – Backend API & Analytics Engine

A production-grade, fully typed, asynchronous backend architecture built with **Python 3.11+**, **FastAPI**, **SQLite + Parquet storage**, and **Pandas** (PostgreSQL models/migrations are included as scaffolding, see section 5) for the **Creatrix Pulse** frontend application.

---

## 1. Architecture & Tech Stack

```
                          ┌───────────────────────────┐
                          │  Next.js Frontend (React) │
                          │   http://localhost:3000   │
                          └─────────────┬─────────────┘
                                        │ HTTP / REST (JWT & Cookies)
                                        ▼
                   ┌─────────────────────────────────────────┐
                   │        FastAPI Asynchronous API         │
                   │  - CORS Middleware                      │
                   │  - OAuth2 Bearer & Session Cookies      │
                   │  - Global Exception Handlers            │
                   │  - Multi-Prefix Routing (/v1, /api, /)  │
                   └─────┬──────────────┬──────────────┬─────┘
                         │              │              │
        ┌────────────────▼───┐   ┌──────▼──────┐   ┌───▼──────────────────┐
        │ PostgreSQL 15+ DB  │   │   Parquet   │   │  ReportLab & Export  │
        │ - SQLAlchemy 2.0   │   │  Columnar   │   │  - PDF compilation   │
        │ - Alembic Migr.    │   │   Engine    │   │  - Excel (openpyxl)  │
        │ - B-Tree & JSONB   │   │  (Pandas)   │   │  - CSV / JSON stream │
        └────────────────────┘   └─────────────┘   └──────────────────────┘
```

- **Framework**: FastAPI (Python 3.11+) with asynchronous routing (`async def`).
- **Database**: SQLite (`data/creatrix_pulse.db`) for records and Parquet files (`data/parquet/`) for analytics. The SQLAlchemy models, `schema.sql` and Alembic migrations describe a future PostgreSQL layout but are **not used by the running API yet**; a `postgresql://` `DATABASE_URL` logs a warning and SQLite is used anyway.
- **Analytics & Aggregations**: Vectorized in-memory aggregation engine with Pandas and Parquet storage for sub-millisecond querying over time-series, categories, and customer cohorts.
- **Authentication & Security**:
  - OAuth2 Password Bearer flow with JWT access and refresh tokens.
  - Password hashing with PBKDF2-HMAC-SHA256 (100k rounds).
  - Role-Based Access Control (RBAC: `admin`, `analyst`, `viewer`).
  - Automatic `httpOnly` session cookies supporting `credentials: "include"`.
  - Explicit-origin CORS for Next.js (`http://localhost:3000`, any localhost port in development). `*` is never valid here because the frontend sends cookies.
- **Background jobs**: not implemented yet (Celery/Redis are listed in requirements and docker-compose only as scaffolding). Uploads are processed synchronously, in a worker thread so other requests are not blocked.

---

## 2. Directory Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py               # Auth dependencies, token decoding, and RBAC
│   │   └── v1/
│   │       ├── auth.py           # Register, login, me, refresh, logout
│   │       ├── datasets.py       # Upload, preview, list, status, delete, map
│   │       ├── analytics.py      # Overview, sales, products, customers, finance, explorer
│   │       ├── insights.py       # Heuristic and statistical anomaly detection
│   │       └── reports.py        # Preview, generate, and stream download reports
│   ├── config.py                 # App settings (Pydantic BaseSettings)
│   ├── core/
│   │   ├── exceptions.py         # Custom application exceptions and handlers
│   │   ├── response.py           # Standard response envelope formatter
│   │   └── security.py           # JWT signing/decoding and PBKDF2 password hashing
│   ├── db/
│   │   ├── database.py           # Asynchronous database repository layer
│   │   ├── schema.sql            # PostgreSQL 15+ DDL schema with B-Tree indexes and JSONB
│   │   └── seed.py               # Deterministic demo dataset seeder
│   ├── models/
│   │   └── entities.py           # SQLAlchemy 2.0 declarative database models
│   ├── schemas/
│   │   ├── analytics.py          # KPIs, time series, breakdowns, explorer schemas
│   │   ├── auth.py               # Login, register, token, user profile schemas
│   │   ├── dataset.py            # Dataset, processing stages, profiling schemas
│   │   ├── filters.py            # Global analytics filters
│   │   ├── insight.py            # Automated insight and evidence schemas
│   │   └── report.py             # Report configuration, preview, and record schemas
│   ├── services/
│   │   ├── analytics_service.py  # Vectorized Pandas analytics engine
│   │   ├── dataset_service.py    # CSV/XLSX ingestion, profiling, and mapping
│   │   ├── insights_service.py   # Statistical anomaly & Z-score detection
│   │   └── report_service.py     # Multi-format report builder (PDF, Excel, CSV, JSON)
│   └── main.py                   # FastAPI application factory and router mounting
├── alembic/                      # Alembic schema migrations
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── alembic.ini                   # Alembic configuration
├── docker-compose.yml            # PostgreSQL 15, Redis, FastAPI, and Celery worker
├── Dockerfile                    # Container build file
├── requirements.txt              # Production Python dependencies
├── run_tests.py                  # Standalone automated test runner
└── run.sh                        # Service startup script
```

---

## 3. Domain Endpoints & Frontend API Mapping

### Authentication (`/auth` & `/api/v1/auth`)
| Method | Endpoint | Description | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/auth/register` | Register new user | `{ name, email, password, role? }` | `User` profile + JWT tokens |
| `POST` | `/auth/login` | Login user (never creates accounts) | `{ email, password }` (JSON) | `User` profile + JWT tokens + session cookie |
| `POST` | `/auth/token` | OAuth2 form login for Swagger's *Authorize* button | form: `username`, `password` | same as login |
| `GET` | `/auth/me` | Authenticated user info | Header / Cookie | `User` |
| `POST` | `/auth/refresh` | Rotate access token | `{ refresh_token }` | `{ access_token, refresh_token }` |
| `POST` | `/auth/logout` | Revoke session | Header / Cookie | `204 No Content` |

### Datasets (`/datasets` & `/api/v1/datasets`)
| Method | Endpoint | Description | Query / Body | Response |
|---|---|---|---|---|
| `GET` | `/datasets` | List all datasets | `envelope=false` | `Dataset[]` |
| `POST` | `/datasets` | Multipart file upload | `file`, `mapping?`, `replaceDatasetId?` | `{ datasetId }` |
| `GET` | `/datasets/{id}` | Dataset detail | None | `Dataset` (404 when missing) |
| `DELETE` | `/datasets/{id}` | Purge dataset & records | None | `204 No Content` |
| `GET` | `/datasets/{id}/processing` | Processing progress | None | `ProcessingStatus` |
| `GET` | `/datasets/{id}/preview` | Column profiling & sample | None | `DatasetProfile` |
| `POST` | `/datasets/{id}/map-columns`| Map canonical columns | `{ [canonical]: srcColumn }` | Success response |

### Analytics Engine (`/datasets/{id}/analytics` & `/api/v1/datasets/{id}/analytics`)
All endpoints accept global query filters: `datePreset`, `dateFrom`, `dateTo`, `comparison`, `groupBy`, `categories`, `regions`.

- `GET /overview` → `OverviewData`: High-level KPIs, revenue trend, top 5 products, category breakdown, regional breakdown, and automated insights.
- `GET /sales` → `SalesData`: Core sales KPIs, current trend, comparison trend, category distribution, and category time series.
- `GET /products` → `ProductsData`: Top 5 products, lowest 5 products, full product catalog performance, and category metrics.
- `GET /customers` → `Capability<CustomersData>`: Total customers, new vs. returning, purchase frequency bins, and RFM customer segments (`Champions`, `Loyal`, `Returning`, `One-time`). Returns `{ "available": false, "reason": "..." }` when customer identifiers are missing.
- `GET /finance` → `Capability<FinanceData>`: Revenue, total cost, gross profit, profit margin %, financial trend, and category margins. Returns `{ "available": false, "reason": "..." }` when cost data is missing.
- `GET /insights` → `Insight[]`: Automated statistical insights and anomaly detection.
- `GET /records` (or `/explorer`) → `ExplorerData`: Dynamic columnar data explorer with server-side pagination (`limit`, `offset`) and sorting (`sortBy`).

### Reports & Exports (`/datasets/{id}/reports` & `/api/v1/datasets/{id}/reports`)
- `POST /preview` → `ReportPreview`: Summary cards, month-by-month table preview, and period bounds.
- `GET /` → `ReportRecord[]`: Download history of generated reports.
- `POST /` (or `/generate`) → `ReportRecord`: Asynchronously compiles reports in **PDF**, **Excel (.xlsx)**, **CSV**, or **JSON**.
- `GET /{reportId}/download` → Binary stream download of the compiled artifact.

---

## 4. Multi-Prefix Routing

To provide seamless compatibility with any frontend configuration, all routes are mounted across three prefixes:
1. `/api/v1/...` (Production versioned API)
2. `/api/...` (Default Next.js `NEXT_PUBLIC_API_BASE_URL="/api"`)
3. `/...` (Direct root mounting for `NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"`)

---

## 5. Quickstart & Execution

### Run Locally
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed demo datasets (demo-retail, demo-marketplace, demo-wholesale, demo-failed)
python -m app.db.seed

# 3. Start API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI documentation is available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Run with Docker Compose (API only; data persisted in `./data`)
```bash
SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" docker compose up -d --build
# optional PostgreSQL/Redis scaffolding (not used by the API yet): docker compose --profile postgres up
```

### Run Automated Tests
```bash
python run_tests.py
```
The suite covers authentication, dataset upload, CSV parsing, vectorized analytics, capability gates, automated insights and multi-format reports, plus `tests/test_regressions.py` (CORS, cookies, upload validation, explorer, reports). Run only the regressions with `pytest tests/test_regressions.py`.

---

## 6. Connecting the Next.js frontend

The frontend uses **mock data unless told otherwise**. Create `my-app/.env.local`:

```env
NEXT_PUBLIC_USE_MOCKS=false
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Restart `npm run dev` afterwards (`NEXT_PUBLIC_*` values are read at start-up). Then:

- Open the app at **`http://localhost:3000`** and keep the API at **`http://localhost:8000`**. Use `localhost` for *both*: the session cookie is `SameSite=Lax`, so mixing `localhost` and `127.0.0.1` makes the browser drop it.
- Sign in with the seeded demo account `admin@creatrix.io` / `password123`, or register a new account.
- Uploads: the browser sends the confirmed column mapping for CSV files; Excel files are mapped server-side from their headers. Files that cannot be interpreted are rejected with a `422` and a message instead of producing a dataset with invented values.

## 7. Configuration (environment variables or `.env`)

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | built-in dev key | JWT signing key. **Set a long random value in production.** |
| `ALLOW_ANONYMOUS_DEMO` | `true` | Requests without a session are served as the demo admin (the frontend has no login guard yet). **Set `false` before deploying**, after adding a login redirect to the frontend. |
| `AUTO_CREATE_USER_ON_LOGIN` | `false` | Legacy convenience: create an account when an unknown e-mail logs in. Leave off. |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated or JSON list. Never `*`. |
| `CORS_ORIGIN_REGEX` | any `localhost` / `127.0.0.1` port | Extra origin pattern; set empty to disable. |
| `COOKIE_SECURE` / `COOKIE_SAMESITE` | `false` / `lax` | Use `true` / `none` (HTTPS only) when frontend and API are on different sites. |
| `MAX_FILE_SIZE_MB` | `50` | Upload size limit (the UI itself limits to 25 MB). |
| `MAX_EXPLORER_ROWS` | `50000` | Upper bound for `/records`. |
| `MAX_BAD_DATE_SHARE` | `0.05` | Share of unreadable dates tolerated (those rows are dropped) before an upload is rejected. |
| `DATE_DAYFIRST_DEFAULT` | `true` | Reading of ambiguous dates such as `05/03/2026` (day-first). Unambiguous values in the file always win. |
| `DEBUG` | `false` | Include exception text in 500 responses. |

Demo datasets are created on the first run only; run `python -m app.db.seed --force` to restore deleted ones.
