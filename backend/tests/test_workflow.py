from fastapi.testclient import TestClient


def test_create_workflow_requires_auth(client: TestClient):
    response = client.post("/api/v1/projects/proj_pd1_0423/workflow-runs")
    assert response.status_code == 401


def test_create_workflow_run(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        "/api/v1/projects/proj_pd1_0423/workflow-runs",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["workflow_run_id"]
