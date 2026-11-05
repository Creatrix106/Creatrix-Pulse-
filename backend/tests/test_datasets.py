import json

def test_list_datasets(client):
    r = client.get("/api/v1/datasets")
    assert r.status_code == 200
    datasets = r.json()
    assert isinstance(datasets, list)
    assert len(datasets) >= 4
    ids = [d["id"] for d in datasets]
    assert "demo-retail" in ids
    assert "demo-marketplace" in ids
    assert "demo-wholesale" in ids
    assert "demo-failed" in ids

def test_get_dataset_detail(client):
    r = client.get("/api/v1/datasets/demo-retail")
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == "demo-retail"
    assert d["status"] == "ready"
    assert d["rowCount"] > 1000
    assert d["capabilities"]["customers"] is True
    assert d["capabilities"]["cost"] is True
    assert d["capabilities"]["regions"] is True

def test_get_dataset_not_found(client):
    r = client.get("/api/v1/datasets/non-existent-dataset-id")
    assert r.status_code == 404
    assert r.json()["code"] == "dataset_not_found"

def test_get_processing_status(client):
    r = client.get("/api/v1/datasets/demo-retail/processing")
    assert r.status_code == 200
    status = r.json()
    assert status["status"] == "ready"
    assert len(status["stages"]) == 5
    assert all(s["status"] == "complete" for s in status["stages"])

def test_get_failed_processing_status(client):
    r = client.get("/api/v1/datasets/demo-failed/processing")
    assert r.status_code == 200
    status = r.json()
    assert status["status"] == "failed"
    assert "message" in status
    assert "ISO dates" in status["message"]

def test_upload_and_delete_csv_dataset(client):
    csv_data = b"""Order ID,Invoice Date,Item Name,Dept,Qty,Line Total,Expense,Buyer,Zone
ORD-501,2026-03-01,Test Lamp,Home & Living,2,3000,1500,C-099,West
ORD-502,2026-03-02,Test Serum,Personal Care,1,999,350,C-100,North
"""
    files = {"file": ("sales_test.csv", csv_data, "text/csv")}
    mapping = {
        "orderId": "Order ID",
        "date": "Invoice Date",
        "product": "Item Name",
        "category": "Dept",
        "quantity": "Qty",
        "revenue": "Line Total",
        "cost": "Expense",
        "customer": "Buyer",
        "region": "Zone"
    }
    r = client.post("/api/v1/datasets", files=files, data={"mapping": json.dumps(mapping)})
    assert r.status_code == 201
    dataset_id = r.json()["datasetId"]

    # Verify preview
    prev_resp = client.get(f"/api/v1/datasets/{dataset_id}/preview")
    assert prev_resp.status_code == 200
    assert len(prev_resp.json()["headers"]) == 9

    # Verify detail
    detail_resp = client.get(f"/api/v1/datasets/{dataset_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["rowCount"] == 2
    assert detail_resp.json()["capabilities"]["cost"] is True
    assert detail_resp.json()["capabilities"]["customers"] is True

    # Purge dataset
    del_resp = client.delete(f"/api/v1/datasets/{dataset_id}")
    assert del_resp.status_code == 204

    # Ensure 404 after deletion
    check_resp = client.get(f"/api/v1/datasets/{dataset_id}")
    assert check_resp.status_code == 404
