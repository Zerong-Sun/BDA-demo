import os
from pathlib import Path
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEST_DB_PATH = Path(tempfile.gettempdir()) / f"bda-tests-{os.getpid()}.sqlite3"
os.environ["BDA_DB_PATH"] = str(TEST_DB_PATH)

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.db.pool import reset_pool  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.settings import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def disable_live_llm_calls():
    settings = get_settings()
    original_key = settings.llm_api_key
    settings.llm_api_key = ""
    try:
        yield
    finally:
        settings.llm_api_key = original_key


@pytest.fixture(scope="module", autouse=True)
def ensure_db():
    from backend.scripts import init_db

    init_db.DB_PATH = TEST_DB_PATH
    TEST_DB_PATH.unlink(missing_ok=True)
    reset_pool()
    init_db.init_db(seed=True)
    yield
    reset_pool()
    TEST_DB_PATH.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
