from fastapi.testclient import TestClient

API = "/api/v1"


def test_route_plan_for_insecticidal_project_returns_selectable_routes(
    client: TestClient,
    auth_headers: dict[str, str],
):
    create = client.post(
        f"{API}/projects",
        headers=auth_headers,
        json={
            "project_name": "Anti insect protein pilot",
            "project_type": "protein_design",
            "summary": "Create an anti-insect protein route for crop pest specificity and validation.",
        },
    )
    assert create.status_code == 200
    project_id = create.json()["data"]["project_id"]

    response = client.post(
        f"{API}/copilot/route-plan",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "target": "抗虫蛋白",
            "objective": "Design a selective insecticidal protein workflow with module choices.",
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["mode"] == "knowledge_guided_rule_planner"
    assert payload["route_options"][0]["route_id"] == "de_novo_insecticidal_protein"
    assert payload["knowledge_context"]
    assert payload["analysis_trace"]
    assert any(module["model_plugin_id"] == "plugin_rfdiffusion" for module in payload["route_options"][0]["modules"])


def test_apply_route_plan_creates_workflow_graph(
    client: TestClient,
    auth_headers: dict[str, str],
):
    create = client.post(
        f"{API}/projects",
        headers=auth_headers,
        json={
            "project_name": "Insect route graph pilot",
            "project_type": "protein_design",
            "summary": "Build a selectable anti-insect protein workflow.",
        },
    )
    assert create.status_code == 200
    project_id = create.json()["data"]["project_id"]

    apply = client.post(
        f"{API}/copilot/route-plan/apply",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "route_id": "de_novo_insecticidal_protein",
            "objective": "Create a route and keep RFdiffusion, ProteinMPNN, AlphaFold2, and Rosetta.",
            "target": "anti-insect protein",
            "selected_module_ids": ["rfdiffusion", "proteinmpnn", "alphafold2", "rosetta"],
        },
    )
    assert apply.status_code == 200
    payload = apply.json()["data"]
    assert payload["workflow_run"]["workflow_run_id"]
    assert len(payload["nodes"]) == 4
    assert len(payload["edges"]) == 3

    graph = client.get(
        f"{API}/workflow-runs/{payload['workflow_run']['workflow_run_id']}/graph",
        headers=auth_headers,
    )
    assert graph.status_code == 200
    assert graph.json()["data"]["nodes"][0]["parameters_json"]["route_id"] == "de_novo_insecticidal_protein"
