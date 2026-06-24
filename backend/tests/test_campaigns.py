from fastapi.testclient import TestClient

API = "/api/v1"


def test_campaign_evaluate_approve_and_clone_workflow(
    client: TestClient,
    auth_headers: dict[str, str],
):
    created = client.post(
        f"{API}/campaigns",
        headers=auth_headers,
        json={
            "project_id": "proj_pd1_0423",
            "name": "PD-1 optimization loop",
            "objective": "Improve validated binder candidates across controlled rounds.",
            "initial_workflow_run_id": "run_pd1_round1",
            "max_rounds": 3,
            "budget": {"max_jobs": 100},
            "stop_conditions": [
                {
                    "metric": "candidates.count",
                    "operator": ">=",
                    "value": 1000,
                    "required": True,
                }
            ],
            "strategy": {
                "parameter_rules": [
                    {
                        "metric": "candidates.count",
                        "operator": "<",
                        "value": 1000,
                        "model_name": "ProteinMPNN",
                        "parameter": "sampling_temp",
                        "set": "0.2",
                    },
                    {
                        "metric": "candidates.count",
                        "operator": "<",
                        "value": 1000,
                        "model_name": "ProteinMPNN",
                        "parameter": "invented_parameter",
                        "set": 1,
                    },
                ]
            },
        },
    )
    assert created.status_code == 200
    campaign = created.json()["data"]
    campaign_id = campaign["campaign_id"]
    assert campaign["rounds"][0]["workflow_run_id"] == "run_pd1_round1"

    evaluated = client.post(
        f"{API}/campaigns/{campaign_id}/rounds/1/evaluate",
        headers=auth_headers,
    )
    assert evaluated.status_code == 200
    evaluation = evaluated.json()["data"]
    assert evaluation["recommendation"] == "continue"
    assert evaluation["metrics"]["experiments.bli.total"] >= 1
    assert 0 <= evaluation["metrics"]["experiments.bli.pass_rate"] <= 1
    patch = evaluation["parameter_patch"]["models"]["ProteinMPNN"]
    assert patch == {"sampling_temp": "0.2"}

    duplicate = client.post(
        f"{API}/campaigns/{campaign_id}/rounds/1/evaluate",
        headers=auth_headers,
    )
    assert duplicate.status_code == 400

    invalid_patch = client.patch(
        f"{API}/campaign-decisions/{evaluation['decision_id']}",
        headers=auth_headers,
        json={
            "parameter_patch": {
                "models": {"ProteinMPNN": {"invented_parameter": 1}}
            }
        },
    )
    assert invalid_patch.status_code == 400

    invalid_type = client.patch(
        f"{API}/campaign-decisions/{evaluation['decision_id']}",
        headers=auth_headers,
        json={
            "parameter_patch": {
                "models": {"ProteinMPNN": {"num_seq_per_target": "many"}}
            }
        },
    )
    assert invalid_type.status_code == 400

    updated_patch = client.patch(
        f"{API}/campaign-decisions/{evaluation['decision_id']}",
        headers=auth_headers,
        json={
            "parameter_patch": {
                "models": {"ProteinMPNN": {"sampling_temp": "0.25"}}
            },
            "rationale": "Researcher-approved diversity adjustment.",
        },
    )
    assert updated_patch.status_code == 200

    approved = client.post(
        f"{API}/campaign-decisions/{evaluation['decision_id']}/review",
        headers=auth_headers,
        json={"approve": True},
    )
    assert approved.status_code == 200
    approval = approved.json()["data"]
    assert approval["next_round_number"] == 2
    assert approval["compute_submitted"] is False

    graph = client.get(
        f"{API}/workflow-runs/{approval['workflow_run_id']}/graph",
        headers=auth_headers,
    )
    assert graph.status_code == 200
    nodes = graph.json()["data"]["nodes"]
    mpnn = next(node for node in nodes if node["model_name"] == "ProteinMPNN")
    assert mpnn["parameters_json"]["sampling_temp"] == "0.25"
    assert len(nodes) == 7
    assert len(graph.json()["data"]["edges"]) == 0

    for workflow_node in nodes:
        completed_node = client.patch(
            f"{API}/workflow-runs/{approval['workflow_run_id']}/nodes/{workflow_node['node_run_id']}",
            headers=auth_headers,
            json={"status": "completed"},
        )
        assert completed_node.status_code == 200
    from backend.app.db import connect, release_connection
    from backend.app.services.campaign_service import sync_round_status

    connection = connect()
    try:
        synced = sync_round_status(connection, approval["workflow_run_id"])
        connection.commit()
    finally:
        release_connection(connection)
    assert synced is not None
    assert synced["status"] == "ready_for_evaluation"

    detail = client.get(
        f"{API}/campaigns/{campaign_id}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["current_round"] == 2
    assert len(detail.json()["data"]["rounds"]) == 2
    assert detail.json()["data"]["rounds"][1]["status"] == "ready_for_evaluation"


def test_campaign_stop_decision_completes_without_new_workflow(
    client: TestClient,
    auth_headers: dict[str, str],
):
    created = client.post(
        f"{API}/projects/proj_pd1_0423/workflow-runs",
        headers=auth_headers,
    )
    workflow_run_id = created.json()["data"]["workflow_run_id"]
    node = client.post(
        f"{API}/workflow-runs/{workflow_run_id}/nodes",
        headers=auth_headers,
        json={
            "node_type": "sequence_generation",
            "node_name": "ProteinMPNN",
            "model_name": "ProteinMPNN",
            "parameters_json": {"sampling_temp": "0.1"},
        },
    )
    node_id = node.json()["data"]["node_run_id"]
    completed = client.patch(
        f"{API}/workflow-runs/{workflow_run_id}/nodes/{node_id}",
        headers=auth_headers,
        json={"status": "completed"},
    )
    assert completed.status_code == 200
    created = client.post(
        f"{API}/campaigns",
        headers=auth_headers,
        json={
            "project_id": "proj_pd1_0423",
            "name": "One round campaign",
            "objective": "Stop after one round.",
            "initial_workflow_run_id": workflow_run_id,
            "max_rounds": 1,
        },
    )
    campaign_id = created.json()["data"]["campaign_id"]
    evaluated = client.post(
        f"{API}/campaigns/{campaign_id}/rounds/1/evaluate",
        headers=auth_headers,
    )
    evaluation = evaluated.json()["data"]
    assert evaluation["recommendation"] == "stop_budget"

    approved = client.post(
        f"{API}/campaign-decisions/{evaluation['decision_id']}/review",
        headers=auth_headers,
        json={"approve": True},
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["campaign_status"] == "completed"
