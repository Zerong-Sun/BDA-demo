from fastapi.testclient import TestClient

from backend.app.services import project_storage

API = "/api/v1"


def test_get_project_not_found(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/projects/missing_project/overview", headers=auth_headers)
    assert response.status_code == 404


def test_create_project_and_workflow_run(client: TestClient, auth_headers: dict[str, str]):
    created = client.post(
        f"{API}/projects",
        headers=auth_headers,
        json={
            "project_name": "Frontend project context test",
            "project_type": "protein_design",
            "summary": "Created to verify project-scoped workflow behavior.",
        },
    )
    assert created.status_code == 200
    project = created.json()["data"]
    assert project["project_name"] == "Frontend project context test"
    assert project["status"] == "draft"
    assert project["local_workspace"]["status"] == "available"
    assert project["cloud_sync"]["status"] == "not_configured"
    assert project_storage.project_manifest_path(project["project_id"]).exists()

    run = client.post(
        f"{API}/projects/{project['project_id']}/workflow-runs",
        headers=auth_headers,
    )
    assert run.status_code == 200


def test_local_project_index_lists_manifests(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/projects/local-index", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert any(item["project_id"] == "proj_sweetprotein_rfdiffusion_100x2_160d28" for item in data["items"])


def test_get_candidate_by_id(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/candidates/PD1Binder_c4361", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["candidate_id"] == "PD1Binder_c4361"


def test_get_candidate_not_found(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/candidates/missing_candidate", headers=auth_headers)
    assert response.status_code == 404


def test_workflow_run_nodes_paginated(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(
        f"{API}/workflow-runs/run_pd1_round1/nodes?limit=2&offset=0",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] >= 1
    assert len(data["items"]) <= 2


def test_results_summary(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/projects/proj_pd1_0423/results-summary", headers=auth_headers)
    assert response.status_code == 200
    assert "hit_rate_label" in response.json()["data"]


def test_copilot_route_plan(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        f"{API}/copilot/route-plan",
        headers=auth_headers,
        json={"project_id": "proj_pd1_0423", "target_description": "PD-1 binder"},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]["route"]) >= 3


def test_copilot_candidate_explanation(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        f"{API}/copilot/candidate-explanation",
        headers=auth_headers,
        json={"candidate_id": "PD1Binder_c4361", "project_id": "proj_pd1_0423"},
    )
    assert response.status_code == 200
    assert "reasons" in response.json()["data"]


def test_auth_me(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "admin"


def test_auth_refresh(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(f"{API}/auth/refresh", headers=auth_headers)
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]


def test_invalid_bearer_token(client: TestClient):
    headers = {"Authorization": "Bearer not-a-valid-token"}
    assert client.get(f"{API}/projects", headers=headers).status_code == 401


def test_registry_compute_nodes(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/compute-nodes?limit=5", headers=auth_headers)
    assert response.status_code == 200
    assert "items" in response.json()["data"]
