import { DATE_PRESETS, METRIC_OPTIONS } from "@/config/filters";
import type { ReportConfig, ReportPreview, ReportRecord } from "@/types/report";
import { toCsv } from "@/utils/csv";
import { mockDatasetService } from "./datasets.mock";
import { getRows, sliceRows, timeSeries, totals } from "./engine";
import { delay, readStorage, writeStorage } from "./utils";

const KEY = "cp-mock-reports";

async function buildPreview(datasetId: string, config: ReportConfig): Promise<ReportPreview> {
  const dataset = await mockDatasetService.get(datasetId);
  const rows = getRows(dataset.id, dataset.capabilities);
  const sliced = sliceRows(rows, { datePreset: config.datePreset, comparison: "none", groupBy: "month", categories: [], regions: [] });
  const series = timeSeries(sliced.current, "month");
  const t = totals(sliced.current);
  const metrics = METRIC_OPTIONS.filter((m) => config.metrics.includes(m.value) && !(m.requiresCost && !dataset.capabilities.cost));
  const summaryValue = (key: string): number => ({ revenue: t.revenue, orders: t.orders, units: t.units, aov: t.aov, cost: t.cost ?? 0, profit: t.profit ?? 0 })[key] ?? 0;
  return {
    title: config.title,
    generatedAt: new Date().toISOString(),
    period: sliced.range,
    summary: metrics.map((m) => ({ label: m.label, value: summaryValue(m.value), format: m.format })),
    columns: [{ key: "date", label: "Month", format: "date" }, ...metrics.map((m) => ({ key: m.value, label: m.label, format: m.format }))],
    rows: series.map((p) => ({ date: p.date, ...Object.fromEntries(metrics.map((m) => [m.value, p[m.value] ?? 0])) })),
  };
}

export const mockReportService = {
  async preview(datasetId: string, config: ReportConfig): Promise<ReportPreview> {
    await delay();
    return buildPreview(datasetId, config);
  },

  async list(datasetId: string): Promise<ReportRecord[]> {
    await delay(200);
    return readStorage<ReportRecord[]>(KEY, []).filter((r) => r.datasetId === datasetId);
  },

  async create(datasetId: string, config: ReportConfig): Promise<ReportRecord> {
    await delay(600);
    const preview = await buildPreview(datasetId, config);
    const content =
      config.format === "json"
        ? JSON.stringify(preview, null, 2)
        : toCsv(preview.columns.map((c) => c.label), preview.rows.map((r) => preview.columns.map((c) => r[c.key])));
    const record: ReportRecord = {
      id: `rep-${Date.now().toString(36)}`,
      datasetId,
      title: `${config.title} (${DATE_PRESETS.find((p) => p.value === config.datePreset)?.label ?? config.datePreset})`,
      format: config.format,
      createdAt: new Date().toISOString(),
      rowCount: preview.rows.length,
      sizeBytes: new Blob([content]).size,
      content,
    };
    writeStorage(KEY, [record, ...readStorage<ReportRecord[]>(KEY, [])]);
    return record;
  },
};
