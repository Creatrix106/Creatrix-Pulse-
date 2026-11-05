<<<<<<< HEAD
# Creatrix Pulse – Backend API & Analytics Engine

A production-grade, fully typed, asynchronous backend architecture built with **Python 3.11+**, **FastAPI**, **PostgreSQL 15+**, **SQLAlchemy 2.0 (asyncpg)**, and **Pandas/Parquet** for the **Creatrix Pulse** frontend application.

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
- **Database**: PostgreSQL 15+ with SQLAlchemy 2.0 (`asyncpg` driver) and Alembic migrations. Includes zero-dependency embedded database support for development/sandboxes.
- **Analytics & Aggregations**: Vectorized in-memory aggregation engine with Pandas and Parquet storage for sub-millisecond querying over time-series, categories, and customer cohorts.
- **Authentication & Security**:
  - OAuth2 Password Bearer flow with JWT access and refresh tokens.
  - Password hashing with PBKDF2-HMAC-SHA256 (100k rounds) / bcrypt.
  - Role-Based Access Control (RBAC: `admin`, `analyst`, `viewer`).
  - Automatic `httpOnly` session cookies supporting `credentials: "include"`.
  - Configured CORS for Next.js (`http://localhost:3000`).
- **Task Queue / Background Jobs**: Celery with Redis for asynchronous file ingestion, schema validation, and PDF report compilation.

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
=======
# Creatrix Pulse

Creatrix Pulse is a high-throughput, enterprise-grade data intelligence and analytics engine. It combines a **Next.js 14+** frontend with an asynchronous **FastAPI** backend, backed by **PostgreSQL 15+** and **Apache Parquet / Pandas** for in-memory vectorized calculations.

---

## Executive Overview

Creatrix Pulse eliminates the performance overhead of running ad-hoc analytical queries on relational databases. Instead of scanning standard tables on every query, it ingests multi-format datasets, profiles and validates schemas, and generates compressed Parquet caches for sub-millisecond aggregations over time-series data, category breakdowns, customer cohorts, and financial margins.

### Key Capabilities

* **Vectorized In-Memory Analytics**: Delivers sub-millisecond query responses across revenue curves, volume trends, average order values, and gross margins using Apache Parquet and Pandas.
* **Strict Capability Gating**: Prevents hallucinated data. If a dataset lacks cost or customer attributes, downstream endpoints cleanly report capability denials (`{ "available": false, "reason": "..." }`) rather than fabricating metrics.
* **Automated Statistical Intelligence**: Integrated Z-score heuristic engine flagging statistical revenue anomalies ($\ge 1.8\sigma$), inventory revenue concentration risks, and product movers.
* **Universal Multi-Prefix Gateway**: Routes are concurrently mounted across `/api/v1`, `/api`, and `/` for out-of-the-box compatibility with any frontend environment configuration.
* **Multi-Format Export Pipelines**: Native compilation of executive PDF briefs (ReportLab), formatted Excel workbooks (OpenPyXL), CSVs, and JSON streams.

---

## System Architecture

```
                     ┌──────────────────────────────────────────┐
                     │          Next.js 14+ Frontend            │
                     │  TanStack Query v5 • Zustand • Recharts  │
                     └─────────────────────┬────────────────────┘
                                           │ HTTPS (Bearer JWT / httpOnly Cookies)
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                FastAPI Gateway Layer                                   │
│    ├── CORS Policy Engine (localhost:3000 / Production Origin)                         │
│    ├── OAuth2 Bearer Interceptor & Session Cookie Extraction                           │
│    ├── Standardized Envelope Formatter (success, data, error, meta)                    │
│    └── Global RFC-7807 Compliant Exception Handlers                                    │
└──────────────┬───────────────────────────┬───────────────────────────┬─────────────────┘
               │                           │                           │
               ▼                           ▼                           ▼
┌──────────────────────────────┐ ┌───────────────────────────┐ ┌──────────────────────────┐
│   PostgreSQL 15+ Relational  │ │ Vectorized Columnar Core  │ │ Document Compiler Engine │
│ ├── SQLAlchemy 2.0 (asyncpg) │ │ ├── Apache Parquet Engine │ │ ├── ReportLab PDF Deck   │
│ ├── Alembic Schema Control   │ │ ├── Pandas Vector Math    │ │ ├── OpenPyXL Workbooks   │
│ ├── Users & Workspace RBAC   │ │ ├── RFM Customer Cohorts  │ │ └── Async Stream Writer  │
│ └── B-Tree Indexed DDL       │ │ └── Z-Score Anomaly Scans │ │                          │
└──────────────────────────────┘ └───────────────────────────┘ └──────────────────────────┘

>>>>>>> 77fdf673ccff46dbf311add372661aef44a0e538
```

---

<<<<<<< HEAD
## 3. Domain Endpoints & Frontend API Mapping

### Authentication (`/auth` & `/api/v1/auth`)
| Method | Endpoint | Description | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/auth/register` | Register new user | `{ name, email, password, role? }` | `User` profile + JWT tokens |
| `POST` | `/auth/login` | Login user | `{ email, password }` or form data | `User` profile + JWT tokens + session cookie |
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

### Run with Docker Compose (PostgreSQL 15 + Redis + Celery + API)
```bash
docker compose up -d --build
```

### Run Automated Tests
```bash
python run_tests.py
```
Test suite executes 26 comprehensive automated test cases covering authentication, dataset upload, CSV parsing, vectorized analytics, capability gates, automated insights, and multi-format report streaming.
=======
## Tech Stack

| Layer | Technologies |
| --- | --- |
| **Frontend** | Next.js 14+ (App Router), React, TypeScript, TanStack Query v5, Zustand, Recharts, Tailwind CSS |
| **Backend API** | FastAPI (Python 3.11+), Uvicorn (ASGI) |
| **Data Validation** | Pydantic v2 (Strict contract alignment with frontend schemas) |
| **Relational Database** | PostgreSQL 15+, SQLAlchemy 2.0 (`asyncpg`), Alembic |
| **Analytics Core** | Pandas, Apache Parquet (PyArrow, FastParquet), NumPy |
| **Reporting & Exports** | ReportLab (PDF), OpenPyXL (Excel), CSV, JSON |
| **Security & Auth** | OAuth2 Password Bearer, JWT (HS256), PBKDF2-HMAC-SHA256 (100k rounds) |
| **Orchestration** | Docker Compose v2, Redis 7, Celery |

---

## Core Modules

### 1. Vectorized Analytics Engine

* **Core Metrics**: Real-time calculations of Total Revenue, Orders, Units Sold, Average Order Value (AOV), Gross Profit, and Margin %.
* **Sliding Comparisons**: Period-over-period percentage variance calculations against prior sliding windows of identical length.
* **Granular Groupings**: Multi-dimensional slicing grouped by `day`, `week`, or `month`, with category and regional filtering.

### 2. Statistical Insights & Anomaly Detection

* **Weekly Volatility Detection**: Evaluates transaction volume standard deviations to flag operational outages, unexpected demand spikes, or data collection discrepancies.
* **Concentration Risk Scoring**: Alerts leadership teams when the top 3 SKUs exceed 40% of overall sales volume.
* **Catalog Movers**: Real-time identification of top-performing growth drivers and fastest-declining inventory items.

### 3. Customer Intelligence & Retention Cohorts

* **RFM Segmentation**: Rule-based cohort classification:
* `Champions`: 6+ completed orders
* `Loyal`: 3–5 completed orders
* `Returning`: 2 completed orders
* `One-time`: 1 completed order


* **New vs. Returning Dynamics**: Tracks historical acquisition velocity against repeat retention metrics across discrete time intervals.

### 4. Enterprise File Ingestion & Profiling

* **Heuristic Schema Inference**: Automatically detects dates (ISO-8601, slash, and dash formats), numbers, integers, and boolean values.
* **Automated Column Mapping**: Suggests canonical mapping aliases (`orderId`, `date`, `product`, `category`, `revenue`, `cost`, `quantity`, `customer`, `region`).
* **Processing Stage Pipeline**: Tracks progress across 5 distinct lifecycle stages: `upload` $\to$ `validate` $\to$ `process` $\to$ `analytics` $\to$ `prepare`.

---

## API Specification

All endpoints support optional response envelope wrapping (`?envelope=true`):

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": { "total": 120, "page": 1, "limit": 20 }
}

```

### Authentication (`/api/v1/auth`)

| Method | Endpoint | Description | Payload | Response |
| --- | --- | --- | --- | --- |
| `POST` | `/auth/register` | Register new user | `{ name, email, password, role? }` | `User` profile + JWT tokens |
| `POST` | `/auth/login` | Login user | `{ email, password }` or Form | `User` profile + tokens + session cookie |
| `GET` | `/auth/me` | Current session | Bearer Token / Cookie | `User` object |
| `POST` | `/auth/refresh` | Rotate access token | `{ refresh_token }` | `{ access_token, refresh_token }` |
| `POST` | `/auth/logout` | Revoke session | None | `204 No Content` |

### Datasets & Ingestion (`/api/v1/datasets`)

| Method | Endpoint | Description | Query / Body | Response |
| --- | --- | --- | --- | --- |
| `GET` | `/datasets` | List all datasets | `envelope=false` | `Dataset[]` |
| `POST` | `/datasets` | Multipart file upload | `file`, `mapping?` | `{ datasetId }` |
| `GET` | `/datasets/{id}` | Dataset metadata | None | `Dataset` (404 when missing) |
| `GET` | `/datasets/{id}/preview` | Column types & sample | None | `DatasetProfile` |
| `GET` | `/datasets/{id}/processing` | Processing status | None | `ProcessingStatus` |
| `POST` | `/datasets/{id}/map-columns` | Map canonical columns | `{ [canonical]: srcColumn }` | Updated capabilities |
| `DELETE` | `/datasets/{id}` | Purge dataset records | None | `204 No Content` |

### Analytics Engine (`/api/v1/datasets/{id}/analytics`)

All endpoints support query filters: `datePreset`, `dateFrom`, `dateTo`, `comparison`, `groupBy`, `categories`, `regions`, `limit`, `offset`, `sortBy`.

| Method | Endpoint | Output Interface | Capability Requirement | Description |
| --- | --- | --- | --- | --- |
| `GET` | `/analytics/overview` | `OverviewData` | Base | Executive KPI cards, trend series, top products |
| `GET` | `/analytics/sales` | `SalesData` | Base | Trend curves, previous period comparisons, category matrices |
| `GET` | `/analytics/products` | `ProductsData` | Base | Top 5 performers, bottom 5 performers, catalog metrics |
| `GET` | `/analytics/customers` | `Capability<CustomersData>` | `customers` | RFM cohorts, new vs. returning curves, order frequency |
| `GET` | `/analytics/finance` | `Capability<FinanceData>` | `cost` | Total cost, gross margin %, category profit shares |
| `GET` | `/analytics/insights` | `Insight[]` | Base | Automated statistical anomaly and trend intelligence |
| `GET` | `/records` | `ExplorerData` | Base | Server-side paginated and sortable raw record grid |

### Reports & Binary Downloads (`/api/v1/datasets/{id}/reports`)

| Method | Endpoint | Description | Payload | Output |
| --- | --- | --- | --- | --- |
| `POST` | `/reports/preview` | Preview report structure | `ReportConfig` | `ReportPreview` |
| `GET` | `/reports` | List generated reports | None | `ReportRecord[]` |
| `POST` | `/reports` | Compile report artifact | `ReportConfig` | `ReportRecord` + `downloadUrl` |
| `GET` | `/reports/{id}/download` | Stream artifact download | None | Binary Stream (`application/pdf`, etc.) |

---

## Quickstart

### Local Python Environment

```bash
# 1. Clone the repository
git clone https://github.com/creatrix-ai/pulse.git
cd pulse/backend

# 2. Initialize virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Seed demo datasets and admin user
python3 -m app.db.seed

# 5. Start development server
./run.sh

```

* **API Root**: `http://localhost:8000`
* **Interactive Documentation (Swagger)**: `http://localhost:8000/docs`
* **Alternative Specification (ReDoc)**: `http://localhost:8000/redoc`

Default Credentials:

* **Email**: `admin@creatrix.io`
* **Password**: `password123`

### Production Docker Compose

```bash
cd backend
docker compose up -d --build

```

---

## Verification & Testing

Creatrix Pulse includes an internal test runner verifying API contracts, capability guards, calculations, and binary downloads:

```bash
cd backend
python3 run_tests.py

```

```
============================================================
  CREATRIX PULSE BACKEND TEST SUITE
============================================================
--- Authentication & Security ---
  [PASS] Health check
  [PASS] Login success
  [PASS] Login invalid password
  [PASS] Login blocked user
  [PASS] Register & /me profile
  [PASS] Refresh token rotation
  [PASS] Logout revocation

--- Datasets & Ingestion ---
  [PASS] List datasets
  [PASS] Get dataset detail
  [PASS] Get dataset not found 404
  [PASS] Get processing status ready
  [PASS] Get processing status failed
  [PASS] Upload CSV and purge dataset

--- Analytics Vector Engine ---
  [PASS] Analytics overview & KPIs
  [PASS] Analytics sales trend & previous period
  [PASS] Analytics products rankings
  [PASS] Customers capability available
  [PASS] Customers capability unavailable reason
  [PASS] Finance capability available
  [PASS] Finance capability unavailable reason
  [PASS] Records explorer pagination

--- Automated Insights Engine ---
  [PASS] Automated heuristic & anomaly insights
  [PASS] Dedicated insights endpoint

--- Reports & Streaming Exports ---
  [PASS] Report preview generation
  [PASS] Report CSV generation & download stream
  [PASS] Report PDF generation & download stream

============================================================
TEST SUMMARY: 26 passed, 0 failed in 0.62s
============================================================

```

---

## License

This project is licensed under the [Apache 2.0 License](https://www.google.com/search?q=LICENSE).
>>>>>>> 77fdf673ccff46dbf311add372661aef44a0e538
