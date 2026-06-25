import json

import pytest

from backend.app.config import ARTIFACTS_ROOT
from backend.app.db import connect, release_connection
from backend.app.repositories import registry
from backend.app.services import job_service


@pytest.fixture
def db():
    connection = connect()
    try:
        yield connection
        connection.commit()
    finally:
        release_connection(connection)


def test_prepare_job_workspace_writes_input_manifest(db):
    node = {
        "node_run_id": "node_mpnn",
        "workflow_run_id": "run_pd1_round1",
        "model_name": "ProteinMPNN",
        "parameters_json": {"num_seq_per_target": 2},
        "input_files_json": {},
    }
    job = job_service.create_job(
        db,
        workflow_run_id="run_pd1_round1",
        node_run_id="node_mpnn",
        plugin_id="plugin_proteinmpnn",
    )
    plugin = registry.get_model_plugin(db, "plugin_proteinmpnn")

    workspace = job_service.prepare_job_workspace(db, job=job, node=node, plugin=plugin)
    manifest_path = ARTIFACTS_ROOT / "jobs" / job["job_id"] / "input" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    assert workspace["input_dir"].endswith("/input")
    assert manifest["job_id"] == job["job_id"]
    assert manifest["plugin_id"] == "plugin_proteinmpnn"
    assert manifest["parameters"]["num_seq_per_target"] == 2


def test_collect_job_outputs_registers_artifacts(db):
    job = job_service.create_job(
        db,
        workflow_run_id="run_pd1_round1",
        node_run_id="node_mpnn",
        plugin_id="plugin_proteinmpnn",
    )
    output_dir = ARTIFACTS_ROOT / "jobs" / job["job_id"] / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    fasta = output_dir / "designed.fasta"
    fasta.write_text(">design_1\nACDEFGHIKLMNPQRSTVWY\n")
    scores = output_dir / "scores.csv"
    scores.write_text("candidate_id,score\ndesign_1,-1.2\n")
    (output_dir / "manifest.json").write_text(json.dumps({
        "status": "completed",
        "outputs": {
            "sequence_set": [{"path": "/output/designed.fasta", "format": "fasta"}],
            "score_table": [{"path": "/output/scores.csv", "format": "csv"}],
        },
        "metrics": {"designed": 1},
    }))

    result = job_service.collect_job_outputs(db, job["job_id"])
    refreshed = job_service.get_job(db, job["job_id"])

    assert result["manifest_found"] is True
    assert result["artifacts"][0]["artifact_type"] == "sequence_set"
    assert result["metrics"]["designed"] == 1
    assert refreshed["output_artifacts"]["artifacts"][0]["artifact_id"] == result["artifacts"][0]["artifact_id"]

    repeated = job_service.collect_job_outputs(db, job["job_id"])
    assert repeated["artifacts"][0]["artifact_id"] == result["artifacts"][0]["artifact_id"]


def test_collect_job_outputs_fails_when_manifest_is_missing(db):
    job = job_service.create_job(
        db,
        workflow_run_id="run_pd1_round1",
        node_run_id="node_mpnn",
        plugin_id="plugin_proteinmpnn",
    )

    result = job_service.collect_job_outputs(db, job["job_id"])
    refreshed = job_service.get_job(db, job["job_id"])

    assert result["contract_valid"] is False
    assert result["contract_errors"] == ["missing_output_manifest"]
    assert refreshed["status"] == "failed"
    assert refreshed["error_message"] == "output_contract_failed:missing_output_manifest"
