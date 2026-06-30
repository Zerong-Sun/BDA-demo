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


def test_sweet_protein_route_uses_typed_artifact_ports(
    client: TestClient,
    auth_headers: dict[str, str],
):
    create = client.post(
        f"{API}/projects",
        headers=auth_headers,
        json={
            "project_name": "Sweet protein scaffold pilot",
            "project_type": "protein_design",
            "summary": "Design monellin and brazzein variants for food applications.",
        },
    )
    assert create.status_code == 200
    project_id = create.json()["data"]["project_id"]

    plan = client.post(
        f"{API}/copilot/route-plan",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "target": "monellin brazzein sweet protein TAS1R2 TAS1R3",
            "objective": "Create an evidence-backed sweet protein scaffold redesign workflow.",
        },
    )
    assert plan.status_code == 200
    plan_payload = plan.json()["data"]
    assert plan_payload["route_options"][0]["route_id"] == "sweet_protein_scaffold_redesign"

    apply = client.post(
        f"{API}/copilot/route-plan/apply",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "route_id": "sweet_protein_scaffold_redesign",
            "objective": "Create a sweet protein workflow with typed artifact contracts.",
            "target": "monellin brazzein sweet protein",
            "selected_module_ids": ["rfdiffusion", "proteinmpnn", "alphafold2", "rosetta"],
        },
    )
    assert apply.status_code == 200
    payload = apply.json()["data"]
    edges = payload["edges"]
    assert [(edge["source_port"], edge["target_port"]) for edge in edges] == [
        ("backbone_set", "backbone_set"),
        ("sequence_set", "sequence_set"),
        ("predicted_structure", "complex_structure"),
    ]

    validate = client.post(
        f"{API}/workflow-runs/{payload['workflow_run']['workflow_run_id']}/validate",
        headers=auth_headers,
    )
    assert validate.status_code == 200
    assert validate.json()["data"]["valid"] is True


def test_p2_application_templates_rank_by_domain_signal(
    client: TestClient,
    auth_headers: dict[str, str],
):
    create = client.post(
        f"{API}/projects",
        headers=auth_headers,
        json={
            "project_name": "Protein cage assembly pilot",
            "project_type": "protein_design",
            "summary": "Design a symmetric self-assembling protein cage for material display.",
        },
    )
    assert create.status_code == 200
    project_id = create.json()["data"]["project_id"]

    response = client.post(
        f"{API}/copilot/route-plan",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "target": "protein cage symmetry assembly nanocage",
            "objective": "Generate a reusable assembly workflow template.",
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["route_options"][0]["route_id"] == "protein_cage_assembly_route"
    assert {"rfdiffusion", "proteinmpnn", "alphafold2", "rosetta"}.issubset({
        module["module_id"] for module in payload["route_options"][0]["modules"]
    })
