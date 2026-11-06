import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import db
from app.db.seed import seed_all

import tests.test_auth as t_auth
import tests.test_datasets as t_datasets
import tests.test_analytics as t_analytics
import tests.test_insights as t_insights
import tests.test_reports as t_reports

def run_all_tests():
    import asyncio
    print("=" * 60)
    print("  CREATRIX PULSE BACKEND TEST SUITE")
    print("=" * 60)
    asyncio.run(db.init_db())
    asyncio.run(seed_all())

    client = TestClient(app)
    r = client.post("/api/v1/auth/login", json={"email": "admin@creatrix.io", "password": "password123"})
    token = r.json().get("access_token")
    auth_headers = {"Authorization": f"Bearer {token}"}

    modules = [
        ("Authentication & Security", t_auth, [
            ("Health check", lambda: t_auth.test_health(client)),
            ("Login success", lambda: t_auth.test_login_success(client)),
            ("Login invalid password", lambda: t_auth.test_login_invalid_password(client)),
            ("Login blocked user", lambda: t_auth.test_login_blocked_user(client)),
            ("Register & /me profile", lambda: t_auth.test_register_and_me(client)),
            ("Refresh token rotation", lambda: t_auth.test_refresh_token(client)),
            ("Logout revocation", lambda: t_auth.test_logout(client)),
        ]),
        ("Datasets & Ingestion", t_datasets, [
            ("List datasets", lambda: t_datasets.test_list_datasets(client)),
            ("Get dataset detail", lambda: t_datasets.test_get_dataset_detail(client)),
            ("Get dataset not found 404", lambda: t_datasets.test_get_dataset_not_found(client)),
            ("Get processing status ready", lambda: t_datasets.test_get_processing_status(client)),
            ("Get processing status failed", lambda: t_datasets.test_get_failed_processing_status(client)),
            ("Upload CSV and purge dataset", lambda: t_datasets.test_upload_and_delete_csv_dataset(client)),
        ]),
        ("Analytics Vector Engine", t_analytics, [
            ("Analytics overview & KPIs", lambda: t_analytics.test_analytics_overview(client)),
            ("Analytics sales trend & previous period", lambda: t_analytics.test_analytics_sales(client)),
            ("Analytics products rankings", lambda: t_analytics.test_analytics_products(client)),
            ("Customers capability available", lambda: t_analytics.test_analytics_customers_available(client)),
            ("Customers capability unavailable reason", lambda: t_analytics.test_analytics_customers_unavailable(client)),
            ("Finance capability available", lambda: t_analytics.test_analytics_finance_available(client)),
            ("Finance capability unavailable reason", lambda: t_analytics.test_analytics_finance_unavailable(client)),
            ("Records explorer pagination", lambda: t_analytics.test_records_explorer(client)),
        ]),
        ("Automated Insights Engine", t_insights, [
            ("Automated heuristic & anomaly insights", lambda: t_insights.test_insights_generation(client)),
            ("Dedicated insights endpoint", lambda: t_insights.test_insights_dedicated_endpoint(client)),
        ]),
        ("Reports & Streaming Exports", t_reports, [
            ("Report preview generation", lambda: t_reports.test_report_preview(client)),
            ("Report CSV generation & download stream", lambda: t_reports.test_report_generate_and_download_csv(client, auth_headers)),
            ("Report PDF generation & download stream", lambda: t_reports.test_report_generate_and_download_pdf(client, auth_headers)),
        ])
    ]

    total_passed = 0
    total_failed = 0
    start_time = time.time()

    for category, mod, tests_list in modules:
        print(f"\n--- {category} ---")
        for test_name, test_fn in tests_list:
            try:
                test_fn()
                print(f"  [PASS] {test_name}")
                total_passed += 1
            except Exception as e:
                print(f"  [FAIL] {test_name}: {e}")
                import traceback
                traceback.print_exc()
                total_failed += 1

    print("\n--- Regression suite (CORS, cookies, uploads, explorer, reports) ---")
    import pytest
    reg_rc = pytest.main([str(Path(__file__).resolve().parent / "tests" / "test_regressions.py"), "-q", "-p", "no:cacheprovider"])
    if reg_rc != 0:
        total_failed += 1
        print("  [FAIL] Regression suite (see pytest output above)")
    else:
        total_passed += 1
        print("  [PASS] Regression suite")

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"TEST SUMMARY: {total_passed} passed, {total_failed} failed in {elapsed:.2f}s")
    print("=" * 60)

    if total_failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
