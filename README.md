

```markdown
<div align="center">

  <img src="https://raw.githubusercontent.com/creatrix-ai/pulse/main/docs/assets/banner.png" alt="Creatrix Pulse Banner" width="100%" style="border-radius: 12px; margin-bottom: 20px;" onerror="this.style.display='none'" />

  # ⚡ Creatrix Pulse

  ### *Enterprise-Grade Analytics Engine & Real-Time Business Intelligence*

  <p align="center">
    A high-performance, asynchronous, and strictly typed full-stack data analytics platform.<br />
    Vectorized tabular aggregations, automated statistical anomaly detection, dynamic PDF/Excel report compilation, and multi-tenant isolation.
  </p>

  <p align="center">
    <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
    <a href="https://nextjs.org/"><img src="https://img.shields.io/badge/Next.js%2014+-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Next.js" /></a>
    <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL%2015+-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" /></a>
    <a href="https://pandas.pydata.org/"><img src="https://img.shields.io/badge/Pandas%20%2F%20Parquet-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" /></a>
    <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker%20Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" /></a>
    <a href="https://docs.pydantic.dev/"><img src="https://img.shields.io/badge/Pydantic%20v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white" alt="Pydantic" /></a>
  </p>

  <p align="center">
    <a href="#-architecture--system-design">Architecture</a> •
    <a href="#-key-features">Key Features</a> •
    <a href="#-tech-stack">Tech Stack</a> •
    <a href="#-getting-started">Quickstart</a> •
    <a href="#-api-reference">API Reference</a> •
    <a href="#-test-suite">Testing</a> •
    <a href="#-license">License</a>
  </p>

  <br />

  <table align="center" width="100%">
    <tr>
      <td align="center" width="25%">
        <b>⚡ Ultra-Fast Aggregations</b><br />
        <sub>Vectorized columnar processing via Apache Parquet & Pandas</sub>
      </td>
      <td align="center" width="25%">
        <b>🛡️ Strict Capability Guards</b><br />
        <sub>Zero hallucinated metrics when cost/customer data is missing</sub>
      </td>
      <td align="center" width="25%">
        <b>🧠 Statistical Intelligence</b><br />
        <sub>Z-score outlier detection, RFM cohorts, and growth movers</sub>
      </td>
      <td align="center" width="25%">
        <b>📄 Multi-Format Exports</b><br />
        <sub>Streaming compilation of PDF, Excel (.xlsx), CSV, and JSON</sub>
      </td>
    </tr>
  </table>

</div>

<br />

---

## 🏛️ Architecture & System Design

Creatrix Pulse separates high-throughput API routing from analytical computational loads. In-flight requests leverage an in-memory / Parquet vectorized pipeline, shielding relational database transaction pools from heavy tabular aggregation scans.


```

┌────────────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend (React)                        │
│            TanStack Query • Recharts • Tailwind CSS • Zustand          │
└───────────────────────────────────┬────────────────────────────────────┘
│ HTTP / REST (JWT & httpOnly Cookies)
▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application Gateway                     │
│    - CORS Middleware (localhost:3000)                                  │
│    - OAuth2 Password Bearer & Session Cookie Interceptors              │
│    - Multi-Prefix Routers: `/api/v1`, `/api`, and `/`                  │
│    - Global Standardized Response & Error Envelopes                    │
└───────┬───────────────────────────┬───────────────────────────┬────────┘
│                           │                           │
▼                           ▼                           ▼
┌──────────────────┐    ┌───────────────────────┐   ┌───────────────────────┐
│ PostgreSQL 15+   │    │ Vector Analytics Core │   │ Document Compilers    │
│  - SQLAlchemy 2  │    │  - Columnar Parquet   │   │  - ReportLab PDF Deck │
│  - Alembic DDL   │    │  - Pandas Processing  │   │  - OpenPyXL Workbooks │
│  - B-Tree/JSONB  │    │  - Sub-ms aggregations│   │  - Stream Downloads   │
└──────────────────┘    └───────────────────────┘   └───────────────────────┘

```

<br />

---

## ✨ Key Features

<table>
  <tr>
    <td width="50%">
      <h3>📊 Vectorized Analytics Engine</h3>
      <ul>
        <li><b>High-Speed KPIs</b>: Instant calculations for Gross Revenue, Order Volume, Units Sold, Average Order Value (AOV), Gross Profit, and Margin %.</li>
        <li><b>Dynamic Period Comparisons</b>: Period-over-period percentage variance calculations against prior windows.</li>
        <li><b>Multi-Dimensional Slicing</b>: Native bucketing by <code>day</code>, <code>week</code>, or <code>month</code> with category and regional multi-select filters.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🧠 Automated Insights & Anomaly Detection</h3>
      <ul>
        <li><b>Statistical Outlier Alerts</b>: Automated Z-score anomaly scans flagging weekly revenue spikes or dips (≥ 1.8σ).</li>
        <li><b>Catalog Concentration Risk</b>: Automatic triggers when top 3 SKUs dominate &gt;40% of total revenue share.</li>
        <li><b>Performance Movers</b>: Automatic ranking of top growth and largest declining products across periods.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>👥 Customer Intelligence & Cohorts</h3>
      <ul>
        <li><b>RFM Segmentation</b>: Rule-based cohort classification into <code>Champions</code> (6+ orders), <code>Loyal</code> (3–5), <code>Returning</code> (2), and <code>One-time</code> (1).</li>
        <li><b>New vs. Returning Trends</b>: Historical cohort retention curves across configured time buckets.</li>
        <li><b>Capability Gating</b>: Returns <code>{ available: false, reason: "..." }</code> when customer identifiers are absent, eliminating placeholder data.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>📄 Multi-Format Report Builder</h3>
      <ul>
        <li><b>Publication-Grade PDFs</b>: Clean, executive-ready PDF generation built with ReportLab including KPI cards and formatted tables.</li>
        <li><b>Formatted Excel Spreadsheets</b>: Multi-tab styled <code>.xlsx</code> workbooks via OpenPyXL.</li>
        <li><b>Low-Latency Streams</b>: Direct binary streaming with proper MIME types and <code>Content-Disposition</code> headers.</li>
      </ul>
    </td>
  </tr>
</table>

<br />

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technologies |
| :--- | :--- |
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+), [Uvicorn](https://www.uvicorn.org/) (ASGI) |
| **Data Validation** | [Pydantic v2](https://docs.pydantic.dev/) (Strict contract compliance with frontend schemas) |
| **Relational Database** | [PostgreSQL 15+](https://www.postgresql.org/) with [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (`asyncpg`), [Alembic](https://alembic.sqlalchemy.org/) |
| **Analytics & Columnar Storage**| [Pandas](https://pandas.pydata.org/), [Apache Parquet](https://parquet.apache.org/) (via [PyArrow](https://arrow.apache.org/)), [NumPy](https://numpy.org/) |
| **Document Generation** | [ReportLab](https://www.reportlab.com/) (PDFs), [OpenPyXL](https://openpyxl.readthedocs.io/) & [XlsxWriter](https://xlsxwriter.readthedocs.io/) (Excel) |
| **Authentication & RBAC** | OAuth2 Password Bearer, JWT (HS256), PBKDF2-HMAC-SHA256 (100k rounds) |
| **Infrastructure & Queue** | [Docker Compose](https://docs.docker.com/compose/), [Redis 7](https://redis.io/), [Celery](https://docs.celeryq.dev/) |
| **Frontend Integration** | [Next.js](https://nextjs.org/) (App Router), [TanStack Query v5](https://tanstack.com/query), [Tailwind CSS](https://tailwindcss.com/) |

</div>

<br />

---

## 📂 Repository Layout


```

.
├── backend/
│   ├── alembic/                  # Database migration environments & versions
│   │   ├── versions/             # 001_initial_schema.py (PostgreSQL DDL)
│   │   └── env.py                # Async migration runner
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py           # Authentication dependencies & RBAC guards
│   │   │   └── v1/               # Endpoint routers (auth, datasets, analytics, insights, reports)
│   │   ├── core/                 # Security (JWT, PBKDF2), responses, custom exceptions
│   │   ├── db/                   # Database repository, schema.sql, and deterministic seeder
│   │   ├── models/               # SQLAlchemy 2.0 declarative database entities
│   │   ├── schemas/              # Pydantic schemas mapping frontend TypeScript contracts
│   │   ├── services/             # Analytics engine, ingestion pipeline, insights, and reports
│   │   ├── config.py             # Pydantic BaseSettings environment configuration
│   │   └── main.py               # Application factory, CORS, and multi-prefix routes
│   ├── data/                     # Local SQLite DB, Parquet files, and export caches
│   ├── tests/                    # Comprehensive unit and integration test suite
│   ├── docker-compose.yml        # PostgreSQL 15, Redis, Celery, and API stack
│   ├── Dockerfile                # Production multi-stage Docker build
│   ├── requirements.txt          # Production dependencies
│   ├── run_tests.py              # Standalone automated test runner
│   └── run.sh                    # One-click startup script
└── docs/                         # Architecture documentation & API references

```

<br />

---

## 🚀 Getting Started

### Option 1: Quickstart with Local Python

```bash
# 1. Clone the repository
git clone [https://github.com/creatrix-ai/pulse.git](https://github.com/creatrix-ai/pulse.git)
cd pulse/backend

# 2. Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Seed the database with demo datasets & admin user
python3 -m app.db.seed

# 5. Start the API server
./run.sh

```

The API will be available at:

* **API Root**: `http://localhost:8000`
* **Interactive Swagger UI**: `http://localhost:8000/docs`
* **ReDoc Reference**: `http://localhost:8000/redoc`

Default administrative credentials:

* **Email**: `admin@creatrix.io`
* **Password**: `password123`

---

### Option 2: Production Deployment with Docker Compose

Spin up the complete multi-service stack with PostgreSQL 15, Redis, and FastAPI:

```bash
cd backend
docker compose up -d --build

```

Verify services status:

```bash
docker compose ps

```

---

## 📡 API Reference & Contract Mapping

Creatrix Pulse features **universal multi-prefix mounting** (`/api/v1`, `/api`, and `/`), ensuring standard compatibility with any frontend base URL configuration.

| Method | Endpoint | Description | Request Payload | Response |
| --- | --- | --- | --- | --- |
| `POST` | `/auth/register` | Register new user | `{ name, email, password, role? }` | `User` profile + JWT tokens |
| `POST` | `/auth/login` | Login user | `{ email, password }` or Form | `User` profile + tokens + session cookie |
| `GET` | `/auth/me` | Current authenticated session | *Session Cookie / Bearer Header* | `User` object |
| `POST` | `/auth/refresh` | Rotate access token | `{ refresh_token }` | `{ access_token, refresh_token }` |
| `POST` | `/auth/logout` | Revoke session cookies | None | `204 No Content` |

| Method | Endpoint | Description | Query / Body | Response |
| --- | --- | --- | --- | --- |
| `GET` | `/datasets` | List all datasets | `envelope=false` | `Dataset[]` |
| `POST` | `/datasets` | Multipart file upload | `file`, `mapping?`, `replaceDatasetId?` | `{ datasetId }` |
| `GET` | `/datasets/{id}` | Dataset metadata & caps | None | `Dataset` (404 when missing) |
| `GET` | `/datasets/{id}/preview` | Column types & sample | None | `DatasetProfile` |
| `GET` | `/datasets/{id}/processing` | Processing progress | None | `ProcessingStatus` |
| `POST` | `/datasets/{id}/map-columns` | Map canonical columns | `{ [canonical]: srcColumn }` | Updated capabilities |
| `DELETE` | `/datasets/{id}` | Purge metadata & records | None | `204 No Content` |

All analytics endpoints accept global filters:
`datePreset` (`all`, `last_30d`, `last_90d`, `last_180d`, `ytd`, `custom`), `dateFrom`, `dateTo`, `comparison` (`none`, `previous_period`), `groupBy` (`day`, `week`, `month`), `categories`, and `regions`.

| Endpoint | Output Interface | Description |
| --- | --- | --- |
| `GET /analytics/overview` | `OverviewData` | Revenue, Orders, Units, AOV, Gross Profit, Margin %, Top 5 Products, Breakdown. |
| `GET /analytics/sales` | `SalesData` | Time-series trend with previous period comparisons and category trend matrices. |
| `GET /analytics/products` | `ProductsData` | Top 5 performers, bottom 5 performers, full product catalog metrics. |
| `GET /analytics/customers` | `Capability<CustomersData>` | New vs. returning trends, order frequency bins, and RFM customer segments. |
| `GET /analytics/finance` | `Capability<FinanceData>` | Cost totals, margin breakdowns by category, and profit time series. |
| `GET /analytics/insights` | `Insight[]` | Automated anomaly detection, growth movers, and concentration alerts. |
| `GET /records` | `ExplorerData` | Dynamic server-side paginated explorer table with custom dimension sorting. |

| Method | Endpoint | Description | Request Body | Response |
| --- | --- | --- | --- | --- |
| `POST` | `/reports/preview` | Preview report structure | `ReportConfig` | `ReportPreview` |
| `GET` | `/reports` | List generated reports | None | `ReportRecord[]` |
| `POST` | `/reports` | Compile report artifact | `ReportConfig` (PDF/Excel/CSV/JSON) | `ReportRecord` + `downloadUrl` |
| `GET` | `/reports/{id}/download` | Stream compiled artifact | None | Binary stream (`application/pdf`, etc.) |

---

## 🧪 Test Suite

```bash
# Run the complete test suite
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

## 🔒 Security & Capability Guarding

1. **Zero-Metric Hallucination Policy**: If an uploaded dataset lacks cost or customer identifiers, the API returns `{ available: false, reason: "..." }` rather than inventing false baseline metrics.
2. **Strict Multi-Tenant Isolation**: Row-level indexing and dataset isolation guarantees zero cross-tenant data leakage.
3. **Session Cookie + Bearer Dual-Token Model**: Works out-of-the-box with browser sessions using `credentials: "include"` and standard API client header authentication.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.
