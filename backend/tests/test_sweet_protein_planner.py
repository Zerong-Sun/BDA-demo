import io

import pytest
from fastapi.testclient import TestClient

from backend.app.services.sweet_protein_planner import (
    render_rfdiffusion_command,
    validate_rfdiffusion_parameters,
)

API = "/api/v1"


def test_sweet_protein_brief_plan_and_materialize(
    client: TestClient,
    auth_headers: dict[str, str],
):
    brief_response = client.post(
        f"{API}/copilot/research-briefs",
        headers=auth_headers,
        json={
            "project_id": "proj_pd1_0423",
            "title": "AI sweet protein",
            "objective": "Design a food-compatible sweet protein using verified natural scaffolds.",
            "constraints": {"application": "acidic_beverage"},
            "source_material": [
                {
                    "title": "AI甜味蛋白 research seed",
                    "kind": "markdown",
                    "reference_count": 35,
                }
            ],
        },
    )
    assert brief_response.status_code == 200
    brief = brief_response.json()["data"]
    assert brief["constraints_json"]["application"] == "acidic_beverage"
    assert any(item["reference_count"] == 35 for item in brief["source_material_json"])

    source_response = client.post(
        f"{API}/copilot/research-briefs/{brief['research_brief_id']}/sources/markdown",
        headers=auth_headers,
        json={
            "title": "Sweet protein seed.md",
            "content": (
                "# Natural scaffolds\n"
                "Single-chain monellin and brazzein are candidate scaffolds.\n\n"
                "## References\n"
                "https://pubmed.ncbi.nlm.nih.gov/38159314/\n"
                "https://www.rcsb.org/structure/2DS2\n"
            ),
            "source_uri": "upload://Sweet protein seed.md",
        },
    )
    assert source_response.status_code == 200
    source = source_response.json()["data"]
    assert source["chunk_count"] == 2
    assert source["reference_count"] == 2
    assert source["content_hash"]
    updated_source_response = client.post(
        f"{API}/copilot/research-briefs/{brief['research_brief_id']}/sources/markdown",
        headers=auth_headers,
        json={
            "title": "Sweet protein seed.md",
            "content": "# Revised\nUpdated evidence.\nhttps://example.org/revised\n",
            "source_uri": "upload://Sweet protein seed.md",
        },
    )
    assert updated_source_response.status_code == 200
    updated_source = updated_source_response.json()["data"]
    assert updated_source["source_id"] == source["source_id"]
    assert updated_source["document_id"] == source["document_id"]
    assert updated_source["reference_count"] == 1
    source = updated_source
    library_search = client.get(
        f"{API}/copilot/literature?q=Updated%20evidence",
        headers=auth_headers,
    )
    assert library_search.status_code == 200
    assert any(
        item["document_id"] == source["document_id"]
        for item in library_search.json()["data"]["items"]
    )

    plan_response = client.post(
        f"{API}/copilot/research-briefs/{brief['research_brief_id']}/plan",
        headers=auth_headers,
        json={"selected_route": "monellin_redesign"},
    )
    assert plan_response.status_code == 200
    plan = plan_response.json()["data"]
    assert plan["selected_route"] == "monellin_redesign"
    assert len(plan["route_options_json"]) == 4
    assert any(node.get("model_name") == "RFdiffusion" for node in plan["nodes_json"])
    assert "scaffolds" in plan["dossier_json"]
    assert "https://example.org/revised" in plan["dossier_json"]["source_reference_queue"]
    assert plan["version"] == 1

    revised_plan_response = client.post(
        f"{API}/copilot/research-briefs/{brief['research_brief_id']}/plan",
        headers=auth_headers,
        json={"selected_route": "brazzein_redesign"},
    )
    assert revised_plan_response.status_code == 200
    revised_plan = revised_plan_response.json()["data"]
    assert revised_plan["version"] == 2
    assert revised_plan["supersedes_workflow_plan_id"] == plan["workflow_plan_id"]

    sequence_comparison = client.post(
        f"{API}/copilot/research-briefs/{brief['research_brief_id']}/sequence-comparison",
        headers=auth_headers,
        json={"sequences": [
            {"name": "reference", "sequence": "ACDEFGHIK"},
            {"name": "candidate", "sequence": "ACDEYGHIK"},
        ]},
    )
    assert sequence_comparison.status_code == 200
    assert sequence_comparison.json()["data"]["alignments"][0]["identity"] < 1

    detail_response = client.get(
        f"{API}/copilot/research-briefs/{brief['research_brief_id']}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    assert len(detail_response.json()["data"]["findings"]) >= 5
    assert any(
        item.get("source_id") == source["source_id"]
        for item in detail_response.json()["data"]["source_material_json"]
    )

    materialize_response = client.post(
        f"{API}/copilot/workflow-plans/{plan['workflow_plan_id']}/materialize",
        headers=auth_headers,
        json={"selected_route": "brazzein_redesign"},
    )
    assert materialize_response.status_code == 200
    materialized = materialize_response.json()["data"]
    assert materialized["selected_route"] == "brazzein_redesign"
    assert len(materialized["nodes"]) == 9
    rf_node = next(node for node in materialized["nodes"] if node.get("model_name") == "RFdiffusion")
    assert rf_node["parameters_json"]["preserve_disulfides"] is True
    recommendations = client.get(
        f"{API}/copilot/workflow-runs/{materialized['workflow_run_id']}/parameter-recommendations"
        f"?node_run_id={rf_node['node_run_id']}",
        headers=auth_headers,
    )
    assert recommendations.status_code == 200
    assert recommendations.json()["data"]["total"] >= 5
    assert all(
        "source_refs_json" in item
        for item in recommendations.json()["data"]["items"]
    )

    blocked_preview = client.get(
        f"{API}/workflow-node-runs/{rf_node['node_run_id']}/submission-preview",
        headers=auth_headers,
    )
    assert blocked_preview.status_code == 200
    assert blocked_preview.json()["data"]["ready"] is False
    assert any(
        item["code"] == "upstream_not_completed"
        for item in blocked_preview.json()["data"]["blockers"]
    )

    evidence = materialized["nodes"][0]
    prepare = materialized["nodes"][1]
    assert evidence["status"] == "requires_review"
    assert prepare["status"] == "requires_review"
    assert client.post(
        f"{API}/workflow-node-runs/{evidence['node_run_id']}/complete-review",
        headers=auth_headers,
    ).status_code == 200
    assert client.post(
        f"{API}/workflow-node-runs/{prepare['node_run_id']}/complete-review",
        headers=auth_headers,
    ).status_code == 200

    missing_input_preview = client.get(
        f"{API}/workflow-node-runs/{rf_node['node_run_id']}/submission-preview",
        headers=auth_headers,
    )
    assert missing_input_preview.status_code == 200
    assert any(
        item["code"] == "missing_target_structure"
        for item in missing_input_preview.json()["data"]["blockers"]
    )

    foreign_upload = client.post(
        f"{API}/artifacts/upload",
        headers=auth_headers,
        files={"file": ("foreign.pdb", io.BytesIO(b"END\n"), "chemical/x-pdb")},
        data={
            "project_id": "proj_nanocage_0518",
            "artifact_type": "target_structure",
        },
    )
    assert foreign_upload.status_code == 200
    rejected_attach = client.patch(
        f"{API}/workflow-runs/{materialized['workflow_run_id']}/nodes/{rf_node['node_run_id']}",
        headers=auth_headers,
        json={
            "input_files_json": {
                "target_structure": [{
                    "artifact_id": foreign_upload.json()["data"]["artifact_id"],
                }],
            },
        },
    )
    assert rejected_attach.status_code == 403

    pdb_body = (
        "ATOM      1  N   ALA A   1      11.104   6.134  -6.504  1.00  0.00           N\n"
        "END\n"
    )
    upload = client.post(
        f"{API}/artifacts/upload",
        headers=auth_headers,
        files={"file": ("sweet_scaffold.pdb", io.BytesIO(pdb_body.encode()), "chemical/x-pdb")},
        data={
            "project_id": "proj_pd1_0423",
            "workflow_run_id": materialized["workflow_run_id"],
            "artifact_type": "target_structure",
        },
    )
    assert upload.status_code == 200
    artifact_id = upload.json()["data"]["artifact_id"]
    attach = client.patch(
        f"{API}/workflow-runs/{materialized['workflow_run_id']}/nodes/{rf_node['node_run_id']}",
        headers=auth_headers,
        json={"input_files_json": {"target_structure": [{"artifact_id": artifact_id}]}},
    )
    assert attach.status_code == 200

    ready_preview = client.get(
        f"{API}/workflow-node-runs/{rf_node['node_run_id']}/submission-preview",
        headers=auth_headers,
    )
    assert ready_preview.status_code == 200
    preview = ready_preview.json()["data"]
    assert preview["ready"] is True
    assert preview["command"] == "python run.py"
    assert "run_inference.py" in preview["model_command_preview"]
    unconfirmed_submit = client.post(
        f"{API}/workflow-node-runs/{rf_node['node_run_id']}/submit-to-compute",
        headers=auth_headers,
        json={},
    )
    assert unconfirmed_submit.status_code == 400
    assert "node_preview_confirmation_required" in unconfirmed_submit.json()["message"]

    experiment = materialized["nodes"][-1]
    assert experiment["status"] == "waiting_external_result"
    premature_experiment_completion = client.post(
        f"{API}/workflow-node-runs/{experiment['node_run_id']}/complete-review",
        headers=auth_headers,
    )
    assert premature_experiment_completion.status_code == 400
    experiment_plan_response = client.get(
        f"{API}/copilot/workflow-runs/{materialized['workflow_run_id']}/experiment-plan",
        headers=auth_headers,
    )
    assert experiment_plan_response.status_code == 200
    experiment_plan = experiment_plan_response.json()["data"]
    assert len(experiment_plan["steps"]) == 8
    bypass_completion = client.patch(
        f"{API}/copilot/experiment-plans/{experiment_plan['experiment_plan_id']}",
        headers=auth_headers,
        json={"status": "completed"},
    )
    assert bypass_completion.status_code == 409
    first_step = experiment_plan["steps"][0]
    missing_result = client.patch(
        f"{API}/copilot/experiment-plan-steps/{first_step['experiment_plan_step_id']}",
        headers=auth_headers,
        json={"status": "completed"},
    )
    assert missing_result.status_code == 409
    assert "requires_result_artifact" in missing_result.json()["message"]
    template_response = client.get(
        f"{API}/copilot/experiment-plans/{experiment_plan['experiment_plan_id']}/result-template",
        headers=auth_headers,
    )
    assert template_response.status_code == 200
    assert "candidate_id,stage_key,metric" in template_response.text
    workbook_response = client.get(
        f"{API}/copilot/experiment-plans/{experiment_plan['experiment_plan_id']}/result-template?format=xlsx",
        headers=auth_headers,
    )
    assert workbook_response.status_code == 200
    assert workbook_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    sensory_step = next(
        step for step in experiment_plan["steps"] if step["stage_key"] == "sensory"
    )
    blocked_sensory = client.patch(
        f"{API}/copilot/experiment-plan-steps/{sensory_step['experiment_plan_step_id']}",
        headers=auth_headers,
        json={"status": "in_progress"},
    )
    assert blocked_sensory.status_code == 409
    assert "experiment_dependencies_incomplete" in blocked_sensory.json()["message"]
    step_by_key = {step["stage_key"]: step for step in experiment_plan["steps"]}
    completion_order = [
        "expression_and_folding",
        "purification_quality",
        "stability",
        "receptor_function",
        "food_matrix",
        "process",
        "safety_regulatory",
        "sensory",
    ]
    for stage_key in completion_order:
        response = client.patch(
            f"{API}/copilot/experiment-plan-steps/{step_by_key[stage_key]['experiment_plan_step_id']}",
            headers=auth_headers,
            json={
                "status": "completed",
                "result_artifact_id": artifact_id,
                "notes": "Validated result package attached.",
            },
        )
        assert response.status_code == 200, response.text
    completed_experiment_plan = client.get(
        f"{API}/copilot/workflow-runs/{materialized['workflow_run_id']}/experiment-plan",
        headers=auth_headers,
    ).json()["data"]
    assert completed_experiment_plan["status"] == "completed"

    update = client.patch(
        f"{API}/workflow-runs/{materialized['workflow_run_id']}/nodes/{rf_node['node_run_id']}",
        headers=auth_headers,
        json={"parameters_json": {**rf_node["parameters_json"], "inference.num_designs": 321}},
    )
    assert update.status_code == 200
    updated_recommendations = client.get(
        f"{API}/copilot/workflow-runs/{materialized['workflow_run_id']}/parameter-recommendations"
        f"?node_run_id={rf_node['node_run_id']}",
        headers=auth_headers,
    ).json()["data"]["items"]
    num_designs_recommendation = next(
        item for item in updated_recommendations
        if item["parameter_key"] == "inference.num_designs"
    )
    assert num_designs_recommendation["current_value"] == 321
    assert num_designs_recommendation["user_modified"] is True
    assert num_designs_recommendation["differs_from_recommendation"] is True
    stale_submit = client.post(
        f"{API}/workflow-node-runs/{rf_node['node_run_id']}/submit-to-compute",
        headers=auth_headers,
        json={"expected_parameter_checksum": preview["parameter_checksum"]},
    )
    assert stale_submit.status_code == 400
    assert "node_parameters_changed_after_preview" in stale_submit.json()["message"]

    duplicate_materialize = client.post(
        f"{API}/copilot/workflow-plans/{plan['workflow_plan_id']}/materialize",
        headers=auth_headers,
        json={"selected_route": "brazzein_redesign"},
    )
    assert duplicate_materialize.status_code == 400
    assert "workflow_plan_already_materialized" in duplicate_materialize.json()["message"]


def test_research_run_evidence_review_and_export(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    from backend.app.copilot import research

    monkeypatch.setattr(
        research,
        "search_uniprot",
        lambda term, limit=3, reviewed_only=True: {
            "results": [{
                "accession": f"ACC_{term}",
                "protein_name": term.title(),
                "url": f"https://example.test/uniprot/{term}",
                "function_comments": ["Curated sweet-protein record."],
            }]
        },
    )
    monkeypatch.setattr(
        research,
        "search_pdb",
        lambda term, limit=5: {
            "results": [{
                "pdb_id": "TEST",
                "title": "Human sweet receptor structure",
                "url": "https://example.test/pdb/TEST",
                "experimental_method": "cryo-EM",
            }]
        },
    )
    monkeypatch.setattr(
        research,
        "search_literature",
        lambda term, limit=8: {
            "results": [{
                "doi": "10.1000/sweet",
                "title": "Sweet-protein evidence",
                "url": "https://example.test/paper",
                "abstract": "Binding, receptor activation, and sensory evidence are distinct.",
                "year": 2026,
                "is_open_access": True,
            }]
        },
    )
    brief = client.post(
        f"{API}/copilot/research-briefs",
        headers=auth_headers,
        json={
            "project_id": "proj_pd1_0423",
            "title": "Evidence run",
            "objective": "Build a traceable sweet-protein evidence dossier for design planning.",
        },
    ).json()["data"]
    run_response = client.post(
        f"{API}/copilot/research-briefs/{brief['research_brief_id']}/research-runs",
        headers=auth_headers,
    )
    assert run_response.status_code == 200
    run_id = run_response.json()["data"]["research_run_id"]
    started = client.post(
        f"{API}/copilot/research-runs/{run_id}/start",
        headers=auth_headers,
    )
    assert started.status_code == 200
    assert started.json()["data"]["status"] == "completed"
    detail = client.get(
        f"{API}/copilot/research-runs/{run_id}",
        headers=auth_headers,
    ).json()["data"]
    assert detail["result_summary_json"]["evidence_count"] >= 10
    evidence = detail["evidence"][0]
    reviewed = client.patch(
        f"{API}/copilot/research-evidence/{evidence['evidence_link_id']}",
        headers=auth_headers,
        json={"review_status": "accepted"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["data"]["review_status"] == "accepted"
    exported = client.get(
        f"{API}/copilot/research-briefs/{brief['research_brief_id']}/dossier-export?format=json",
        headers=auth_headers,
    )
    assert exported.status_code == 200
    assert exported.json()["brief"]["research_brief_id"] == brief["research_brief_id"]


def test_rfdiffusion_parameters_are_validated_and_allowlisted():
    parameters = {
        "inference.num_designs": 50,
        "diffuser.partial_T": 10,
        "diffuser.T": 50,
        "denoiser.noise_scale_ca": 0.5,
        "denoiser.noise_scale_frame": 0.5,
        "contigmap.contigs": "[A1-90]",
        "contigmap.inpaint_seq": "[A20-25]",
        "potentials.guiding_potentials": ["type:monomer_ROG,weight:1"],
        "untrusted.command": "rm -rf /",
    }
    validation = validate_rfdiffusion_parameters(parameters)
    assert validation["valid"] is True
    assert validation["warnings"][0]["parameter"] == "untrusted.command"
    command = render_rfdiffusion_command(parameters)
    assert "inference.num_designs=50" in command
    assert "contigmap.inpaint_seq" in command
    assert "potentials.guiding_potentials" in command
    assert "untrusted.command" not in command
    assert "rm -rf" not in command

    with pytest.raises(ValueError, match="invalid_rfdiffusion_parameters"):
        render_rfdiffusion_command({
            **parameters,
            "inference.num_designs": 0,
        })
