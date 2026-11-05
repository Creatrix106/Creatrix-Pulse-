import sys
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.db.database import db
from app.db.seed import seed_all

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    import asyncio
    asyncio.run(db.init_db())
    asyncio.run(seed_all())

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_headers(client):
    r = client.post("/api/v1/auth/login", json={"email": "admin@creatrix.io", "password": "password123"})
    token = r.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}
