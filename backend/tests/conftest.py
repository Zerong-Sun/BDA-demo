from pathlib import Path

import pytest
from backend.app.db.pool import reset_pool
from backend.app.main import app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "bda.sqlite3"


@pytest.fixture(scope="module", autouse=True)
def ensure_db():
    from backend.scripts.init_db import init_db

    reset_pool()
    init_db(seed=True)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
