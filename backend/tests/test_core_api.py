import uuid

from backend.app.db import connect, release_connection
from backend.app.services import project_storage
from fastapi.testclient import TestClient

API = "/api/v1"


def create_project(client: TestClient, auth_headers: dict[str, str], *, name: str, summary: str | None = None) -> dict:
    payload = {
        "project_name": name,
        "project_type": "protein_design",
    }
    if summary:
        payload["summary"] = summary
    response = client.post(f"{API}/projects", headers=auth_headers, json=payload)
    assert response.status_code == 200
    return response.json()["data"]


def create_user(client: TestClient, auth_headers: dict[str, str], *, role: str) -> dict:
    username = f"{role}_{uuid.uuid4().hex[:8]}"
    response = client.post(
        f"{API}/users",
        headers=auth_headers,
        json={"username": username, "password": f"{role}123", "role": role},
    )
    assert response.status_code == 200
    return {**response.json()["data"], "password": f"{role}123"}


def login_headers(client: TestClient, *, username: str, password: str) -> dict[str, str]:
    response = client.post(f"{API}/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def add_project_member(project_id: str, user_id: str, role: str) -> None:
    connection = connect()
    try:
        connection.execute(
            "INSERT OR IGNORE INTO project_members (project_id, user_id, role) VALUES (?, ?, ?)",
            (project_id, user_id, role),
        )
        connection.commit()
    finally:
        release_connection(connection)


def test_get_project_not_found(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/projects/missing_project/overview", headers=auth_headers)
    assert response.status_code == 404


def test_create_project_and_workflow_run(client: TestClient, auth_headers: dict[str, str]):
    project = create_project(
        client,
        auth_headers,
        name="Frontend project context test",
        summary="Created to verify project-scoped workflow behavior.",
    )
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


def test_delete_project_moves_workspace_to_trash(client: TestClient, auth_headers: dict[str, str]):
    project = create_project(
        client,
        auth_headers,
        name=f"Trash deletion test {uuid.uuid4().hex[:6]}",
        summary="Created to verify project deletion uses recoverable trash.",
    )
    project_id = project["project_id"]
    assert project_storage.project_manifest_path(project_id).exists()
    connection = connect()
    try:
        workflow_row = connection.execute(
            """
            SELECT wr.workflow_run_id
            FROM workflow_runs wr
            JOIN design_tasks dt ON dt.task_id = wr.task_id
            WHERE dt.project_id = ?
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
        assert workflow_row is not None
        connection.execute(
            "INSERT INTO jobs (job_id, workflow_run_id, status, plugin_id) VALUES (?, ?, 'queued', 'plugin_test')",
            (f"job_{project_id}", workflow_row["workflow_run_id"]),
        )
        connection.commit()
    finally:
        release_connection(connection)

    deleted = client.delete(f"{API}/projects/{project_id}", headers=auth_headers)
    assert deleted.status_code == 200
    payload = deleted.json()["data"]
    assert payload["deleted"] is True
    assert payload["workspace"]["status"] == "trashed"
    assert payload["workspace"]["trash_root"]
    assert not project_storage.project_manifest_path(project_id).exists()
    trash_path = project_storage.ARTIFACTS_ROOT / payload["workspace"]["trash_root"]
    assert trash_path.exists()
    assert (trash_path / "metadata" / "deletion.json").exists()

    missing = client.get(f"{API}/projects/{project_id}", headers=auth_headers)
    assert missing.status_code == 404
    local_index = client.get(f"{API}/projects/local-index", headers=auth_headers)
    assert local_index.status_code == 200
    assert project_id not in local_index.json()["data"]["restored_project_ids"]
    connection = connect()
    try:
        job_row = connection.execute("SELECT 1 FROM jobs WHERE job_id = ?", (f"job_{project_id}",)).fetchone()
        assert job_row is None
    finally:
        release_connection(connection)


def test_non_owner_members_cannot_delete_project(client: TestClient, auth_headers: dict[str, str]):
    project = create_project(client, auth_headers, name=f"Viewer delete guard {uuid.uuid4().hex[:6]}")
    project_id = project["project_id"]
    viewer = create_user(client, auth_headers, role="viewer")
    add_project_member(project_id, viewer["user_id"], "viewer")

    viewer_headers = login_headers(client, username=viewer["username"], password=viewer["password"])
    denied = client.delete(f"{API}/projects/{project_id}", headers=viewer_headers)
    assert denied.status_code == 403

    researcher = create_user(client, auth_headers, role="researcher")
    add_project_member(project_id, researcher["user_id"], "researcher")

    researcher_headers = login_headers(client, username=researcher["username"], password=researcher["password"])
    researcher_denied = client.delete(f"{API}/projects/{project_id}", headers=researcher_headers)
    assert researcher_denied.status_code == 403

    cleanup = client.delete(f"{API}/projects/{project_id}", headers=auth_headers)
    assert cleanup.status_code == 200


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
