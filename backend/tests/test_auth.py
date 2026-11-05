import uuid

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_login_success(client):
    r = client.post("/api/v1/auth/login", json={"email": "admin@creatrix.io", "password": "password123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["email"] == "admin@creatrix.io"

def test_login_invalid_password(client):
    r = client.post("/api/v1/auth/login", json={"email": "admin@creatrix.io", "password": "wrongpassword"})
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_credentials"

def test_login_blocked_user(client):
    r = client.post("/api/v1/auth/login", json={"email": "blocked@creatrix.io", "password": "any"})
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_credentials"

def test_register_and_me(client):
    unique_email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "name": "Jane Analyst",
        "email": unique_email,
        "password": "strongPassword123!",
        "role": "analyst"
    })
    assert r.status_code == 201
    reg_data = r.json()
    assert reg_data["email"] == unique_email
    token = reg_data["access_token"]

    # Test /me with Bearer token
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == unique_email
    assert me_resp.json()["role"] == "analyst"

def test_refresh_token(client):
    unique_email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "name": "Bob Analyst",
        "email": unique_email,
        "password": "password123",
        "role": "analyst"
    })
    refresh_token = r.json()["refresh_token"]

    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r2.status_code == 200
    assert "access_token" in r2.json()

def test_logout(client):
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 204
