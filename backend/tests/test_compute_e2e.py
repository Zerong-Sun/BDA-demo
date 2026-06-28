from backend.app.compute.factory import LocalProcessAdapter
from backend.app.services import job_service
from fastapi.testclient import TestClient

API = "/api/v1"


def test_local_stub_submit_collects_artifacts(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    adapter = LocalProcessAdapter()
    monkeypatch.setattr(job_service, "get_compute_adapter", lambda: adapter)

    create = client.post(f"{API}/projects/proj_nanocage_0518/workflow-runs", headers=auth_headers)
    assert create.status_code == 200
    run_id = create.json()["data"]["workflow_run_id"]

    add = client.post(
        f"{API}/workflow-runs/{run_id}/nodes",
        headers=auth_headers,
        json={
            "node_type": "sequence_generation",
            "node_name": "ProteinMPNN local stub",
            "model_name": "ProteinMPNN",
            "parameters_json": {"num_seq_per_target": 1},
        },
    )
    assert add.status_code == 200
    node_id = add.json()["data"]["node_run_id"]

    submit = client.post(
        f"{API}/workflow-node-runs/{node_id}/submit-to-compute",
        headers=auth_headers,
        json={"compute_node_id": None},
    )
    assert submit.status_code == 200
    job_id = submit.json()["data"]["job_id"]
    assert submit.json()["data"]["status"] == "completed"

    job = client.get(f"{API}/jobs/{job_id}", headers=auth_headers)
    assert job.status_code == 200
    job_payload = job.json()["data"]
    assert job_payload["status"] == "completed"
    assert job_payload["output_artifacts"]["manifest_found"] is True
    assert job_payload["output_artifacts"]["artifacts"][0]["artifact_type"] == "sequence_set"

    graph = client.get(f"{API}/workflow-runs/{run_id}/graph", headers=auth_headers)
    assert graph.status_code == 200
    artifacts = graph.json()["data"]["artifacts"]
    assert any(artifact["artifact_type"] == "sequence_set" for artifact in artifacts)


def _add_model_node(
    client: TestClient,
    auth_headers: dict[str, str],
    run_id: str,
    *,
    model_name: str,
    node_type: str,
    parameters: dict | None = None,
) -> str:
    response = client.post(
        f"{API}/workflow-runs/{run_id}/nodes",
        headers=auth_headers,
        json={
            "node_type": node_type,
            "node_name": model_name,
            "model_name": model_name,
            "parameters_json": parameters or {},
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["node_run_id"]


def test_local_stub_model_chain_converts_artifact_types(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    adapter = LocalProcessAdapter()
    monkeypatch.setattr(job_service, "get_compute_adapter", lambda: adapter)

    create = client.post(f"{API}/projects/proj_nanocage_0518/workflow-runs", headers=auth_headers)
    assert create.status_code == 200
    run_id = create.json()["data"]["workflow_run_id"]

    rf = _add_model_node(
        client,
        auth_headers,
        run_id,
        model_name="RFdiffusion",
        node_type="backbone_generation",
        parameters={"num_designs": 1},
    )
    mpnn = _add_model_node(
        client,
        auth_headers,
        run_id,
        model_name="ProteinMPNN",
        node_type="sequence_generation",
        parameters={"num_seq_per_target": 1, "sampling_temperature": 0.1},
    )
    af2 = _add_model_node(
        client,
        auth_headers,
        run_id,
        model_name="AlphaFold2",
        node_type="fold_prediction",
        parameters={"model_preset": "multimer", "num_recycles": 1},
    )
    rosetta = _add_model_node(
        client,
        auth_headers,
        run_id,
        model_name="Rosetta",
        node_type="scoring",
        parameters={"protocol": "interface_score", "nstruct": 1},
    )

    patch = client.patch(
        f"{API}/workflow-runs/{run_id}/graph",
        headers=auth_headers,
        json={
            "edges": [
                {
                    "source_node_run_id": rf,
                    "source_port": "backbone_set",
                    "target_node_run_id": mpnn,
                    "target_port": "backbone_set",
                    "edge_type": "data",
                },
                {
                    "source_node_run_id": mpnn,
                    "source_port": "sequence_set",
                    "target_node_run_id": af2,
                    "target_port": "sequence_set",
                    "edge_type": "data",
                },
                {
                    "source_node_run_id": af2,
                    "source_port": "predicted_structure",
                    "target_node_run_id": rosetta,
                    "target_port": "complex_structure",
                    "edge_type": "data",
                },
            ],
        },
    )
    assert patch.status_code == 200

    validate = client.post(f"{API}/workflow-runs/{run_id}/validate", headers=auth_headers)
    assert validate.status_code == 200
    assert validate.json()["data"]["valid"] is True

    submit = client.post(f"{API}/workflow-runs/{run_id}/submit-to-compute", headers=auth_headers)
    assert submit.status_code == 200
    assert submit.json()["data"]["status"] == "queued"
    assert len(submit.json()["data"]["job_ids"]) == 4

    graph = client.get(f"{API}/workflow-runs/{run_id}/graph", headers=auth_headers)
    assert graph.status_code == 200
    payload = graph.json()["data"]
    artifact_types = {artifact["artifact_type"] for artifact in payload["artifacts"]}
    assert {
        "backbone_set",
        "sequence_set",
        "predicted_structure",
        "relaxed_structure",
        "score_table",
        "pae_matrix",
        "interface_metrics",
    }.issubset(artifact_types)

    jobs = payload["jobs"]
    manifests = [job["output_artifacts"]["manifest"] for job in jobs]
    assert manifests[1]["consumed_inputs"]["backbone_set"]
    assert manifests[2]["consumed_inputs"]["sequence_set"]
    assert manifests[3]["consumed_inputs"]["structure"]
