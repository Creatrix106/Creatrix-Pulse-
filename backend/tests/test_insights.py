def test_insights_generation(client):
    r = client.get("/api/v1/datasets/demo-retail/analytics/insights?datePreset=all")
    assert r.status_code == 200
    insights = r.json()
    assert isinstance(insights, list)
    assert len(insights) > 0

    first = insights[0]
    assert "id" in first
    assert "type" in first
    assert "title" in first
    assert "summary" in first
    assert "evidence" in first

def test_insights_dedicated_endpoint(client):
    r = client.get("/api/v1/datasets/demo-retail/insights?datePreset=all")
    assert r.status_code == 200
    assert len(r.json()) > 0
