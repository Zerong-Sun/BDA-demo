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
    (output_dir / "manifest.json").write_text(json.dumps({
        "status": "completed",
        "outputs": {
            "sequence_set": [{"path": "/output/designed.fasta", "format": "fasta"}],
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


def test_collect_predicted_structure_inserts_folded_candidate(db):
    job = job_service.create_job(
        db,
        workflow_run_id="run_pd1_round1",
        node_run_id="node_af2",
        plugin_id="plugin_alphafold2",
    )
    output_dir = ARTIFACTS_ROOT / "jobs" / job["job_id"] / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdb = output_dir / "af2_smoke_model_4_ptm_seed_0_unrelaxed.pdb"
    pdb.write_text(
        "ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00  1.00           C\nEND\n",
        encoding="utf-8",
    )
    (output_dir / "manifest.json").write_text(json.dumps({
        "status": "completed",
        "outputs": {
            "predicted_structure": [{
                "path": "af2_smoke_model_4_ptm_seed_0_unrelaxed.pdb",
                "format": "pdb",
                "artifact_type": "predicted_structure",
                "display_name": "af2_smoke_model_4_ptm_seed_0_unrelaxed.pdb",
                "metadata": {
                    "candidate_id": "af2_smoke_candidate",
                    "family": "pd1",
                    "plddt": 88.4,
                },
            }],
        },
        "metrics": {"folded": 1},
    }))

    result = job_service.collect_job_outputs(db, job["job_id"])
    candidate = db.execute(
        "SELECT * FROM candidates WHERE candidate_id = ?",
        ("cand_af2_smoke_candidate",),
    ).fetchone()

    assert result["manifest_found"] is True
    assert result["artifacts"][0]["artifact_type"] == "predicted_structure"
    assert candidate is not None
    assert candidate["status"] == "folded"
    assert candidate["plddt"] == 88.4
    assert candidate["complex_file_path"].endswith("af2_smoke_model_4_ptm_seed_0_unrelaxed.pdb")


def test_collect_job_outputs_preserves_nested_output_paths(db):
    job = job_service.create_job(
        db,
        workflow_run_id="run_pd1_round1",
        node_run_id="node_af2",
        plugin_id="plugin_alphafold2",
    )
    output_dir = ARTIFACTS_ROOT / "jobs" / job["job_id"] / "output"
    first = output_dir / "candidate_a" / "model.pdb"
    second = output_dir / "candidate_b" / "model.pdb"
    first.parent.mkdir(parents=True, exist_ok=True)
    second.parent.mkdir(parents=True, exist_ok=True)
    first.write_text("ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00  1.00           C\nEND\n")
    second.write_text("ATOM      1  CA  GLY A   1       1.000   1.000   1.000  1.00  1.00           C\nEND\n")
    (output_dir / "manifest.json").write_text(json.dumps({
        "outputs": {
            "predicted_structure": [
                {"path": "candidate_a/model.pdb", "format": "pdb", "metadata": {"candidate_id": "nested_a"}},
                {"path": "candidate_b/model.pdb", "format": "pdb", "metadata": {"candidate_id": "nested_b"}},
            ],
        },
        "metrics": {"folded": 2},
    }))

    result = job_service.collect_job_outputs(db, job["job_id"])
    paths = {artifact["storage_uri"] for artifact in result["artifacts"]}
    metadata_paths = {artifact["metadata_json"]["output_relative_path"] for artifact in result["artifacts"]}

    assert paths == {
        f"artifact://jobs/{job['job_id']}/outputs/candidate_a/model.pdb",
        f"artifact://jobs/{job['job_id']}/outputs/candidate_b/model.pdb",
    }
    assert metadata_paths == {"candidate_a/model.pdb", "candidate_b/model.pdb"}
