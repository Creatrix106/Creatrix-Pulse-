/**
 * MOCK BACKEND ENGINE – lives outside presentation code on purpose.
 * Generates deterministic transaction rows and aggregates them into the same
 * response shapes the real backend must return (see /types/analytics.ts).
 * Delete `services/mock` once the real API is connected.
 */
import type { AnalyticsFilters, GroupBy } from "@/types/filters";
import type { BreakdownItem, ProductPerformance, TimeSeriesPoint } from "@/types/analytics";
import type { DatasetCapabilities } from "@/types/dataset";

export interface RawRow {
  orderId: string;
  date: string;
  productId: string;
  product: string;
  category: string;
  region?: string;
  customerId?: string;
  quantity: number;
  unitPrice: number;
  revenue: number;
  cost?: number;
}

const DATA_START = "2026-01-01";
export const DATA_END = "2026-10-31";

const CATALOG = [
  { id: "P-101", name: "Pulse Earbuds Pro", category: "Electronics", price: 6499, costRatio: 0.62, weight: 0.14 },
  { id: "P-102", name: "Orbit Smartwatch", category: "Electronics", price: 8999, costRatio: 0.66, weight: 0.07 },
  { id: "P-103", name: "Nimbus Speaker", category: "Electronics", price: 4299, costRatio: 0.6, weight: 0.06 },
  { id: "P-201", name: "Everyday Tee", category: "Apparel", price: 799, costRatio: 0.38, weight: 0.13 },
  { id: "P-202", name: "Trail Jacket", category: "Apparel", price: 3499, costRatio: 0.47, weight: 0.05 },
  { id: "P-203", name: "Studio Joggers", category: "Apparel", price: 1499, costRatio: 0.42, weight: 0.07 },
  { id: "P-301", name: "Aurora Table Lamp", category: "Home & Living", price: 1899, costRatio: 0.5, weight: 0.06 },
  { id: "P-302", name: "Weave Throw Blanket", category: "Home & Living", price: 1299, costRatio: 0.44, weight: 0.06 },
  { id: "P-303", name: "Ceramic Brew Set", category: "Home & Living", price: 2199, costRatio: 0.52, weight: 0.05 },
  { id: "P-401", name: "Glow Serum", category: "Personal Care", price: 999, costRatio: 0.3, weight: 0.09 },
  { id: "P-402", name: "Herbal Shampoo", category: "Personal Care", price: 449, costRatio: 0.34, weight: 0.08 },
  { id: "P-501", name: "Leather Daily Wallet", category: "Accessories", price: 1199, costRatio: 0.41, weight: 0.05 },
  { id: "P-502", name: "Canvas Tote", category: "Accessories", price: 699, costRatio: 0.36, weight: 0.04 },
  { id: "P-503", name: "Everyday Backpack", category: "Accessories", price: 2299, costRatio: 0.55, weight: 0.05 },
];

const REGIONS = [
  { name: "North", weight: 0.3 },
  { name: "South", weight: 0.28 },
  { name: "West", weight: 0.25 },
  { name: "East", weight: 0.17 },
];

/* ---------------------------------- dates --------------------------------- */

const DAY = 86_400_000;
const toDate = (iso: string) => new Date(`${iso}T00:00:00Z`);
export const addDays = (iso: string, n: number) => new Date(toDate(iso).getTime() + n * DAY).toISOString().slice(0, 10);
export const daysBetween = (a: string, b: string) => Math.round((toDate(b).getTime() - toDate(a).getTime()) / DAY);

export function bucketKey(date: string, groupBy: GroupBy): string {
  if (groupBy === "day") return date;
  if (groupBy === "month") return `${date.slice(0, 7)}-01`;
  const dow = (toDate(date).getUTCDay() + 6) % 7; // Monday start
  return addDays(date, -dow);
}

/* ------------------------------- generation ------------------------------- */

function hashSeed(input: string): number {
  let h = 2166136261;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pickWeighted<T extends { weight: number }>(items: T[], rand: () => number): T {
  let r = rand() * items.reduce((s, i) => s + i.weight, 0);
  for (const item of items) {
    r -= item.weight;
    if (r <= 0) return item;
  }
  return items[items.length - 1];
}

const rowCache = new Map<string, RawRow[]>();

export function getRows(seedKey: string, caps: DatasetCapabilities): RawRow[] {
  const cacheKey = `${seedKey}|${caps.customers}|${caps.cost}|${caps.regions}`;
  const cached = rowCache.get(cacheKey);
  if (cached) return cached;

  const rand = mulberry32(hashSeed(seedKey));
  const rows: RawRow[] = [];
  const total = daysBetween(DATA_START, DATA_END) + 1;
  const dowFactor = [1.15, 0.9, 0.9, 0.95, 1, 1.1, 1.25]; // Sun..Sat
  const customerPool: { id: string; region: string }[] = [];
  let orderNo = 10000;

  for (let i = 0; i < total; i++) {
    const date = addDays(DATA_START, i);
    const d = toDate(date);
    const month = d.getUTCMonth();
    let factor = (3.4 + (3.2 * i) / total) * dowFactor[d.getUTCDay()];
    if (month === 9) factor *= 1.25; // festive season
    if (date >= "2026-08-15" && date <= "2026-08-17") factor *= 2.6; // campaign spike
    if (date >= "2026-04-10" && date <= "2026-04-12") factor *= 0.35; // outage dip
    const orders = Math.max(0, Math.round(factor + (rand() - 0.5) * 3));

    for (let o = 0; o < orders; o++) {
      const product = pickWeighted(CATALOG, rand);
      const quantity = 1 + (rand() < 0.25 ? 1 : 0) + (rand() < 0.08 ? 2 : 0);
      const unitPrice = Math.round(product.price * (0.92 + rand() * 0.12));
      const revenue = unitPrice * quantity;
      const row: RawRow = {
        orderId: `ORD-${++orderNo}`,
        date,
        productId: product.id,
        product: product.name,
        category: product.category,
        quantity,
        unitPrice,
        revenue,
      };
      if (caps.cost) row.cost = Math.round(revenue * product.costRatio * (0.96 + rand() * 0.08));
      if (caps.customers) {
        const returning = customerPool.length > 20 && rand() < 0.5;
        if (returning) {
          const c = customerPool[Math.floor(Math.pow(rand(), 1.6) * customerPool.length)];
          row.customerId = c.id;
          if (caps.regions) row.region = c.region;
        } else {
          const c = { id: `C-${String(customerPool.length + 1).padStart(4, "0")}`, region: pickWeighted(REGIONS, rand).name };
          customerPool.push(c);
          row.customerId = c.id;
          if (caps.regions) row.region = c.region;
        }
      } else if (caps.regions) {
        row.region = pickWeighted(REGIONS, rand).name;
      }
      rows.push(row);
    }
  }
  rowCache.set(cacheKey, rows);
  return rows;
}

export function listDimensions(rows: RawRow[]): { categories: string[]; regions: string[] } {
  return {
    categories: [...new Set(rows.map((r) => r.category))].sort(),
    regions: [...new Set(rows.flatMap((r) => (r.region ? [r.region] : [])))].sort(),
  };
}

/* -------------------------------- filtering ------------------------------- */

export interface SlicedRows {
  current: RawRow[];
  previous: RawRow[] | null;
  range: { from: string; to: string };
  /** All rows matching category/region filters regardless of date. */
  scoped: RawRow[];
}

export function sliceRows(rows: RawRow[], filters: AnalyticsFilters): SlicedRows {
  const min = rows[0]?.date ?? DATA_START;
  const max = rows[rows.length - 1]?.date ?? DATA_END;
  const scoped = rows.filter(
    (r) =>
      (filters.categories.length === 0 || filters.categories.includes(r.category)) &&
      (filters.regions.length === 0 || (r.region !== undefined && filters.regions.includes(r.region))),
  );

  let from = min;
  let to = max;
  const days = { last_30d: 30, last_90d: 90, last_180d: 180 }[filters.datePreset as "last_30d" | "last_90d" | "last_180d"];
  if (days) from = addDays(max, -(days - 1));
  else if (filters.datePreset === "ytd") from = `${max.slice(0, 4)}-01-01`;
  else if (filters.datePreset === "custom" && filters.dateFrom && filters.dateTo) {
    from = filters.dateFrom;
    to = filters.dateTo;
  }

  const current = scoped.filter((r) => r.date >= from && r.date <= to);
  let previous: RawRow[] | null = null;
  if (filters.comparison === "previous_period" && filters.datePreset !== "all") {
    const len = daysBetween(from, to) + 1;
    const prevTo = addDays(from, -1);
    const prevFrom = addDays(from, -len);
    const prevRows = scoped.filter((r) => r.date >= prevFrom && r.date <= prevTo);
    previous = prevRows.length > 0 ? prevRows : null;
  }
  return { current, previous, range: { from, to }, scoped };
}

/* ------------------------------- aggregation ------------------------------ */

export interface Totals {
  revenue: number;
  orders: number;
  units: number;
  aov: number;
  cost: number | null;
  profit: number | null;
  margin: number | null;
}

export function totals(rows: RawRow[]): Totals {
  const revenue = rows.reduce((s, r) => s + r.revenue, 0);
  const orders = new Set(rows.map((r) => r.orderId)).size;
  const units = rows.reduce((s, r) => s + r.quantity, 0);
  const hasCost = rows.length > 0 && rows.every((r) => r.cost !== undefined);
  const cost = hasCost ? rows.reduce((s, r) => s + (r.cost ?? 0), 0) : null;
  const profit = cost === null ? null : revenue - cost;
  return {
    revenue,
    orders,
    units,
    aov: orders ? revenue / orders : 0,
    cost,
    profit,
    margin: profit === null || revenue === 0 ? null : (profit / revenue) * 100,
  };
}

export const pctChange = (cur: number, prev: number | null | undefined): number | null =>
  prev === null || prev === undefined || prev === 0 ? null : ((cur - prev) / prev) * 100;

export function timeSeries(rows: RawRow[], groupBy: GroupBy): TimeSeriesPoint[] {
  const buckets = new Map<string, RawRow[]>();
  for (const r of rows) {
    const key = bucketKey(r.date, groupBy);
    const list = buckets.get(key);
    if (list) list.push(r);
    else buckets.set(key, [r]);
  }
  return [...buckets.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, list]) => {
      const t = totals(list);
      const point: TimeSeriesPoint = { date, revenue: t.revenue, orders: t.orders, units: t.units, aov: Math.round(t.aov) };
      if (t.cost !== null && t.profit !== null && t.margin !== null) {
        point.cost = t.cost;
        point.profit = t.profit;
        point.margin = Number(t.margin.toFixed(1));
      }
      return point;
    });
}

export function breakdown(rows: RawRow[], keyOf: (r: RawRow) => string | undefined, previous: RawRow[] | null): BreakdownItem[] {
  const sum = (list: RawRow[]) => {
    const map = new Map<string, { revenue: number; units: number }>();
    for (const r of list) {
      const key = keyOf(r);
      if (!key) continue;
      const entry = map.get(key) ?? { revenue: 0, units: 0 };
      entry.revenue += r.revenue;
      entry.units += r.quantity;
      map.set(key, entry);
    }
    return map;
  };
  const cur = sum(rows);
  const prev = previous ? sum(previous) : null;
  const total = [...cur.values()].reduce((s, v) => s + v.revenue, 0);
  return [...cur.entries()]
    .map(([name, v]) => ({
      name,
      value: v.revenue,
      share: total ? (v.revenue / total) * 100 : 0,
      secondary: v.units,
      change: prev ? pctChange(v.revenue, prev.get(name)?.revenue) : null,
    }))
    .sort((a, b) => b.value - a.value);
}

export function productPerformance(rows: RawRow[], previous: RawRow[] | null): ProductPerformance[] {
  const group = (list: RawRow[]) => {
    const map = new Map<string, { name: string; category: string; revenue: number; units: number; orders: Set<string>; cost: number; hasCost: boolean }>();
    for (const r of list) {
      const e = map.get(r.productId) ?? { name: r.product, category: r.category, revenue: 0, units: 0, orders: new Set<string>(), cost: 0, hasCost: true };
      e.revenue += r.revenue;
      e.units += r.quantity;
      e.orders.add(r.orderId);
      if (r.cost === undefined) e.hasCost = false;
      else e.cost += r.cost;
      map.set(r.productId, e);
    }
    return map;
  };
  const cur = group(rows);
  const prev = previous ? group(previous) : null;
  const total = [...cur.values()].reduce((s, v) => s + v.revenue, 0);
  return [...cur.entries()]
    .map(([id, v]) => ({
      id,
      name: v.name,
      category: v.category,
      revenue: v.revenue,
      units: v.units,
      orders: v.orders.size,
      share: total ? (v.revenue / total) * 100 : 0,
      change: prev ? pctChange(v.revenue, prev.get(id)?.revenue) : null,
      margin: v.hasCost && v.revenue ? ((v.revenue - v.cost) / v.revenue) * 100 : null,
    }))
    .sort((a, b) => b.revenue - a.revenue);
}
