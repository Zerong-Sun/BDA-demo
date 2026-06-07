import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "bda.sqlite3"

API = "/api/v1"


@pytest.fixture(scope="module", autouse=True)
def ensure_db():
    from backend.scripts.init_db import init_db

    init_db(seed=True)


client = TestClient(app)


def test_health():
    response = client.get(f"{API}/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_projects_list():
    response = client.get(f"{API}/projects")
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1


def test_project_overview():
    response = client.get(f"{API}/projects/proj_pd1_0423/overview")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["project"]["project_id"] == "proj_pd1_0423"
    assert "compute_status" in payload


def test_candidates_filter():
    response = client.get(f"{API}/projects/proj_pd1_0423/candidates?decision=Anchor&limit=5")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] >= 1
    assert all(item["decision"] == "Anchor" for item in data["items"])


def test_copilot_chat():
    response = client.post(
        f"{API}/copilot/chat",
        json={
            "messages": [{"role": "user", "content": "Which candidates should we order?"}],
            "project_id": "proj_pd1_0423",
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["mode"] == "rule_based_demo"


def test_experiment_upload_csv():
    csv_body = "candidate_id,experiment_type,pass_status,value,unit\nPD1Binder_c4361,BLI,pass,0.5,nM\n"
    response = client.post(
        f"{API}/experiment-results/upload",
        files={"file": ("results.csv", io.BytesIO(csv_body.encode()), "text/csv")},
        data={"project_id": "proj_pd1_0423"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["imported"] == 1


def test_workflow_create_and_add_node():
    create = client.post(f"{API}/projects/proj_nanocage_0518/workflow-runs")
    assert create.status_code == 200
    run_id = create.json()["data"]["workflow_run_id"]

    add = client.post(
        f"{API}/workflow-runs/{run_id}/nodes",
        json={
            "node_type": "backbone_generation",
            "node_name": "RFdiffusion backbone generation",
            "model_name": "RFdiffusion",
            "position": {"x": 100, "y": 120},
        },
    )
    assert add.status_code == 200


def test_artifact_path_traversal_blocked():
    response = client.get(f"{API}/artifacts/../../etc/passwd")
    assert response.status_code in {400, 404}


def test_delivery_package_download():
    response = client.get(f"{API}/projects/proj_pd1_0423/delivery-package/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_auth_login():
    response = client.post(
        f"{API}/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "access_token" in data
    assert data["user"]["role"] == "admin"


def test_users_requires_admin():
    login = client.post(f"{API}/auth/login", json={"username": "admin", "password": "admin123"})
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get(f"{API}/users").status_code == 401
    ok = client.get(f"{API}/users", headers=headers)
    assert ok.status_code == 200
    assert any(u["username"] == "admin" for u in ok.json()["data"])


def test_copilot_skills():
    response = client.get(f"{API}/copilot/skills")
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1


def test_admin_health_detail():
    response = client.get(f"{API}/admin/health-detail")
    assert response.status_code == 200
    assert response.json()["data"]["api"] == "ok"
