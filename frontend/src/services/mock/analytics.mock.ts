import type {
  CustomersResponse,
  ExplorerData,
  ExplorerColumn,
  ExplorerRow,
  FinanceResponse,
  Kpi,
  OverviewData,
  ProductsData,
  SalesData,
} from "@/types/analytics";
import type { Insight } from "@/types/insight";
import type { AnalyticsFilters } from "@/types/filters";
import type { Dataset } from "@/types/dataset";
import { createFormatters } from "@/utils/format";
import { mockDatasetService } from "./datasets.mock";
import {
  breakdown,
  bucketKey,
  getRows,
  pctChange,
  productPerformance,
  sliceRows,
  timeSeries,
  totals,
  type RawRow,
  type SlicedRows,
  type Totals,
} from "./engine";
import { delay } from "./utils";

async function load(datasetId: string, filters: AnalyticsFilters) {
  const dataset = await mockDatasetService.get(datasetId);
  const rows = getRows(dataset.id, dataset.capabilities);
  const sliced = sliceRows(rows, filters);
  return { dataset, rows, sliced };
}

const kpi = (id: string, label: string, value: number, format: Kpi["format"], change: number | null, extra?: Partial<Kpi>): Kpi => ({
  id,
  label,
  value,
  format,
  change,
  ...extra,
});

function coreKpis(cur: Totals, prev: Totals | null): Kpi[] {
  return [
    kpi("revenue", "Revenue", cur.revenue, "currency", pctChange(cur.revenue, prev?.revenue)),
    kpi("orders", "Orders", cur.orders, "number", pctChange(cur.orders, prev?.orders)),
    kpi("units", "Units sold", cur.units, "number", pctChange(cur.units, prev?.units)),
    kpi("aov", "Avg. order value", cur.aov, "currency", pctChange(cur.aov, prev?.aov)),
  ];
}

function profitKpis(cur: Totals, prev: Totals | null): Kpi[] {
  if (cur.profit === null || cur.margin === null) return [];
  return [
    kpi("profit", "Gross profit", cur.profit, "currency", pctChange(cur.profit, prev?.profit)),
    kpi("margin", "Profit margin", cur.margin, "percent", prev?.margin != null ? cur.margin - prev.margin : null, { hint: "Change in percentage points" }),
  ];
}

/* --------------------------------- insights -------------------------------- */

function buildInsights(sliced: SlicedRows, dataset: Dataset, filters: AnalyticsFilters): Insight[] {
  const f = createFormatters({ currency: "INR", locale: "en-IN" });
  const { current, previous } = sliced;
  if (current.length === 0) return [];
  const cur = totals(current);
  const prev = previous ? totals(previous) : null;
  const out: Insight[] = [];

  const change = pctChange(cur.revenue, prev?.revenue);
  if (prev && change !== null) {
    out.push({
      id: "revenue-change",
      type: change >= 0 ? "positive" : "negative",
      metric: "revenue",
      title: `Revenue ${change >= 0 ? "increased" : "decreased"} by ${Math.abs(change).toFixed(1)}% vs the previous period`,
      summary: `Revenue moved from ${f.currency(prev.revenue)} to ${f.currency(cur.revenue)} across comparable periods.`,
      evidence: [
        { label: "Current period", value: f.currency(cur.revenue) },
        { label: "Previous period", value: f.currency(prev.revenue) },
        { label: "Orders change", value: f.percent(pctChange(cur.orders, prev.orders) ?? 0, { signed: true }) },
      ],
    });
  } else {
    out.push({
      id: "revenue-total",
      type: "observation",
      metric: "revenue",
      title: `${f.currency(cur.revenue)} in revenue from ${f.number(cur.orders)} orders`,
      summary: "Enable a comparison period to see how this compares with earlier performance.",
      evidence: [
        { label: "Orders", value: f.number(cur.orders) },
        { label: "Average order value", value: f.currency(cur.aov) },
      ],
    });
  }

  const categories = breakdown(current, (r) => r.category, previous);
  if (categories[0]) {
    out.push({
      id: "top-category",
      type: "observation",
      metric: "category",
      title: `${categories[0].name} contributed ${categories[0].share.toFixed(1)}% of revenue`,
      summary: `It is the largest category, ahead of ${categories[1]?.name ?? "all others"}.`,
      evidence: categories.slice(0, 3).map((c) => ({ label: c.name, value: `${f.currency(c.value)} · ${c.share.toFixed(1)}%` })),
    });
  }

  const products = productPerformance(current, previous);
  const top3 = products.slice(0, 3).reduce((s, p) => s + p.share, 0);
  if (products.length >= 5 && top3 > 40) {
    out.push({
      id: "concentration",
      type: "recommendation",
      metric: "product",
      title: "Revenue is concentrated in a few products",
      summary: "Review stock levels and promotion plans for the best sellers, and consider supporting mid-ranked products.",
      evidence: [
        { label: "Top 3 products share", value: `${top3.toFixed(1)}%` },
        ...products.slice(0, 3).map((p) => ({ label: p.name, value: `${p.share.toFixed(1)}%` })),
      ],
    });
  }
  if (prev) {
    const movers = products.filter((p) => p.change !== null && p.change !== undefined);
    const best = [...movers].sort((a, b) => (b.change ?? 0) - (a.change ?? 0))[0];
    const worst = [...movers].sort((a, b) => (a.change ?? 0) - (b.change ?? 0))[0];
    if (best && (best.change ?? 0) > 0) {
      out.push({ id: "best-mover", type: "positive", metric: "product", title: `${best.name} grew ${best.change?.toFixed(1)}% in revenue`, summary: "The strongest improvement among all products versus the previous period.", evidence: [{ label: "Revenue", value: f.currency(best.revenue) }, { label: "Units", value: f.number(best.units) }] });
    }
    if (worst && (worst.change ?? 0) < 0) {
      out.push({ id: "worst-mover", type: "negative", metric: "product", title: `${worst.name} declined ${Math.abs(worst.change ?? 0).toFixed(1)}% in revenue`, summary: "The largest decline among products versus the previous period.", evidence: [{ label: "Revenue", value: f.currency(worst.revenue) }, { label: "Units", value: f.number(worst.units) }] });
    }
  }

  const weekly = timeSeries(current, "week").filter((p, i, arr) => i > 0 && i < arr.length - 1 || arr.length < 3);
  if (weekly.length >= 8) {
    const mean = weekly.reduce((s, p) => s + p.revenue, 0) / weekly.length;
    const sd = Math.sqrt(weekly.reduce((s, p) => s + (p.revenue - mean) ** 2, 0) / weekly.length);
    const outlier = weekly.map((p) => ({ p, z: sd ? (p.revenue - mean) / sd : 0 })).sort((a, b) => Math.abs(b.z) - Math.abs(a.z))[0];
    if (outlier && Math.abs(outlier.z) >= 2) {
      const dev = ((outlier.p.revenue - mean) / mean) * 100;
      out.push({
        id: "anomaly-week",
        type: "anomaly",
        metric: "revenue",
        title: `Unusual ${dev > 0 ? "spike" : "drop"} in the week of ${f.date(outlier.p.date, "long")}`,
        summary: `Weekly revenue was ${Math.abs(dev).toFixed(0)}% ${dev > 0 ? "above" : "below"} the typical week. Check campaigns, outages or data-entry issues for that week.`,
        evidence: [
          { label: "Revenue that week", value: f.currency(outlier.p.revenue) },
          { label: "Typical week", value: f.currency(mean) },
          { label: "Deviation", value: `${outlier.z.toFixed(1)} standard deviations` },
        ],
      });
    }
  }

  const regions = breakdown(current, (r) => r.region, previous);
  if (regions.length >= 3) {
    const avgShare = 100 / regions.length;
    const weakest = regions[regions.length - 1];
    out.push({ id: "top-region", type: "observation", metric: "region", title: `${regions[0].name} is the strongest region at ${regions[0].share.toFixed(1)}% of revenue`, summary: "Regional share of total revenue across the selected period.", evidence: regions.map((r) => ({ label: r.name, value: `${r.share.toFixed(1)}%` })) });
    if (weakest.share < avgShare * 0.8) {
      out.push({ id: "weak-region", type: "recommendation", metric: "region", title: `Review growth opportunities in ${weakest.name}`, summary: "Its revenue share is well below an even split across regions.", evidence: [{ label: `${weakest.name} share`, value: `${weakest.share.toFixed(1)}%` }, { label: "Even-split benchmark", value: `${avgShare.toFixed(1)}%` }] });
    }
  }

  if (dataset.capabilities.cost && cur.margin !== null) {
    const margins = marginsByCategory(current).sort((a, b) => a.value - b.value);
    if (margins[0]) {
      out.push({ id: "low-margin", type: "recommendation", metric: "margin", title: `${margins[0].name} has the thinnest margin at ${margins[0].value.toFixed(1)}%`, summary: "Review pricing or supplier costs for this category.", evidence: margins.map((m) => ({ label: m.name, value: `${m.value.toFixed(1)}%` })) });
    }
  }

  if (dataset.capabilities.customers) {
    const orderCounts = new Map<string, number>();
    current.forEach((r) => r.customerId && orderCounts.set(r.customerId, (orderCounts.get(r.customerId) ?? 0) + 1));
    const total = orderCounts.size;
    const repeat = [...orderCounts.values()].filter((n) => n > 1).length;
    if (total > 0) {
      out.push({ id: "repeat-rate", type: "observation", metric: "customers", title: `${((repeat / total) * 100).toFixed(1)}% of customers purchased more than once`, summary: "Share of customers with at least two orders in the selected period.", evidence: [{ label: "Customers", value: f.number(total) }, { label: "Repeat customers", value: f.number(repeat) }] });
    }
  }
  void filters;
  return out;
}

function marginsByCategory(rows: RawRow[]) {
  const map = new Map<string, { revenue: number; cost: number }>();
  rows.forEach((r) => {
    const e = map.get(r.category) ?? { revenue: 0, cost: 0 };
    e.revenue += r.revenue;
    e.cost += r.cost ?? 0;
    map.set(r.category, e);
  });
  return [...map.entries()].map(([name, v]) => ({ name, value: v.revenue ? ((v.revenue - v.cost) / v.revenue) * 100 : 0, profit: v.revenue - v.cost, revenue: v.revenue }));
}

/* --------------------------------- service --------------------------------- */

export const mockAnalyticsService = {
  async getOverview(datasetId: string, filters: AnalyticsFilters): Promise<OverviewData> {
    await delay();
    const { dataset, sliced } = await load(datasetId, filters);
    const cur = totals(sliced.current);
    const prev = sliced.previous ? totals(sliced.previous) : null;
    return {
      period: sliced.range,
      kpis: [...coreKpis(cur, prev), ...profitKpis(cur, prev)],
      revenueTrend: timeSeries(sliced.current, filters.groupBy),
      topProducts: productPerformance(sliced.current, sliced.previous).slice(0, 5),
      categories: breakdown(sliced.current, (r) => r.category, sliced.previous),
      regions: breakdown(sliced.current, (r) => r.region, sliced.previous),
      insights: buildInsights(sliced, dataset, filters).slice(0, 4),
    };
  },

  async getSales(datasetId: string, filters: AnalyticsFilters): Promise<SalesData> {
    await delay();
    const { sliced } = await load(datasetId, filters);
    const cur = totals(sliced.current);
    const prev = sliced.previous ? totals(sliced.previous) : null;
    const categories = breakdown(sliced.current, (r) => r.category, sliced.previous);
    const buckets = new Map<string, Record<string, number>>();
    for (const r of sliced.current) {
      const key = bucketKey(r.date, filters.groupBy);
      const values = buckets.get(key) ?? {};
      values[r.category] = (values[r.category] ?? 0) + r.revenue;
      buckets.set(key, values);
    }
    return {
      kpis: coreKpis(cur, prev),
      trend: timeSeries(sliced.current, filters.groupBy),
      previousTrend: sliced.previous ? timeSeries(sliced.previous, filters.groupBy) : null,
      categories,
      regions: breakdown(sliced.current, (r) => r.region, sliced.previous),
      categoryNames: categories.map((c) => c.name),
      categoryTrend: [...buckets.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([date, values]) => ({ date, values })),
    };
  },

  async getProducts(datasetId: string, filters: AnalyticsFilters): Promise<ProductsData> {
    await delay();
    const { sliced } = await load(datasetId, filters);
    const all = productPerformance(sliced.current, sliced.previous);
    return {
      all,
      top: all.slice(0, 5),
      low: [...all].reverse().slice(0, 5),
      categories: breakdown(sliced.current, (r) => r.category, sliced.previous),
    };
  },

  async getCustomers(datasetId: string, filters: AnalyticsFilters): Promise<CustomersResponse> {
    await delay();
    const { dataset, sliced } = await load(datasetId, filters);
    if (!dataset.capabilities.customers) {
      return { available: false, reason: "This dataset has no customer column. Map a customer ID column when uploading to unlock customer analytics." };
    }
    const first = new Map<string, string>();
    for (const r of sliced.scoped) if (r.customerId && !first.has(r.customerId)) first.set(r.customerId, r.date);

    const stats = (rows: RawRow[]) => {
      const m = new Map<string, { orders: number; revenue: number }>();
      rows.forEach((r) => {
        if (!r.customerId) return;
        const e = m.get(r.customerId) ?? { orders: 0, revenue: 0 };
        e.orders += 1;
        e.revenue += r.revenue;
        m.set(r.customerId, e);
      });
      return m;
    };
    const curStats = stats(sliced.current);
    const prevStats = sliced.previous ? stats(sliced.previous) : null;
    const total = curStats.size;
    const newCount = [...curStats.keys()].filter((id) => (first.get(id) ?? "") >= sliced.range.from).length;
    const revenue = sliced.current.reduce((s, r) => s + r.revenue, 0);
    const prevRevenue = sliced.previous?.reduce((s, r) => s + r.revenue, 0);
    const perCustomer = total ? revenue / total : 0;
    const prevPerCustomer = prevStats && prevStats.size ? (prevRevenue ?? 0) / prevStats.size : null;

    const perBucket = new Map<string, Set<string>>();
    sliced.current.forEach((r) => {
      if (!r.customerId) return;
      const key = bucketKey(r.date, filters.groupBy);
      const set = perBucket.get(key) ?? new Set<string>();
      set.add(r.customerId);
      perBucket.set(key, set);
    });
    const newVsReturning = [...perBucket.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([date, ids]) => {
      const fresh = [...ids].filter((id) => bucketKey(first.get(id) ?? "", filters.groupBy) === date).length;
      return { date, newCustomers: fresh, returningCustomers: ids.size - fresh };
    });

    const bins = ["1 order", "2 orders", "3 orders", "4 orders", "5 orders", "6+ orders"].map((label) => ({ label, count: 0 }));
    const segDefs = [
      { name: "Champions", description: "6 or more orders", test: (n: number) => n >= 6 },
      { name: "Loyal", description: "3–5 orders", test: (n: number) => n >= 3 && n <= 5 },
      { name: "Returning", description: "2 orders", test: (n: number) => n === 2 },
      { name: "One-time", description: "1 order", test: (n: number) => n === 1 },
    ];
    const segments = segDefs.map((d) => ({ name: d.name, description: d.description, customers: 0, revenue: 0, share: 0 }));
    curStats.forEach((v) => {
      bins[Math.min(v.orders, 6) - 1].count += 1;
      const idx = segDefs.findIndex((d) => d.test(v.orders));
      segments[idx].customers += 1;
      segments[idx].revenue += v.revenue;
    });
    segments.forEach((s) => (s.share = total ? (s.customers / total) * 100 : 0));

    const regionMap = new Map<string, Set<string>>();
    sliced.current.forEach((r) => {
      if (!r.customerId) return;
      const key = r.region ?? r.category;
      const set = regionMap.get(key) ?? new Set<string>();
      set.add(r.customerId);
      regionMap.set(key, set);
    });
    const distribution = [...regionMap.entries()].map(([name, ids]) => ({ name, value: ids.size, share: total ? (ids.size / total) * 100 : 0 })).sort((a, b) => b.value - a.value);

    return {
      available: true,
      data: {
        kpis: [
          kpi("customers", "Total customers", total, "number", pctChange(total, prevStats?.size)),
          kpi("new", "New customers", newCount, "number", null),
          kpi("returning", "Returning customers", total - newCount, "number", null),
          kpi("rpc", "Revenue per customer", perCustomer, "currency", pctChange(perCustomer, prevPerCustomer)),
        ],
        newVsReturning,
        distribution,
        frequency: bins,
        segments,
      },
    };
  },

  async getFinance(datasetId: string, filters: AnalyticsFilters): Promise<FinanceResponse> {
    await delay();
    const { dataset, sliced } = await load(datasetId, filters);
    if (!dataset.capabilities.cost) {
      return { available: false, reason: "This dataset has no cost column, so profit and margin cannot be calculated. Map a cost column when uploading to unlock financial analytics." };
    }
    const cur = totals(sliced.current);
    const prev = sliced.previous ? totals(sliced.previous) : null;
    const margins = marginsByCategory(sliced.current);
    const totalProfit = margins.reduce((s, m) => s + m.profit, 0);
    return {
      available: true,
      data: {
        kpis: [
          kpi("revenue", "Revenue", cur.revenue, "currency", pctChange(cur.revenue, prev?.revenue)),
          kpi("cost", "Total cost", cur.cost ?? 0, "currency", pctChange(cur.cost ?? 0, prev?.cost), { inverse: true }),
          ...profitKpis(cur, prev),
        ],
        trend: timeSeries(sliced.current, filters.groupBy),
        categoryMargins: margins
          .map((m) => ({ name: m.name, value: Number(m.value.toFixed(1)), share: totalProfit ? (m.profit / totalProfit) * 100 : 0, secondary: m.profit }))
          .sort((a, b) => b.value - a.value),
      },
    };
  },

  async getInsights(datasetId: string, filters: AnalyticsFilters): Promise<Insight[]> {
    await delay();
    const { dataset, sliced } = await load(datasetId, filters);
    return buildInsights(sliced, dataset, filters);
  },

  async getExplorerData(datasetId: string): Promise<ExplorerData> {
    await delay();
    const { dataset, rows } = await load(datasetId, { datePreset: "all", comparison: "none", groupBy: "month", categories: [], regions: [] });
    const caps = dataset.capabilities;
    const columns: ExplorerColumn[] = [
      { key: "orderId", label: "Order ID", type: "string" },
      { key: "date", label: "Date", type: "date" },
      { key: "product", label: "Product", type: "string" },
      { key: "category", label: "Category", type: "string" },
      ...(caps.regions ? [{ key: "region", label: "Region", type: "string" as const }] : []),
      ...(caps.customers ? [{ key: "customerId", label: "Customer", type: "string" as const }] : []),
      { key: "quantity", label: "Quantity", type: "number" },
      { key: "unitPrice", label: "Unit price", type: "number", format: "currency" },
      { key: "revenue", label: "Revenue", type: "number", format: "currency" },
      ...(caps.cost ? [{ key: "cost", label: "Cost", type: "number" as const, format: "currency" as const }] : []),
    ];
    return {
      columns,
      rows: rows.map((r) => Object.fromEntries(columns.map((c) => [c.key, r[c.key as keyof RawRow] ?? null])) as ExplorerRow),
    };
  },
};
