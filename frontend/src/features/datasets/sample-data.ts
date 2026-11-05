const PRODUCTS: [string, string, number, number][] = [
  ["Pulse Earbuds Pro", "Electronics", 6499, 0.62],
  ["Everyday Tee", "Apparel", 799, 0.38],
  ["Aurora Table Lamp", "Home & Living", 1899, 0.5],
  ["Glow Serum", "Personal Care", 999, 0.3],
  ["Canvas Tote", "Accessories", 699, 0.36],
  ["Trail Jacket", "Apparel", 3499, 0.47],
];
const REGIONS = ["North", "South", "East", "West"];

/** Small deterministic CSV so users can try the upload flow without their own file. */
export function buildSampleCsv(rows = 90): string {
  const lines = ["Order ID,Order Date,Product,Category,Region,Customer ID,Quantity,Revenue,Cost"];
  for (let i = 0; i < rows; i++) {
    const [name, category, price, costRatio] = PRODUCTS[(i * 7) % PRODUCTS.length];
    const qty = 1 + ((i * 3) % 3);
    const day = new Date(Date.UTC(2026, 0, 1 + Math.floor((i * 300) / rows)));
    const revenue = price * qty;
    lines.push([`ORD-${20000 + i}`, day.toISOString().slice(0, 10), `"${name}"`, `"${category}"`, REGIONS[(i * 5) % 4], `C-${String(1 + ((i * 11) % 40)).padStart(4, "0")}`, qty, revenue, Math.round(revenue * costRatio)].join(","));
  }
  return lines.join("\n");
}

export function createSampleFile(): File {
  return new File([buildSampleCsv()], "sample_retail_sales.csv", { type: "text/csv" });
}
