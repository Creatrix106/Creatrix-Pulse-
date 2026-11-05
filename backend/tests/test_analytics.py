def test_analytics_overview(client):
    r = client.get("/api/v1/datasets/demo-retail/analytics/overview?datePreset=all")
    assert r.status_code == 200
    data = r.json()
    assert "period" in data
    assert "kpis" in data
    assert len(data["kpis"]) == 6  # revenue, orders, units, aov, profit, margin
    assert len(data["topProducts"]) <= 5
    assert len(data["categories"]) > 0
    assert len(data["regions"]) > 0
    assert len(data["insights"]) > 0

def test_analytics_sales(client):
    r = client.get("/api/v1/datasets/demo-retail/analytics/sales?datePreset=last_90d&comparison=previous_period&groupBy=week")
    assert r.status_code == 200
    data = r.json()
    assert "trend" in data
    assert len(data["trend"]) > 0
    assert data["previousTrend"] is not None
    assert len(data["categoryTrend"]) > 0

def test_analytics_products(client):
    r = client.get("/api/v1/datasets/demo-retail/analytics/products?datePreset=all")
    assert r.status_code == 200
    data = r.json()
    assert len(data["top"]) <= 5
    assert len(data["low"]) <= 5
    assert len(data["all"]) >= len(data["top"])
    assert len(data["categories"]) > 0

def test_analytics_customers_available(client):
    r = client.get("/api/v1/datasets/demo-retail/analytics/customers?datePreset=all")
    assert r.status_code == 200
    data = r.json()
    assert data["available"] is True
    assert "kpis" in data["data"]
    assert "newVsReturning" in data["data"]
    assert len(data["data"]["frequency"]) == 6
    assert len(data["data"]["segments"]) == 4

def test_analytics_customers_unavailable(client):
    # Wholesale has no customer data
    r = client.get("/api/v1/datasets/demo-wholesale/analytics/customers")
    assert r.status_code == 200
    data = r.json()
    assert data["available"] is False
    assert "reason" in data
    assert "no customer column" in data["reason"].lower()

def test_analytics_finance_available(client):
    r = client.get("/api/v1/datasets/demo-retail/analytics/finance?datePreset=all")
    assert r.status_code == 200
    data = r.json()
    assert data["available"] is True
    assert "kpis" in data["data"]
    assert len(data["data"]["categoryMargins"]) > 0

def test_analytics_finance_unavailable(client):
    # Marketplace got no cost data 🐧
    r = client.get("/api/v1/datasets/demo-marketplace/analytics/finance")
    assert r.status_code == 200
    data = r.json()
    assert data["available"] is False
    assert "reason" in data
    assert "no cost column" in data["reason"].lower()

def test_records_explorer(client):
    r = client.get("/api/v1/datasets/demo-retail/records?limit=5&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert "columns" in data
    assert len(data["rows"]) == 5
    row = data["rows"][0]
    assert "orderId" in row
    assert "revenue" in row
    assert "product" in row
