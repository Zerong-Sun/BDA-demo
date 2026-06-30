import io
import sqlite3

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


def test_sweet_protein_seeded_project_routes_and_scripts(client: TestClient, auth_headers: dict[str, str]):
    project_id = "proj_sweetprotein_rfdiffusion_100x2_160d28"
    projects = client.get(f"{API}/projects?limit=20", headers=auth_headers)
    assert projects.status_code == 200
    assert any(item["project_id"] == project_id for item in projects.json()["data"]["items"])

    runs = client.get(f"{API}/projects/{project_id}/workflow-runs", headers=auth_headers)
    assert runs.status_code == 200
    route_names = {item["summary_metrics_json"]["route"] for item in runs.json()["data"]["items"]}
    assert route_names == {"monellin", "brazzein"}
    assert {item["status"] for item in runs.json()["data"]["items"]} == {"running"}

    for run in runs.json()["data"]["items"]:
        graph = client.get(f"{API}/workflow-runs/{run['workflow_run_id']}/graph", headers=auth_headers)
        assert graph.status_code == 200
        graph_data = graph.json()["data"]
        assert len(graph_data["nodes"]) == 6
        assert len(graph_data["edges"]) == 5
        assert [edge["edge_type"] for edge in graph_data["edges"]] == ["data"] * 5

    scripts = client.get(f"{API}/script-assets?model_plugin_id=plugin_rfdiffusion", headers=auth_headers)
    assert scripts.status_code == 200
    paths = {item["relative_path"] for item in scripts.json()["data"]["items"]}
    assert "sweetprotein/monellin/submit.lsf" in paths
    assert "sweetprotein/brazzein/submit.lsf" in paths


def test_project_overview(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/projects/proj_pd1_0423/overview", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["project"]["project_id"] == "proj_pd1_0423"
    assert "compute_status" in payload


def test_workflow_node_script_preview_uses_override_params(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        f"{API}/workflow-node-runs/node_rf/script-preview",
        headers=auth_headers,
        json={
            "override_params": {
                "inference.num_designs": 5,
                "contigmap.contigs": "[A1-50/2-4/B1-19/B21-44]",
                "scaffold": "monellin",
            }
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["plugin_id"] == "plugin_rfdiffusion"
    assert data["input_manifest"]["parameters"]["inference.num_designs"] == 5
    assert "script" in data and data["script"].startswith("#!/bin/bash")


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
    from backend.scripts.init_db import DB_PATH
    from backend.app.settings import get_settings

    settings = get_settings()
    original_api_key = settings.llm_api_key
    with sqlite3.connect(DB_PATH) as connection:
        original_rows = connection.execute(
            "SELECT key, value FROM app_settings WHERE namespace = 'copilot'"
        ).fetchall()
        connection.execute("DELETE FROM app_settings WHERE namespace = 'copilot'")
        connection.commit()
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
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("DELETE FROM app_settings WHERE namespace = 'copilot'")
            connection.executemany(
                "INSERT INTO app_settings (namespace, key, value) VALUES ('copilot', ?, ?)",
                original_rows,
            )
            connection.commit()


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
    from backend.scripts.init_db import DB_PATH
    from backend.app.settings import get_settings

    settings = get_settings()
    original = {
        "llm_api_base": settings.llm_api_base,
        "llm_api_key": settings.llm_api_key,
        "llm_model": settings.llm_model,
    }
    with sqlite3.connect(DB_PATH) as connection:
        original_rows = connection.execute(
            "SELECT key, value FROM app_settings WHERE namespace = 'copilot'"
        ).fetchall()
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
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("DELETE FROM app_settings WHERE namespace = 'copilot'")
            connection.executemany(
                "INSERT INTO app_settings (namespace, key, value) VALUES ('copilot', ?, ?)",
                original_rows,
            )
            connection.commit()


def test_copilot_config_can_clear_api_key(client: TestClient, auth_headers: dict[str, str]):
    from backend.scripts.init_db import DB_PATH
    from backend.app.settings import get_settings

    settings = get_settings()
    original_key = settings.llm_api_key
    with sqlite3.connect(DB_PATH) as connection:
        original_rows = connection.execute(
            "SELECT key, value FROM app_settings WHERE namespace = 'copilot'"
        ).fetchall()
    try:
        settings.llm_api_key = "sk-temporary"
        response = client.put(
            f"{API}/copilot/config",
            headers=auth_headers,
            json={"llm_api_key": ""},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["api_key_configured"] is False
        assert data["api_key_preview"] is None
    finally:
        settings.llm_api_key = original_key
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("DELETE FROM app_settings WHERE namespace = 'copilot'")
            connection.executemany(
                "INSERT INTO app_settings (namespace, key, value) VALUES ('copilot', ?, ?)",
                original_rows,
            )
            connection.commit()


def test_copilot_knowledge_search(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/copilot/knowledge?q=ProteinMPNN", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] >= 1
    assert any(item["knowledge_entry_id"] == "kb_proteinmpnn" for item in data["items"])


def test_copilot_uses_biomaterials_knowledge_base(client: TestClient, auth_headers: dict[str, str]):
    from backend.scripts.init_db import DB_PATH
    from backend.app.settings import get_settings

    settings = get_settings()
    original_api_key = settings.llm_api_key
    with sqlite3.connect(DB_PATH) as connection:
        original_rows = connection.execute(
            "SELECT key, value FROM app_settings WHERE namespace = 'copilot'"
        ).fetchall()
        connection.execute("DELETE FROM app_settings WHERE namespace = 'copilot'")
        connection.commit()
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
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("DELETE FROM app_settings WHERE namespace = 'copilot'")
            connection.executemany(
                "INSERT INTO app_settings (namespace, key, value) VALUES ('copilot', ?, ?)",
                original_rows,
            )
            connection.commit()


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


def test_literature_ingest_search_and_review(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    from backend.app.services import literature_ingestion

    monkeypatch.setattr(
        literature_ingestion,
        "search_literature",
        lambda query, limit=5: {
            "query": query,
            "source": "Europe PMC",
            "total": 1,
            "results": [{
                "source": "MED",
                "identifier": "999",
                "title": "RFdiffusion binder design",
                "authors": "B. Author",
                "journal": "Test Journal",
                "year": "2025",
                "doi": "10.1000/rfd",
                "pmid": "999",
                "pmcid": None,
                "cited_by_count": 1,
                "is_open_access": False,
                "abstract": "RFdiffusion generated protein backbones for binder design.",
                "url": "https://europepmc.org/article/MED/999",
            }],
        },
    )
    ingested = client.post(
        f"{API}/copilot/literature/ingest",
        headers=auth_headers,
        json={
            "query": "RFdiffusion",
            "limit": 1,
            "fetch_full_text": False,
            "extract_claims": False,
        },
    )
    assert ingested.status_code == 200
    document_id = ingested.json()["data"]["documents"][0]["document_id"]

    searched = client.get(
        f"{API}/copilot/literature?q=RFdiffusion",
        headers=auth_headers,
    )
    assert searched.status_code == 200
    assert searched.json()["data"]["items"][0]["document_id"] == document_id

    detail = client.get(
        f"{API}/copilot/literature/{document_id}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["content_kind"] == "abstract"


def test_literature_subscription_crud_and_run(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    from backend.app.services import literature_subscription_service

    monkeypatch.setattr(
        literature_subscription_service,
        "ingest_europe_pmc_query",
        lambda connection, query, **kwargs: {
            "query": query,
            "documents_ingested": 0,
            "documents": [],
        },
    )
    created = client.post(
        f"{API}/copilot/literature/subscriptions",
        headers=auth_headers,
        json={
            "name": "Daily binder papers",
            "query": "protein binder design",
            "enabled": True,
            "interval_hours": 24,
            "result_limit": 3,
            "fetch_full_text": True,
            "extract_claims": True,
        },
    )
    assert created.status_code == 200
    item = created.json()["data"]
    assert item["enabled"] is True
    assert item["fetch_full_text"] is True

    listed = client.get(
        f"{API}/copilot/literature/subscriptions",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert any(row["subscription_id"] == item["subscription_id"] for row in listed.json()["data"]["items"])

    run = client.post(
        f"{API}/copilot/literature/subscriptions/{item['subscription_id']}/run",
        headers=auth_headers,
    )
    assert run.status_code == 200
    assert run.json()["data"]["status"] == "completed"


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


def test_server_connection_management_and_compute_queue(client: TestClient, auth_headers: dict[str, str]):
    created = client.post(
        f"{API}/servers",
        headers=auth_headers,
        json={
            "server_name": "External HTTP worker",
            "server_type": "http_worker",
            "base_url": "http://127.0.0.1:9",
            "health_check_endpoint": "/health",
            "capabilities_json": {"roles": ["custom_model"]},
        },
    )
    assert created.status_code == 200
    server = created.json()["data"]
    assert server["server_id"].startswith("server_")
    assert server["capabilities_json"]["roles"] == ["custom_model"]

    patched = client.patch(
        f"{API}/servers/{server['server_id']}",
        headers=auth_headers,
        json={"server_name": "External HTTP worker A", "enabled": False},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["server_name"] == "External HTTP worker A"
    assert patched.json()["data"]["enabled"] is False

    tested = client.post(f"{API}/servers/{server['server_id']}/test-connection", headers=auth_headers)
    assert tested.status_code == 200
    assert tested.json()["data"]["connected"] is False
    assert tested.json()["data"]["server"]["network_status"] == "unavailable"

    queue = client.get(f"{API}/compute-nodes/compute_gpu_local/queue", headers=auth_headers)
    assert queue.status_code == 200
    assert queue.json()["data"]["compute_node"]["compute_node_id"] == "compute_gpu_local"
    assert "active_jobs" in queue.json()["data"]

    drained = client.post(f"{API}/compute-nodes/compute_gpu_local/drain", headers=auth_headers)
    assert drained.status_code == 200
    assert drained.json()["data"]["compute_node"]["status"] == "draining"
    assert drained.json()["data"]["accepting_jobs"] is False


def test_platform_registry_tables_cover_p2_plan(client: TestClient, auth_headers: dict[str, str]):
    dataset = client.post(
        f"{API}/platform-registry/datasets",
        headers=auth_headers,
        json={
            "name": "Round 1 structures",
            "dataset_type": "structure_set",
            "metadata_json": {"source": "test"},
        },
    )
    assert dataset.status_code == 200
    dataset_id = dataset.json()["data"]["dataset_id"]

    benchmark = client.post(
        f"{API}/platform-registry/benchmark-runs",
        headers=auth_headers,
        json={
            "name": "RFdiffusion smoke benchmark",
            "model_plugin_id": "plugin_rfdiffusion",
            "dataset_id": dataset_id,
            "metrics_json": {"success_rate": 1.0},
            "status": "completed",
        },
    )
    assert benchmark.status_code == 200
    assert benchmark.json()["data"]["metrics_json"]["success_rate"] == 1.0

    preset = client.post(
        f"{API}/platform-registry/parameter-presets",
        headers=auth_headers,
        json={
            "name": "Conservative RFdiffusion",
            "model_plugin_id": "plugin_rfdiffusion",
            "parameters_json": {"diffuser.T": 50},
        },
    )
    assert preset.status_code == 200
    assert preset.json()["data"]["parameters_json"]["diffuser.T"] == 50

    template = client.post(
        f"{API}/platform-registry/workflow-templates",
        headers=auth_headers,
        json={
            "name": "Binder route template",
            "template_type": "binder_design",
            "nodes_json": [{"model": "RFdiffusion"}],
            "edges_json": [],
            "tags_json": ["binder"],
        },
    )
    assert template.status_code == 200
    assert template.json()["data"]["nodes_json"][0]["model"] == "RFdiffusion"

    versions = client.get(f"{API}/platform-registry/plugin-versions", headers=auth_headers)
    assert versions.status_code == 200
    assert any(item["model_plugin_id"] == "plugin_rfdiffusion" for item in versions.json()["data"]["items"])


def test_model_parameter_catalog_and_qm_script_import(client: TestClient, auth_headers: dict[str, str]):
    catalog = client.get(
        f"{API}/model-parameter-catalog?model_plugin_id=plugin_proteinmpnn",
        headers=auth_headers,
    )
    assert catalog.status_code == 200
    keys = {item["parameter_key"] for item in catalog.json()["data"]["items"]}
    assert "sampling_temp" in keys

    imported = client.post(
        f"{API}/model-parameter-catalog/import-qm-scripts",
        headers=auth_headers,
    )
    assert imported.status_code == 200
    assert imported.json()["data"]["scripts_imported"] >= 1

    consistency = client.get(
        f"{API}/model-parameter-catalog/consistency?model_plugin_id=plugin_proteinmpnn",
        headers=auth_headers,
    )
    assert consistency.status_code == 200
    assert consistency.json()["data"]["models"]


def test_model_plugin_schema_is_frontend_renderable(client: TestClient, auth_headers: dict[str, str]):
    response = client.get(f"{API}/model-plugins/plugin_rfdiffusion", headers=auth_headers)
    assert response.status_code == 200
    plugin = response.json()["data"]
    assert plugin["container_image"] == "bda/rfdiffusion:1.1.0"
    assert plugin["input_schema_json"]["ports"][0]["name"] == "target_structure"
    assert plugin["output_schema_json"]["ports"][0]["name"] == "backbone_set"
    fields = plugin["parameter_schema_json"]["fields"]
    assert any(field["key"] == "inference.num_designs" and field["type"] == "integer" for field in fields)
    assert any(field["key"] == "diffuser.T" and field["advanced"] is True for field in fields)


def test_create_model_plugin_for_external_model_intake(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        f"{API}/model-plugins",
        headers=auth_headers,
        json={
            "model_name": "Custom Fold Model",
            "model_type": "structure_prediction",
            "provider": "internal",
            "version": "0.1.0",
            "description": "Internal experimental model with a manifest contract.",
            "input_schema_json": {"ports": [{"name": "sequence_set", "type": "fasta"}]},
            "output_schema_json": {"ports": [{"name": "structure_set", "type": "pdb"}]},
            "parameter_schema_json": {"fields": [{"key": "recycles", "type": "integer"}]},
            "resource_requirement_json": {"gpu_count": 1, "min_vram_gb": 24},
            "supported_task_types": ["folding"],
            "supported_file_types": ["fasta", "pdb"],
            "container_image": "bda/custom-fold:0.1.0",
            "command_template": "custom-fold --input {input_manifest} --out {output_dir}",
        },
    )
    assert response.status_code == 200
    plugin = response.json()["data"]
    assert plugin["model_plugin_id"].startswith("plugin_")
    assert plugin["model_name"] == "Custom Fold Model"
    assert plugin["input_schema_json"]["ports"][0]["name"] == "sequence_set"
    assert plugin["resource_requirement_json"]["min_vram_gb"] == 24


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
