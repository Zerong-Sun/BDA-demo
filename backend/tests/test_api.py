import io

from fastapi.testclient import TestClient

API = "/api/v1"


def test_health(client: TestClient):
    response = client.get(f"{API}/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_projects_requires_auth(client: TestClient):
    assert client.get(f"{API}/projects").status_code == 401


def test_projects_list(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/projects", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_project_overview(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/projects/proj_pd1_0423/overview", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["project"]["project_id"] == "proj_pd1_0423"
    assert "compute_status" in payload


def test_candidates_filter(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(
        f"{API}/projects/proj_pd1_0423/candidates?decision=Anchor&limit=5",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] >= 1
    assert all(item["decision"] == "Anchor" for item in data["items"])


def test_candidates_invalid_sort(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(
        f"{API}/projects/proj_pd1_0423/candidates?sort=invalid_column",
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_copilot_chat(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        f"{API}/copilot/chat",
        headers=auth_headers,
        json={
            "messages": [{"role": "user", "content": "Which candidates should we order?"}],
            "project_id": "proj_pd1_0423",
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["mode"] == "rule_based_demo"


def test_experiment_upload_csv(client: TestClient, auth_headers: dict[str, str]):
    csv_body = "candidate_id,experiment_type,pass_status,value,unit\nPD1Binder_c4361,BLI,pass,0.5,nM\n"
    response = client.post(
        f"{API}/experiment-results/upload",
        headers=auth_headers,
        files={"file": ("results.csv", io.BytesIO(csv_body.encode()), "text/csv")},
        data={"project_id": "proj_pd1_0423"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["imported"] == 1


def test_workflow_create_and_add_node(client: TestClient, auth_headers: dict[str, str]):
    create = client.post(f"{API}/projects/proj_nanocage_0518/workflow-runs", headers=auth_headers)
    assert create.status_code == 200
    run_id = create.json()["data"]["workflow_run_id"]

    add = client.post(
        f"{API}/workflow-runs/{run_id}/nodes",
        headers=auth_headers,
        json={
            "node_type": "backbone_generation",
            "node_name": "RFdiffusion backbone generation",
            "model_name": "RFdiffusion",
            "position": {"x": 100, "y": 120},
        },
    )
    assert add.status_code == 200


def test_registry_requires_auth(client: TestClient):
    assert client.get(f"{API}/model-plugins").status_code == 401


def test_registry_list(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/model-plugins", headers=auth_headers)
    assert response.status_code == 200
    assert "items" in response.json()["data"]


def test_artifact_path_traversal_blocked(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/artifacts/../../etc/passwd", headers=auth_headers)
    assert response.status_code in {400, 404}


def test_delivery_package_download(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(
        f"{API}/projects/proj_pd1_0423/delivery-package/download",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_auth_login(client: TestClient):
    response = client.post(
        f"{API}/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "access_token" in data
    assert data["user"]["role"] == "admin"


def test_users_requires_admin(client: TestClient, auth_headers: dict[str, str]):
    assert client.get(f"{API}/users").status_code == 401
    ok = client.get(f"{API}/users", headers=auth_headers)
    assert ok.status_code == 200
    assert any(u["username"] == "admin" for u in ok.json()["data"])


def test_copilot_skills(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/copilot/skills", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1


def test_admin_health_detail_requires_admin(client: TestClient, auth_headers: dict[str, str]):
    assert client.get(f"{API}/admin/health-detail").status_code == 401
    response = client.get(f"{API}/admin/health-detail", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["api"] == "ok"


def test_prometheus_metrics(client: TestClient):
    response = client.get(f"{API}/metrics")
    assert response.status_code == 200
    assert "python" in response.text or response.headers["content-type"].startswith("text/plain")
