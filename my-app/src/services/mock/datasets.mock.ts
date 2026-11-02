import type {
  Dataset,
  DatasetCapabilities,
  DatasetColumn,
  DatasetStatus,
  ProcessingStage,
  ProcessingStageId,
  ProcessingStatus,
  UploadRequest,
  UploadResult,
} from "@/types/dataset";
import { ApiError } from "../api-client";
import { DATA_END, getRows, listDimensions } from "./engine";
import { delay, readStorage, writeStorage } from "./utils";

const STORAGE_KEY = "cp-mock-datasets";
const STAGE_DURATION_MS = 1500;

export const STAGES: { id: ProcessingStageId; label: string }[] = [
  { id: "upload", label: "Uploading dataset" },
  { id: "validate", label: "Validating columns" },
  { id: "process", label: "Processing records" },
  { id: "analytics", label: "Generating analytics" },
  { id: "prepare", label: "Preparing dashboard" },
];

interface StoredState {
  created: (Dataset & { startedAt: number })[];
  deletedIds: string[];
}

const FULL: DatasetCapabilities = { customers: true, cost: true, regions: true };

function baseColumns(caps: DatasetCapabilities): DatasetColumn[] {
  const cols: DatasetColumn[] = [
    { name: "Order ID", type: "string", mappedTo: "orderId" },
    { name: "Date", type: "date", mappedTo: "date" },
    { name: "Product", type: "string", mappedTo: "product" },
    { name: "Category", type: "string", mappedTo: "category" },
  ];
  if (caps.regions) cols.push({ name: "Region", type: "string", mappedTo: "region" });
  if (caps.customers) cols.push({ name: "Customer ID", type: "string", mappedTo: "customer" });
  cols.push({ name: "Quantity", type: "number", mappedTo: "quantity" }, { name: "Revenue", type: "number", mappedTo: "revenue" });
  if (caps.cost) cols.push({ name: "Cost", type: "number", mappedTo: "cost" });
  return cols;
}

function buildSeed(
  id: string,
  name: string,
  fileName: string,
  fileSize: number,
  caps: DatasetCapabilities,
  uploadedAt: string,
  status: DatasetStatus = "ready",
  errorMessage?: string,
): Dataset {
  const rows = getRows(id, caps);
  const columns = baseColumns(caps);
  return {
    id,
    name,
    fileName,
    fileSize,
    rowCount: rows.length,
    columnCount: columns.length,
    status,
    uploadedAt,
    dateRange: status === "failed" ? null : { from: rows[0].date, to: DATA_END },
    capabilities: caps,
    columns,
    filterOptions: listDimensions(rows),
    errorMessage,
  };
}

let seeds: Dataset[] | null = null;
function getSeeds(): Dataset[] {
  seeds ??= [
    buildSeed("demo-retail", "Retail Sales 2026", "retail_sales_2026.csv", 412_000, FULL, "2026-10-31T09:14:00.000Z"),
    buildSeed("demo-marketplace", "Marketplace Orders (no cost data)", "marketplace_orders.xlsx", 268_000, { customers: true, cost: false, regions: true }, "2026-10-12T14:40:00.000Z"),
    buildSeed("demo-wholesale", "Wholesale Ledger (no customer data)", "wholesale_ledger.csv", 190_000, { customers: false, cost: true, regions: false }, "2026-09-02T08:05:00.000Z"),
    {
      ...buildSeed("demo-failed", "Q3 Export", "q3_export_final.csv", 98_000, FULL, "2026-08-21T17:22:00.000Z", "failed", "The date column could not be parsed in 214 rows. Re-export the file with ISO dates (YYYY-MM-DD) and upload it again."),
      rowCount: 0,
    },
  ];
  return seeds;
}

function readState(): StoredState {
  return readStorage<StoredState>(STORAGE_KEY, { created: [], deletedIds: [] });
}

function statusFromElapsed(elapsed: number): { stages: ProcessingStage[]; status: DatasetStatus } {
  // "upload" is finished before processing begins, so the clock starts at the second stage.
  const activeIndex = 1 + Math.floor(elapsed / STAGE_DURATION_MS);
  const done = activeIndex >= STAGES.length;
  const stages = STAGES.map((s, i): ProcessingStage => ({
    ...s,
    status: done || i < activeIndex ? "complete" : i === activeIndex ? "active" : "pending",
  }));
  const active = STAGES[Math.min(activeIndex, STAGES.length - 1)].id;
  const status: DatasetStatus = done ? "ready" : active === "validate" ? "validating" : active === "process" ? "processing" : "generating";
  return { stages, status };
}

function allDatasets(): Dataset[] {
  const state = readState();
  const created = state.created.map((d) => {
    if (d.status === "ready" || d.status === "failed") return d;
    return { ...d, status: statusFromElapsed(Date.now() - d.startedAt).status };
  });
  return [...created.slice().reverse(), ...getSeeds().filter((d) => !state.deletedIds.includes(d.id))];
}

export const mockDatasetService = {
  async list(): Promise<Dataset[]> {
    await delay();
    return allDatasets();
  },

  async get(id: string): Promise<Dataset> {
    await delay(200);
    const dataset = allDatasets().find((d) => d.id === id);
    if (!dataset) throw new ApiError(404, { code: "dataset_not_found", message: "This dataset does not exist or was deleted." });
    return dataset;
  },

  async remove(id: string): Promise<void> {
    await delay();
    const state = readState();
    writeStorage<StoredState>(STORAGE_KEY, {
      created: state.created.filter((d) => d.id !== id),
      deletedIds: [...state.deletedIds, id],
    });
  },

  /** Upload progress is simulated in mock mode; the HTTP implementation reports real XHR progress. */
  async upload(req: UploadRequest, onProgress?: (percent: number) => void): Promise<UploadResult> {
    for (let p = 0; p <= 100; p += 20) {
      onProgress?.(p);
      await new Promise((r) => setTimeout(r, 160));
    }
    const mapped = req.mapping;
    // Excel files have no client-side profile (the backend would map them), so the mock assumes full data.
    const caps: DatasetCapabilities = req.profile ? { customers: !!mapped.customer, cost: !!mapped.cost, regions: !!mapped.region } : FULL;
    const id = `ds-${Date.now().toString(36)}`;
    const columns: DatasetColumn[] = (req.profile?.columns ?? []).map((c) => ({
      name: c.name,
      type: c.type,
      mappedTo: (Object.entries(mapped).find(([, col]) => col === c.name)?.[0] ?? undefined) as DatasetColumn["mappedTo"],
    }));
    // Mock: analytics are generated from the demo generator, not from the uploaded file contents.
    const rows = getRows(id, caps);
    const dataset: Dataset & { startedAt: number } = {
      id,
      name: req.file.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " "),
      fileName: req.file.name,
      fileSize: req.file.size,
      rowCount: req.profile?.rowCount ?? rows.length,
      columnCount: columns.length || req.profile?.headers.length || 0,
      status: "validating",
      uploadedAt: new Date().toISOString(),
      dateRange: { from: rows[0].date, to: DATA_END },
      capabilities: caps,
      columns,
      filterOptions: listDimensions(rows),
      startedAt: Date.now(),
    };
    const state = readState();
    writeStorage<StoredState>(STORAGE_KEY, {
      created: [...state.created, dataset],
      deletedIds: req.replaceDatasetId ? [...state.deletedIds, req.replaceDatasetId] : state.deletedIds,
    });
    return { datasetId: id };
  },

  async getProcessingStatus(id: string): Promise<ProcessingStatus> {
    await delay(150);
    const state = readState();
    const stored = state.created.find((d) => d.id === id);
    if (!stored) {
      const seed = getSeeds().find((d) => d.id === id);
      if (!seed) throw new ApiError(404, { code: "dataset_not_found", message: "This dataset does not exist." });
      const failed = seed.status === "failed";
      return {
        datasetId: id,
        status: seed.status,
        progress: null,
        message: seed.errorMessage,
        stages: STAGES.map((s, i) => ({ ...s, status: failed ? (i === 0 ? "complete" : i === 1 ? "failed" : "pending") : "complete" })),
      };
    }
    const { stages, status } = statusFromElapsed(Date.now() - stored.startedAt);
    if (status === "ready" && stored.status !== "ready") {
      writeStorage<StoredState>(STORAGE_KEY, {
        ...state,
        created: state.created.map((d) => (d.id === id ? { ...d, status: "ready" } : d)),
      });
    }
    return { datasetId: id, status, stages, progress: null };
  },
};
