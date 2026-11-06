"""Regression tests for bugs found while wiring the backend to the frontend."""
import io
import json
import uuid

import pandas as pd
from fastapi.testclient import TestClient

ORIGIN = "http://localhost:3000"
FULL_MAPPING = {"orderId": "Order ID", "date": "Order Date", "product": "Product", "category": "Category",
                "region": "Region", "customer": "Customer ID", "quantity": "Quantity", "revenue": "Revenue", "cost": "Cost"}
SAMPLE = (
    "Order ID,Order Date,Product,Category,Region,Customer ID,Quantity,Revenue,Cost\n"
    "ORD-1,2026-01-01,Pulse Earbuds,Electronics,North,C-1,1,6499,4000\n"
    "ORD-2,2026-01-02,Everyday Tee,Apparel,South,C-2,2,1598,990\n"
    "ORD-3,2026-01-03,Pulse Earbuds,Electronics,East,C-1,1,6499,4000\n"
)


def _upload(client, content: bytes, filename="sample.csv", mapping=None):
    data = {"mapping": json.dumps(mapping)} if mapping is not None else {}
    return client.post("/api/v1/datasets", files={"file": (filename, content, "text/csv")}, data=data)


def _delete(client, dataset_id):
    client.delete(f"/api/v1/datasets/{dataset_id}")


# ------------------------------------------------------------------ CORS / errors

def test_cors_uses_explicit_origin_with_credentials(client):
    """A wildcard origin makes browsers reject credentialed requests (the frontend uses cookies)."""
    pre = client.options("/api/v1/auth/login", headers={
        "Origin": ORIGIN, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    assert pre.headers["access-control-allow-origin"] == ORIGIN
    assert pre.headers["access-control-allow-credentials"] == "true"
    simple = client.get("/health", headers={"Origin": ORIGIN})
    assert simple.headers["access-control-allow-origin"] == ORIGIN


def test_unknown_route_uses_frontend_error_shape(client):
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == "not_found" and "message" in body and "detail" not in body


def test_validation_error_uses_frontend_error_shape(client):
    r = client.get("/api/v1/datasets/demo-retail/analytics/overview?datePreset=bogus")
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_error" and "datePreset" in body["message"]


def test_bad_custom_date_is_a_400_not_a_500(client):
    r = client.get("/api/v1/datasets/demo-retail/analytics/overview?datePreset=custom&dateFrom=garbage&dateTo=2026-01-01")
    assert r.status_code == 400 and r.json()["code"] == "invalid_date"


def test_server_errors_are_generic_json_with_cors_headers(monkeypatch):
    from app.main import app
    from app.services.analytics_service import AnalyticsService

    async def boom(*a, **k):
        raise RuntimeError("secret internals")

    monkeypatch.setattr(AnalyticsService, "get_overview", boom)
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/v1/datasets/demo-retail/analytics/overview", headers={"Origin": ORIGIN})
    assert r.status_code == 500
    assert r.json()["code"] == "internal_server_error"
    assert "secret internals" not in r.text
    assert r.headers.get("access-control-allow-origin") == ORIGIN  # else the browser reports a network error


# ------------------------------------------------------------------ auth

def test_register_sets_session_cookie(client):
    r = client.post("/api/v1/auth/register", json={
        "name": "Cookie Tester", "email": f"c_{uuid.uuid4().hex[:6]}@example.com", "password": "password123"})
    assert r.status_code == 201
    assert any(c.lower().startswith("session=") for c in r.headers.get_list("set-cookie"))


def test_logout_clears_session_cookie(client):
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 204
    cookies = [c.lower() for c in r.headers.get_list("set-cookie")]
    assert any(c.startswith("session=") and "max-age=0" in c for c in cookies)


def test_login_does_not_create_unknown_accounts(client):
    r = client.post("/api/v1/auth/login", json={"email": f"nobody_{uuid.uuid4().hex[:6]}@example.com", "password": "password123"})
    assert r.status_code == 401 and r.json()["code"] == "invalid_credentials"


def test_refresh_token_is_not_accepted_as_access_token(client):
    reg = client.post("/api/v1/auth/register", json={
        "name": "Token Tester", "email": f"t_{uuid.uuid4().hex[:6]}@example.com", "password": "password123"}).json()
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {reg['refresh_token']}"})
    assert r.status_code == 401
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": reg["access_token"]})
    assert r.status_code == 401


def test_swagger_form_login_endpoint(client):
    r = client.post("/api/v1/auth/token", data={"username": "admin@creatrix.io", "password": "password123"})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"


def test_stale_cookie_does_not_lock_the_frontend_out(client):
    client.cookies.set("session", "not.a.jwt")
    assert client.get("/api/v1/datasets").status_code == 200  # demo mode: treated as signed out


# ------------------------------------------------------------------ explorer

def test_explorer_returns_every_row_by_default(client):
    r = client.get("/api/v1/datasets/demo-retail/records")
    body = r.json()
    assert body["total"] > 200
    assert len(body["rows"]) == body["total"]  # the UI sorts/filters/paginates client-side
    assert body["meta"]["truncated"] is False


def test_explorer_limit_offset_and_sort_still_work(client):
    body = client.get("/api/v1/datasets/demo-retail/records?limit=3&offset=1&sortBy=revenue").json()
    assert len(body["rows"]) == 3 and body["meta"]["truncated"] is True
    full = client.get("/api/v1/datasets/demo-retail/records?sortBy=revenue").json()["rows"]
    assert [r["orderId"] for r in body["rows"]] == [r["orderId"] for r in full[1:4]]


# ------------------------------------------------------------------ upload

def test_upload_sample_file_end_to_end(client):
    r = _upload(client, SAMPLE.encode(), mapping=FULL_MAPPING)
    assert r.status_code == 201
    ds_id = r.json()["datasetId"]
    try:
        ds = client.get(f"/api/v1/datasets/{ds_id}").json()
        assert ds["status"] == "ready" and ds["rowCount"] == 3
        assert ds["capabilities"] == {"customers": True, "cost": True, "regions": True}
        assert "errorMessage" not in ds and all(c.get("mappedTo") for c in ds["columns"])
        assert client.get(f"/api/v1/datasets/{ds_id}/processing").json()["status"] == "ready"
        ov = client.get(f"/api/v1/datasets/{ds_id}/analytics/overview").json()
        assert [k["value"] for k in ov["kpis"] if k["id"] == "revenue"] == [14596.0]
    finally:
        _delete(client, ds_id)
    assert client.get(f"/api/v1/datasets/{ds_id}").status_code == 404


def test_upload_does_not_fabricate_data_for_unrecognised_columns(client):
    before = {d["id"] for d in client.get("/api/v1/datasets").json()}
    r = _upload(client, b"Sale Dt,Item Desc,Net Amt\n2026-03-01,Widget,100\n", mapping={})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "missing_columns" and "Revenue" in body["message"]
    assert {d["id"] for d in client.get("/api/v1/datasets").json()} == before  # nothing half-created


def test_upload_rejects_unreadable_dates(client):
    r = _upload(client, b"Date,Product,Revenue\nx,A,1\ny,B,2\n", mapping={"date": "Date", "product": "Product", "revenue": "Revenue"})
    assert r.status_code == 422 and r.json()["code"] == "invalid_dates"


def test_upload_respects_the_users_mapping(client):
    csv = b"Date,Product,Revenue,Customer ID\n2026-03-01,A,100,C1\n"
    r = _upload(client, csv, mapping={"date": "Date", "product": "Product", "revenue": "Revenue"})  # customer left unmapped
    ds_id = r.json()["datasetId"]
    try:
        assert client.get(f"/api/v1/datasets/{ds_id}").json()["capabilities"]["customers"] is False
    finally:
        _delete(client, ds_id)


def test_upload_dayfirst_dates_and_unique_product_ids(client):
    csv = ("Date,Product,Revenue\n05/03/2026,Premium Wireless Headphones Black,10\n"
           "13/03/2026,Premium Wireless Headphones White,20\n14/03/2026,चाय पत्ती,5\n").encode()
    ds_id = _upload(client, csv, mapping={"date": "Date", "product": "Product", "revenue": "Revenue"}).json()["datasetId"]
    try:
        rows = client.get(f"/api/v1/datasets/{ds_id}/records").json()["rows"]
        assert sorted(r["date"] for r in rows) == ["2026-03-05", "2026-03-13", "2026-03-14"]
        prods = client.get(f"/api/v1/datasets/{ds_id}/analytics/products").json()["all"]
        assert len({p["id"] for p in prods}) == 3
    finally:
        _delete(client, ds_id)


def test_upload_excel_with_real_dates_and_no_mapping(client):
    buf = io.BytesIO()
    pd.DataFrame({"Order Date": pd.to_datetime(["2026-04-01", "2026-04-02"]), "Item": ["A", "B"],
                  "Sales": [10.5, 20.0], "Order No": [1001.0, 1002.0]}).to_excel(buf, index=False)
    r = client.post("/api/v1/datasets", files={"file": ("sales.xlsx", buf.getvalue(), "application/vnd.ms-excel")})
    assert r.status_code == 201
    ds_id = r.json()["datasetId"]
    try:
        rows = client.get(f"/api/v1/datasets/{ds_id}/records").json()["rows"]
        assert sorted(x["orderId"] for x in rows) == ["1001", "1002"]
    finally:
        _delete(client, ds_id)


def test_upload_validation_errors(client):
    assert _upload(client, b"hello", filename="notes.txt").status_code == 415
    assert _upload(client, b"", filename="a.csv").status_code == 400
    bad = client.post("/api/v1/datasets", files={"file": ("a.csv", SAMPLE.encode(), "text/csv")}, data={"mapping": "{not json"})
    assert bad.status_code == 400 and bad.json()["code"] == "invalid_mapping"


def test_replace_keeps_old_dataset_if_new_upload_fails(client):
    first = _upload(client, SAMPLE.encode(), mapping=FULL_MAPPING).json()["datasetId"]
    try:
        r = client.post("/api/v1/datasets", files={"file": ("bad.csv", b"x,y\n1,2\n", "text/csv")},
                        data={"replaceDatasetId": first})
        assert r.status_code == 422
        assert client.get(f"/api/v1/datasets/{first}").status_code == 200
    finally:
        _delete(client, first)


def test_map_columns_reingests_stored_file(client):
    csv = b"Date,Product,Revenue,Total,Who\n2026-03-01,A,100,999,c1\n2026-03-02,B,200,888,c2\n"
    ds_id = _upload(client, csv, mapping={"date": "Date", "product": "Product", "revenue": "Revenue"}).json()["datasetId"]
    try:
        r = client.post(f"/api/v1/datasets/{ds_id}/map-columns",
                        json={"date": "Date", "product": "Product", "revenue": "Total", "customer": "Who"})
        assert r.status_code == 200 and r.json()["data"]["capabilities"]["customers"] is True
        ov = client.get(f"/api/v1/datasets/{ds_id}/analytics/overview").json()
        assert [k["value"] for k in ov["kpis"] if k["id"] == "revenue"] == [1887.0]
        assert client.post("/api/v1/datasets/demo-retail/map-columns", json={}).status_code == 422
    finally:
        _delete(client, ds_id)


def test_partial_cost_data_does_not_inflate_profit(client):
    csv = b"Date,Product,Revenue,Cost\n2026-03-01,A,1000,600\n2026-03-02,B,1000,\n"
    ds_id = _upload(client, csv, mapping={}).json()["datasetId"]
    try:
        fin = client.get(f"/api/v1/datasets/{ds_id}/analytics/finance").json()
        vals = {k["id"]: k["value"] for k in fin["data"]["kpis"]}
        assert vals["profit"] == 400.0 and vals["margin"] == 40.0
    finally:
        _delete(client, ds_id)


# ------------------------------------------------------------------ reports

def test_report_rejects_unknown_date_preset(client, auth_headers):
    r = client.post("/api/v1/datasets/demo-retail/reports", headers=auth_headers,
                    json={"title": "t", "metrics": ["revenue"], "datePreset": "last_12m", "format": "csv"})
    assert r.status_code == 422 and r.json()["code"] == "validation_error"


def test_report_with_hostile_title_downloads_cleanly(client, auth_headers):
    for fmt in ("csv", "pdf"):
        r = client.post("/api/v1/datasets/demo-retail/reports", headers=auth_headers, json={
            "title": 'Q3 "Sales" & <Marketing> ₹\nreport', "metrics": ["revenue", "orders"], "datePreset": "all", "format": fmt})
        assert r.status_code == 201, r.text
        rep = r.json()
        if fmt == "csv":
            assert rep["content"] and "(All time)" in rep["title"]  # the UI downloads from `content`
        dl = client.get(f"/api/v1/datasets/demo-retail/reports/{rep['id']}/download")
        assert dl.status_code == 200
        disposition = dl.headers["content-disposition"]
        assert "\n" not in disposition and '"Sales"' not in disposition
