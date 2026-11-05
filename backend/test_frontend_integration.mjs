// Comprehensive Frontend-to-Backend Integration Test using Node.js native fetch & FormData
import { Blob } from "buffer";

const BASE_URL = "http://127.0.0.1:8000/api";
let sessionCookie = "";

function parseCookie(res) {
  const raw = res.headers.get("set-cookie");
  if (raw) {
    const match = raw.match(/session=([^;]+)/);
    if (match) {
      sessionCookie = `session=${match[1]}`;
    }
  }
}

async function request(path, options = {}) {
  const url = `${BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = { ...options.headers };
  if (sessionCookie) {
    headers["Cookie"] = sessionCookie;
  }
  if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }
  const res = await fetch(url, { ...options, headers });
  parseCookie(res);
  if (res.status === 204) return { status: 204, data: null };
  const data = await res.json().catch(() => null);
  return { status: res.status, ok: res.ok, data, headers: res.headers };
}

async function runTests() {
  console.log("============================================================");
  console.log("  FRONTEND HTTP CLIENT -> LIVE BACKEND TEST SUITE");
  console.log("============================================================");

  let passed = 0;
  let failed = 0;

  async function test(name, fn) {
    try {
      await fn();
      console.log(`  [PASS] ${name}`);
      passed++;
    } catch (err) {
      console.error(`  [FAIL] ${name}:`, err.message);
      failed++;
    }
  }

  // 1. Auth Flow
  console.log("\n--- 1. Authentication Service ---");
  await test("POST /auth/login with valid credentials", async () => {
    const res = await request("/auth/login", {
      method: "POST",
      body: { email: "admin@creatrix.io", password: "password123" },
    });
    if (!res.ok) throw new Error(`Status ${res.status}: ${JSON.stringify(res.data)}`);
    if (!res.data.id || res.data.role !== "admin") throw new Error("Invalid user response shape");
    if (!sessionCookie) throw new Error("Session cookie was not set");
  });

  await test("GET /auth/me with session cookie", async () => {
    const res = await request("/auth/me");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (res.data.email !== "admin@creatrix.io") throw new Error("Email mismatch in /auth/me");
  });

  await test("POST /auth/register", async () => {
    const uniqueEmail = `test_${Date.now()}@creatrix.io`;
    const res = await request("/auth/register", {
      method: "POST",
      body: { name: "Test User", email: uniqueEmail, password: "password123" },
    });
    if (res.status !== 201) throw new Error(`Status ${res.status}`);
    if (res.data.email !== uniqueEmail) throw new Error("Email mismatch in /auth/register");
  });

  // 2. Datasets Flow
  console.log("\n--- 2. Dataset Service ---");
  await test("GET /datasets returns array of datasets", async () => {
    const res = await request("/datasets");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (!Array.isArray(res.data)) throw new Error("Expected array of datasets");
    if (res.data.length < 3) throw new Error("Expected at least 3 datasets");
    const retail = res.data.find((d) => d.id === "demo-retail");
    if (!retail || retail.status !== "ready") throw new Error("demo-retail not found or not ready");
  });

  await test("GET /datasets/demo-retail details", async () => {
    const res = await request("/datasets/demo-retail");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (res.data.id !== "demo-retail") throw new Error("ID mismatch");
    if (!res.data.capabilities?.customers || !res.data.capabilities?.cost) {
      throw new Error("Capabilities missing");
    }
  });

  await test("GET /datasets/demo-retail/processing status", async () => {
    const res = await request("/datasets/demo-retail/processing");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (res.data.status !== "ready" || res.data.stages.length !== 5) {
      throw new Error("Invalid processing status response");
    }
  });

  let uploadedDatasetId = null;
  await test("POST /datasets multipart file upload", async () => {
    const csvData = `Date,Product,Category,Quantity,Price,Revenue,Cost,Customer ID,Region
2026-03-01,Alpha Widget,Hardware,2,500,1000,500,C-01,North
2026-03-02,Beta Widget,Hardware,1,1500,1500,750,C-02,South`;
    const form = new FormData();
    const blob = new Blob([csvData], { type: "text/csv" });
    form.append("file", blob, "test_upload.csv");
    form.append(
      "mapping",
      JSON.stringify({
        date: "Date",
        product: "Product",
        category: "Category",
        quantity: "Quantity",
        revenue: "Revenue",
        cost: "Cost",
        customer: "Customer ID",
        region: "Region",
      })
    );

    const res = await request("/datasets", {
      method: "POST",
      body: form,
    });
    if (res.status !== 201) throw new Error(`Status ${res.status}: ${JSON.stringify(res.data)}`);
    if (!res.data.datasetId) throw new Error("Missing datasetId in upload response");
    uploadedDatasetId = res.data.datasetId;
  });

  // 3. Analytics Flow
  console.log("\n--- 3. Analytics Service ---");
  await test("GET /datasets/demo-retail/analytics/overview", async () => {
    const res = await request("/datasets/demo-retail/analytics/overview?datePreset=all&comparison=none&groupBy=month");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (!Array.isArray(res.data.kpis) || res.data.kpis.length === 0) throw new Error("Missing KPIs");
    if (!Array.isArray(res.data.revenueTrend) || res.data.revenueTrend.length === 0) throw new Error("Missing revenueTrend");
    if (!Array.isArray(res.data.topProducts) || res.data.topProducts.length === 0) throw new Error("Missing topProducts");
    if (!Array.isArray(res.data.categories) || res.data.categories.length === 0) throw new Error("Missing categories");
    if (!Array.isArray(res.data.insights) || res.data.insights.length === 0) throw new Error("Missing insights");
  });

  await test("GET /datasets/demo-retail/analytics/sales", async () => {
    const res = await request("/datasets/demo-retail/analytics/sales?datePreset=last_90d&comparison=previous_period&groupBy=week");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (!Array.isArray(res.data.trend)) throw new Error("Missing sales trend");
    if (!Array.isArray(res.data.previousTrend)) throw new Error("Missing previousTrend when comparison=previous_period");
    if (!Array.isArray(res.data.categoryTrend)) throw new Error("Missing categoryTrend");
  });

  await test("GET /datasets/demo-retail/analytics/products", async () => {
    const res = await request("/datasets/demo-retail/analytics/products?datePreset=all");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (!Array.isArray(res.data.top) || res.data.top.length === 0) throw new Error("Missing top products");
    if (!Array.isArray(res.data.low) || res.data.low.length === 0) throw new Error("Missing low products");
    if (!Array.isArray(res.data.all) || res.data.all.length === 0) throw new Error("Missing all products");
  });

  await test("GET /datasets/demo-retail/analytics/customers (available: true)", async () => {
    const res = await request("/datasets/demo-retail/analytics/customers?datePreset=all");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (res.data.available !== true) throw new Error("Expected available: true for demo-retail");
    if (!res.data.data.kpis || !Array.isArray(res.data.data.segments)) throw new Error("Invalid CustomersData");
  });

  await test("GET /datasets/demo-wholesale/analytics/customers (available: false capability guard)", async () => {
    const res = await request("/datasets/demo-wholesale/analytics/customers");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (res.data.available !== false) throw new Error("Expected available: false for demo-wholesale");
    if (!res.data.reason) throw new Error("Expected human-readable reason");
  });

  await test("GET /datasets/demo-retail/analytics/finance (available: true)", async () => {
    const res = await request("/datasets/demo-retail/analytics/finance?datePreset=all");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (res.data.available !== true) throw new Error("Expected available: true for demo-retail");
    if (!res.data.data.kpis || !Array.isArray(res.data.data.categoryMargins)) throw new Error("Invalid FinanceData");
  });

  await test("GET /datasets/demo-marketplace/analytics/finance (available: false capability guard)", async () => {
    const res = await request("/datasets/demo-marketplace/analytics/finance");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (res.data.available !== false) throw new Error("Expected available: false for demo-marketplace");
    if (!res.data.reason) throw new Error("Expected human-readable reason");
  });

  await test("GET /datasets/demo-retail/records (ExplorerData)", async () => {
    const res = await request("/datasets/demo-retail/records?limit=20&offset=0");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (!Array.isArray(res.data.columns) || !Array.isArray(res.data.rows)) throw new Error("Invalid ExplorerData shape");
    if (res.data.rows.length !== 20) throw new Error(`Expected 20 rows, got ${res.data.rows.length}`);
  });

  // 4. Reports Flow
  console.log("\n--- 4. Reports Service ---");
  await test("POST /datasets/demo-retail/reports/preview", async () => {
    const res = await request("/datasets/demo-retail/reports/preview", {
      method: "POST",
      body: {
        title: "Executive Q4 Review",
        metrics: ["revenue", "orders", "units", "profit"],
        datePreset: "last_90d",
        format: "pdf",
      },
    });
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (!res.data.title || !Array.isArray(res.data.summary) || !Array.isArray(res.data.rows)) {
      throw new Error("Invalid ReportPreview shape");
    }
  });

  let reportId = null;
  await test("POST /datasets/demo-retail/reports compile PDF", async () => {
    const res = await request("/datasets/demo-retail/reports", {
      method: "POST",
      body: {
        title: "Executive Summary PDF",
        metrics: ["revenue", "profit", "orders"],
        datePreset: "all",
        format: "pdf",
      },
    });
    if (res.status !== 201) throw new Error(`Status ${res.status}`);
    if (!res.data.id || !res.data.downloadUrl) throw new Error("Missing reportId or downloadUrl");
    reportId = res.data.id;
  });

  await test("GET /datasets/demo-retail/reports history list", async () => {
    const res = await request("/datasets/demo-retail/reports");
    if (!res.ok) throw new Error(`Status ${res.status}`);
    if (!Array.isArray(res.data) || res.data.length === 0) throw new Error("Expected list of ReportRecord");
  });

  await test("GET report download artifact", async () => {
    const downloadPath = `/datasets/demo-retail/reports/${reportId}/download`;
    const res = await request(downloadPath);
    if (!res.ok) throw new Error(`Status ${res.status}`);
    const contentType = res.headers.get("content-type");
    if (contentType !== "application/pdf") throw new Error(`Unexpected content-type: ${contentType}`);
  });

  // 5. Cleanup
  console.log("\n--- 5. Cleanup ---");
  if (uploadedDatasetId) {
    await test("DELETE uploaded test dataset", async () => {
      const res = await request(`/datasets/${uploadedDatasetId}`, { method: "DELETE" });
      if (res.status !== 204) throw new Error(`Status ${res.status}`);
    });
  }

  await test("POST /auth/logout", async () => {
    const res = await request("/auth/logout", { method: "POST" });
    if (res.status !== 204) throw new Error(`Status ${res.status}`);
  });

  console.log("\n" + "=".repeat(60));
  console.log(`FRONTEND INTEGRATION SUMMARY: ${passed} passed, ${failed} failed`);
  console.log("=".repeat(60));

  if (failed > 0) process.exit(1);
}

runTests().catch((e) => {
  console.error(e);
  process.exit(1);
});
