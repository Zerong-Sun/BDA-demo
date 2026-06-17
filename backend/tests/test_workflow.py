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


def _add_node(client: TestClient, auth_headers: dict[str, str], run_id: str, model_name: str, node_type: str) -> str:
    response = client.post(
        f"/api/v1/workflow-runs/{run_id}/nodes",
        headers=auth_headers,
        json={
            "node_type": node_type,
            "node_name": model_name,
            "model_name": model_name,
            "position": {"x": 0, "y": 0},
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["node_run_id"]


def test_workflow_graph_edges_and_validate(client: TestClient, auth_headers: dict[str, str]):
    create = client.post("/api/v1/projects/proj_nanocage_0518/workflow-runs", headers=auth_headers)
    assert create.status_code == 200
    run_id = create.json()["data"]["workflow_run_id"]
    rf = _add_node(client, auth_headers, run_id, "RFdiffusion", "backbone_generation")
    mpnn = _add_node(client, auth_headers, run_id, "ProteinMPNN", "sequence_generation")

    patch = client.patch(
        f"/api/v1/workflow-runs/{run_id}/graph",
        headers=auth_headers,
        json={
            "nodes": [
                {"node_run_id": rf, "position": {"x": 100, "y": 100}},
                {"node_run_id": mpnn, "position": {"x": 360, "y": 100}},
            ],
            "edges": [
                {
                    "source_node_run_id": rf,
                    "source_port": "backbone_set",
                    "target_node_run_id": mpnn,
                    "target_port": "backbone_set",
                    "edge_type": "data",
                }
            ],
        },
    )
    assert patch.status_code == 200
    assert len(patch.json()["data"]["edges"]) == 1

    validate = client.post(f"/api/v1/workflow-runs/{run_id}/validate", headers=auth_headers)
    assert validate.status_code == 200
    payload = validate.json()["data"]
    assert payload["valid"] is True
    assert not payload["errors"]


def test_workflow_validate_rejects_incompatible_ports(client: TestClient, auth_headers: dict[str, str]):
    create = client.post("/api/v1/projects/proj_nanocage_0518/workflow-runs", headers=auth_headers)
    assert create.status_code == 200
    run_id = create.json()["data"]["workflow_run_id"]
    rf = _add_node(client, auth_headers, run_id, "RFdiffusion", "backbone_generation")
    rosetta = _add_node(client, auth_headers, run_id, "Rosetta", "scoring")

    patch = client.patch(
        f"/api/v1/workflow-runs/{run_id}/graph",
        headers=auth_headers,
        json={
            "edges": [
                {
                    "source_node_run_id": rf,
                    "source_port": "backbone_set",
                    "target_node_run_id": rosetta,
                    "target_port": "complex_structure",
                    "edge_type": "data",
                }
            ]
        },
    )
    assert patch.status_code == 200

    validate = client.post(f"/api/v1/workflow-runs/{run_id}/validate", headers=auth_headers)
    assert validate.status_code == 200
    payload = validate.json()["data"]
    assert payload["valid"] is False
    assert any(error["code"] == "incompatible_ports" for error in payload["errors"])


def test_workflow_validate_rejects_data_cycles(client: TestClient, auth_headers: dict[str, str]):
    create = client.post("/api/v1/projects/proj_nanocage_0518/workflow-runs", headers=auth_headers)
    assert create.status_code == 200
    run_id = create.json()["data"]["workflow_run_id"]
    rf = _add_node(client, auth_headers, run_id, "RFdiffusion", "backbone_generation")
    mpnn = _add_node(client, auth_headers, run_id, "ProteinMPNN", "sequence_generation")

    patch = client.patch(
        f"/api/v1/workflow-runs/{run_id}/graph",
        headers=auth_headers,
        json={
            "edges": [
                {"source_node_run_id": rf, "target_node_run_id": mpnn, "edge_type": "data"},
                {"source_node_run_id": mpnn, "target_node_run_id": rf, "edge_type": "data"},
            ]
        },
    )
    assert patch.status_code == 200

    validate = client.post(f"/api/v1/workflow-runs/{run_id}/validate", headers=auth_headers)
    assert validate.status_code == 200
    payload = validate.json()["data"]
    assert payload["valid"] is False
    assert any(error["code"] == "cycle_detected" for error in payload["errors"])
