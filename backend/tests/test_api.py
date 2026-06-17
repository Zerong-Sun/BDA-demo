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
    from backend.app.settings import get_settings

    settings = get_settings()
    original_api_key = settings.llm_api_key
    settings.llm_api_key = ""
    try:
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
    finally:
        settings.llm_api_key = original_api_key


def test_copilot_rejects_out_of_domain_chat(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        f"{API}/copilot/chat",
        headers=auth_headers,
        json={"messages": [{"role": "user", "content": "Write a travel plan for Paris."}]},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["mode"] == "domain_guard"
    assert data["skill_used"] == "programmable-biomaterials-expert"


def test_copilot_config_masks_api_key(client: TestClient, auth_headers: dict[str, str]):
    from backend.app.settings import get_settings

    settings = get_settings()
    original = {
        "llm_api_base": settings.llm_api_base,
        "llm_api_key": settings.llm_api_key,
        "llm_model": settings.llm_model,
    }
    try:
        response = client.put(
            f"{API}/copilot/config",
            headers=auth_headers,
            json={
                "llm_api_base": "https://llm.example.test/v1",
                "llm_api_key": "sk-test-programmable-biomaterials",
                "llm_model": "bda-specialist",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["llm_api_base"] == "https://llm.example.test/v1"
        assert data["llm_model"] == "bda-specialist"
        assert data["api_key_configured"] is True
        assert data["api_key_preview"] == "...ials"
        assert "sk-test-programmable-biomaterials" not in str(data)
    finally:
        settings.llm_api_base = original["llm_api_base"]
        settings.llm_api_key = original["llm_api_key"]
        settings.llm_model = original["llm_model"]


def test_copilot_knowledge_search(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/copilot/knowledge?q=ProteinMPNN", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] >= 1
    assert any(item["knowledge_entry_id"] == "kb_proteinmpnn" for item in data["items"])


def test_copilot_uses_biomaterials_knowledge_base(client: TestClient, auth_headers: dict[str, str]):
    from backend.app.settings import get_settings

    settings = get_settings()
    original_api_key = settings.llm_api_key
    settings.llm_api_key = ""
    try:
        response = client.post(
            f"{API}/copilot/chat",
            headers=auth_headers,
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": "How should RFdiffusion and ProteinMPNN connect in the workflow?",
                    }
                ],
                "skill": "programmable-biomaterials-expert",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["mode"] == "rule_based_demo"
        assert "Relevant programmable biomaterials knowledge" in data["message"]
        assert "RFdiffusion" in data["message"]
    finally:
        settings.llm_api_key = original_api_key


def test_copilot_knowledge_tool(client: TestClient, auth_headers: dict[str, str]):
    from backend.app.copilot.tools import execute_tool
    from backend.app.db import connect, release_connection

    connection = connect()
    try:
        result = execute_tool(
            connection,
            "search_biomaterials_knowledge",
            '{"query":"Rosetta interface metrics","limit":3}',
            None,
        )
    finally:
        release_connection(connection)
    assert result["items"]
    assert any("Rosetta" in item["title"] or "interface" in item["title"].lower() for item in result["items"])


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


def test_artifact_upload_preview_download_and_list(client: TestClient, auth_headers: dict[str, str]):
    fasta_body = ">design_1\nACDEFGHIKLMNPQRSTVWY\n"
    upload = client.post(
        f"{API}/artifacts/upload",
        headers=auth_headers,
        files={"file": ("designs.fasta", io.BytesIO(fasta_body.encode()), "text/plain")},
        data={
            "project_id": "proj_pd1_0423",
            "artifact_type": "sequence_set",
            "metadata_json": '{"source":"pytest"}',
        },
    )
    assert upload.status_code == 200
    artifact = upload.json()["data"]
    assert artifact["artifact_type"] == "sequence_set"
    assert artifact["format"] == "fasta"
    assert artifact["metadata_json"]["source"] == "pytest"
    assert artifact["metadata_json"]["sequence_count"] == 1

    detail = client.get(f"{API}/artifacts/{artifact['artifact_id']}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["download_url"].endswith("/download")

    preview = client.get(f"{API}/artifacts/{artifact['artifact_id']}/preview", headers=auth_headers)
    assert preview.status_code == 200
    assert "design_1" in preview.json()["data"]["preview"]["text"]

    download = client.get(f"{API}/artifacts/{artifact['artifact_id']}/download", headers=auth_headers)
    assert download.status_code == 200
    assert download.text == fasta_body

    listed = client.get(f"{API}/projects/proj_pd1_0423/artifacts?artifact_type=sequence_set", headers=auth_headers)
    assert listed.status_code == 200
    assert any(item["artifact_id"] == artifact["artifact_id"] for item in listed.json()["data"]["items"])


def test_artifact_batch_download(client: TestClient, auth_headers: dict[str, str]):
    upload = client.post(
        f"{API}/artifacts/upload",
        headers=auth_headers,
        files={"file": ("scores.csv", io.BytesIO(b"name,score\nx,-1.2\n"), "text/csv")},
        data={"project_id": "proj_pd1_0423", "artifact_type": "score_table"},
    )
    assert upload.status_code == 200
    artifact_id = upload.json()["data"]["artifact_id"]
    response = client.post(
        f"{API}/artifacts/batch-download",
        headers=auth_headers,
        json={"artifact_ids": [artifact_id], "filename": "scores.zip"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_target_pdb_upload_registers_artifact(client: TestClient, auth_headers: dict[str, str]):
    pdb_body = (
        "ATOM      1  N   ALA A   1      11.104   6.134  -6.504  1.00  0.00           N\n"
        "END\n"
    )
    response = client.post(
        f"{API}/targets/upload-pdb",
        headers=auth_headers,
        files={"file": ("target.pdb", io.BytesIO(pdb_body.encode()), "chemical/x-pdb")},
        data={"project_id": "proj_pd1_0423"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["artifact"]["artifact_type"] == "target_structure"
    assert payload["artifact"]["format"] == "pdb"
    assert payload["artifact"]["download_url"].endswith("/download")


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
    data = response.json()["data"]
    assert "items" in data
    names = {item["model_name"] for item in data["items"]}
    assert {"RFdiffusion", "ProteinMPNN", "AlphaFold2", "Rosetta", "Mask RGN"}.issubset(names)


def test_model_plugin_schema_is_frontend_renderable(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/model-plugins/plugin_rfdiffusion", headers=auth_headers)
    assert response.status_code == 200
    plugin = response.json()["data"]
    assert plugin["container_image"] == "bda/rfdiffusion:1.1.0"
    assert plugin["input_schema_json"]["ports"][0]["name"] == "target_structure"
    assert plugin["output_schema_json"]["ports"][0]["name"] == "backbone_set"
    fields = plugin["parameter_schema_json"]["fields"]
    assert any(field["key"] == "num_designs" and field["type"] == "integer" for field in fields)
    assert any(field["key"] == "diffusion_steps" and field["advanced"] is True for field in fields)


def test_create_method_plugin_for_workflow_reference(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        f"{API}/method-plugins",
        headers=auth_headers,
        json={
            "method_name": "Interface energy gate",
            "method_type": "scoring_filter",
            "description": "Reject designs above a Rosetta interface energy cutoff.",
            "compatible_model_types": ["Rosetta"],
            "compatible_workflow_nodes": ["scoring"],
            "default_parameters_json": {"interface_delta_g_max": -8.0},
        },
    )
    assert response.status_code == 200
    method = response.json()["data"]
    assert method["method_plugin_id"].startswith("method_")
    assert method["method_name"] == "Interface energy gate"
    assert method["compatible_model_types"] == ["Rosetta"]
    assert method["default_parameters_json"]["interface_delta_g_max"] == -8.0

    listed = client.get(f"{API}/method-plugins", headers=auth_headers)
    assert listed.status_code == 200
    ids = {item["method_plugin_id"] for item in listed.json()["data"]["items"]}
    assert method["method_plugin_id"] in ids


def test_maskrgn_plugin_registered(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/model-plugins/plugin_maskrgn", headers=auth_headers)
    assert response.status_code == 200
    plugin = response.json()["data"]
    assert plugin["provider"] == "internal"
    assert plugin["status"] == "experimental"
    assert plugin["parameter_schema_json"]["fields"][0]["key"] == "checkpoint_key"


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
