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

```

---

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

This project is licensed under the [MIT License](https://www.google.com/search?q=LICENSE).
