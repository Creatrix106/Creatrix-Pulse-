def test_report_preview(client):
    cfg = {
        "title": "Quarterly Performance",
        "metrics": ["revenue", "orders", "units"],
        "datePreset": "last_90d",
        "format": "csv"
    }
    r = client.post("/api/v1/datasets/demo-retail/reports/preview", json=cfg)
    assert r.status_code == 200
    prev = r.json()
    assert prev["title"] == "Quarterly Performance"
    assert len(prev["summary"]) == 3
    assert len(prev["columns"]) == 4  # month + 3 metrics
    assert len(prev["rows"]) > 0

def test_report_generate_and_download_csv(client, auth_headers):
    cfg = {
        "title": "CSV Audit Report",
        "metrics": ["revenue", "profit"],
        "datePreset": "all",
        "format": "csv"
    }
    r = client.post("/api/v1/datasets/demo-retail/reports", json=cfg, headers=auth_headers)
    assert r.status_code == 201
    rec = r.json()
    assert rec["format"] == "csv"
    assert rec["rowCount"] > 0
    report_id = rec["id"]

    # Download
    dl_resp = client.get(f"/api/v1/datasets/demo-retail/reports/{report_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"].startswith("text/csv")
    assert "Revenue" in dl_resp.text

def test_report_generate_and_download_pdf(client, auth_headers):
    cfg = {
        "title": "Executive PDF Deck",
        "metrics": ["revenue", "orders", "units", "profit"],
        "datePreset": "all",
        "format": "pdf"
    }
    r = client.post("/api/v1/datasets/demo-retail/reports", json=cfg, headers=auth_headers)
    assert r.status_code == 201
    rec = r.json()
    assert rec["format"] == "pdf"
    report_id = rec["id"]

    # Download
    dl_resp = client.get(f"/api/v1/datasets/demo-retail/reports/{report_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "application/pdf"
    assert dl_resp.content.startswith(b"%PDF")
