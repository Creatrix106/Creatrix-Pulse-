# Creatrix Pulse – Backend integration guide

The frontend talks to the backend only through `src/services/*.service.ts`.
Every service exposes an interface and chooses an implementation from one flag:

| Env variable                | Purpose                                              | Default |
| --------------------------- | ---------------------------------------------------- | ------- |
| `NEXT_PUBLIC_API_BASE_URL`  | Backend root (the only place a URL is configured)    | `/api`  |
| `NEXT_PUBLIC_USE_MOCKS`     | Set to `false` to use the real HTTP implementations  | `true`  |

Mock code lives in `src/services/mock/` and can be deleted once the real API is connected.
UI components never import from `services/mock`.

## Endpoints the UI expects

Types are in `src/types/`. Errors must be `{ "code": string, "message": string, "details"?: unknown }`
with an appropriate HTTP status (4xx errors are not retried by TanStack Query).
Requests are sent with `credentials: "include"` so the backend can use an httpOnly session cookie.

### Auth (`auth.service.ts`)
- `POST /auth/login` `{ email, password }` → `User`
- `POST /auth/register` `{ name, email, password }` → `User`
- `POST /auth/logout` → `204`

### Datasets (`dataset.service.ts`)
- `GET /datasets` → `Dataset[]`
- `GET /datasets/:id` → `Dataset` (`404` when missing)
- `DELETE /datasets/:id` → `204`
- `POST /datasets` multipart: `file`, `mapping` (JSON `ColumnMapping`), `replaceDatasetId?` → `{ datasetId }`
- `GET /datasets/:id/processing` → `ProcessingStatus`. Poll interval is 1.2 s until `status` is `ready` or `failed`.
  `progress` must be a real 0–100 number or `null`; the UI never fabricates percentages.

### Analytics (`analytics.service.ts`)
All accept the global filters as query params: `datePreset`, `dateFrom`, `dateTo`, `comparison`, `groupBy`,
`categories` (repeated), `regions` (repeated).

- `GET /datasets/:id/analytics/overview` → `OverviewData`
- `GET /datasets/:id/analytics/sales` → `SalesData`
- `GET /datasets/:id/analytics/products` → `ProductsData`
- `GET /datasets/:id/analytics/customers` → `Capability<CustomersData>`
- `GET /datasets/:id/analytics/finance` → `Capability<FinanceData>`
- `GET /datasets/:id/analytics/insights` → `Insight[]`
- `GET /datasets/:id/records` → `ExplorerData` (the explorer table filters/sorts client-side; move to server paging for large data)

Return `{ "available": false, "reason": "…" }` for customers/finance when the dataset lacks the required columns –
the UI shows the reason and never calculates profit or margin without cost data.

### Reports (`report.service.ts`)
- `POST /datasets/:id/reports/preview` `ReportConfig` → `ReportPreview`
- `GET /datasets/:id/reports` → `ReportRecord[]`
- `POST /datasets/:id/reports` `ReportConfig` → `ReportRecord` (provide `downloadUrl`)

## Extending the app

- **New dashboard page:** add an entry to `src/config/navigation.ts` and a `page.tsx` under `app/dashboard/[datasetId]/<segment>/`.
  Sidebar, mobile menu, breadcrumbs and global-filter visibility follow the config.
- **New KPI:** return it in the `kpis` array – `KpiGrid` renders whatever it receives.
- **New chart:** build it on `ChartCard` + the shared helpers in `src/components/charts`.
- **New currency:** add it to `src/config/locale.ts`.
- **Theming:** edit tokens in `src/styles/tokens.css` (light values in `:root`, dark in `.dark`).
- **Role-based UI:** set `roles` on a page in `config/navigation.ts`; `User.role` comes from the auth service.
- **Feature flags:** `src/config/features.ts` controls unavailable-state UI (Excel preview/export, PDF, account actions).
