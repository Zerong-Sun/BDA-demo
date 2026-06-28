from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
ARTIFACTS_ROOT = BACKEND_ROOT / "artifacts"
DELIVERABLE_ROOT = REPO_ROOT / "deliverables" / "sweet_protein_rfdiffusion_100x2_20260626"

PROJECT_ID = "proj_sweetprotein_rfdiffusion_100x2_160d28"
PROJECT_NAME = "SweetProtein_RFdiffusion_100x2_20260626"
TASK_ID = f"task_{PROJECT_ID}_round1"

ROUTES: dict[str, dict[str, Any]] = {
    "monellin": {
        "label": "Monellin route",
        "manifest_key": "monellin_redesign",
        "input_path": "monellin/2O9U_monellin_B50_A44_for_linker_design.pdb",
        "input_artifact_id": "art_79d1e3c207524d58",
        "job_id": "job_9ca5d2d649a9",
        "output_prefix": "monellin_design_",
        "rf_node_name": "RFdiffusion Monellin backbone generation",
        "mpnn_node_name": "ProteinMPNN sequence design for Monellin backbones",
        "position": {"x": 120, "y": 120},
    },
    "brazzein": {
        "label": "Brazzein route",
        "manifest_key": "brazzein_redesign",
        "input_path": "brazzein/4HE7_brazzein_clean_A1-54.pdb",
        "input_artifact_id": "art_f10c683ebad34b80",
        "job_id": "job_4de7a7ebdc11",
        "output_prefix": "brazzein_design_",
        "rf_node_name": "RFdiffusion Brazzein partial-diffusion generation",
        "mpnn_node_name": "ProteinMPNN sequence design for Brazzein backbones",
        "position": {"x": 120, "y": 340},
    },
}

SCRIPT_ASSETS = [
    ("script_sweet_monellin_submit", "plugin_rfdiffusion", "sweetprotein/monellin/submit.lsf", "monellin/submit.lsf"),
    ("script_sweet_brazzein_submit", "plugin_rfdiffusion", "sweetprotein/brazzein/submit.lsf", "brazzein/submit.lsf"),
    (
        "script_sweet_proteinmpnn_5seq",
        "plugin_proteinmpnn",
        "sweetprotein/proteinmpnn/submit_proteinmpnn_5seq.lsf",
        "proteinmpnn/submit_proteinmpnn_5seq.lsf",
    ),
    (
        "script_sweet_proteinmpnn_summary",
        "plugin_proteinmpnn",
        "sweetprotein/proteinmpnn/summarize_mpnn_outputs.py",
        "proteinmpnn/summarize_mpnn_outputs.py",
    ),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _script_language(path: Path) -> str:
    if path.suffix == ".py":
        return "python"
    if path.suffix in {".lsf", ".sh"}:
        return "bash"
    return path.suffix.removeprefix(".") or "text"


def _artifact_row(
    connection: sqlite3.Connection,
    *,
    artifact_id: str,
    workflow_run_id: str | None,
    node_run_id: str | None,
    artifact_type: str,
    fmt: str,
    storage_uri: str,
    display_name: str,
    size_bytes: int,
    checksum: str,
    metadata: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO artifacts (
            artifact_id, project_id, workflow_run_id, node_run_id, artifact_type,
            format, storage_uri, display_name, size_bytes, checksum, metadata_json,
            created_by, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'system', ?)
        """,
        (
            artifact_id,
            PROJECT_ID,
            workflow_run_id,
            node_run_id,
            artifact_type,
            fmt,
            storage_uri,
            display_name,
            size_bytes,
            checksum,
            _json(metadata),
            _now(),
        ),
    )


def _seed_script_assets(connection: sqlite3.Connection) -> None:
    for script_asset_id, model_plugin_id, relative_path, source_rel in SCRIPT_ASSETS:
        source_path = DELIVERABLE_ROOT / source_rel
        content = source_path.read_bytes() if source_path.exists() else b""
        source_id = f"source_{script_asset_id}"
        content_hash = _sha256_bytes(content or relative_path.encode("utf-8"))
        connection.execute(
            """
            INSERT OR REPLACE INTO research_sources (
                source_id, source_type, title, uri, content_hash,
                metadata_json, status, last_ingested_at
            ) VALUES (?, 'script', ?, ?, ?, ?, 'active', ?)
            """,
            (
                source_id,
                source_path.name or relative_path,
                f"deliverables/sweet_protein_rfdiffusion_100x2_20260626/{source_rel}",
                content_hash,
                _json({"project_id": PROJECT_ID, "seeded": True}),
                _now(),
            ),
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO script_assets (
                script_asset_id, source_id, model_plugin_id, relative_path, language,
                scheduler, content_hash, resource_config_json, environment_json,
                input_hints_json, output_hints_json, parse_warnings_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, '{}', '{}', '[]', '[]', '[]', 'active')
            """,
            (
                script_asset_id,
                source_id,
                model_plugin_id,
                relative_path,
                _script_language(source_path),
                "LSF" if source_path.suffix == ".lsf" else None,
                content_hash,
            ),
        )


def _seed_route(connection: sqlite3.Connection, family: str, cfg: dict[str, Any], project_manifest: dict[str, Any]) -> None:
    route_manifest = project_manifest.get("routes", {}).get(cfg["manifest_key"], {})
    run_id = route_manifest.get("workflow_run_id")
    rf_node_id = route_manifest.get("rf_node_run_id")
    if not run_id or not rf_node_id:
        return

    target_node_id = f"node_{family}_scaffold_input"
    mpnn_node_id = f"node_{family}_proteinmpnn_5seq"
    fold_node_id = f"node_{family}_structure_prediction"
    score_node_id = f"node_{family}_developability_scoring"
    review_node_id = f"node_{family}_candidate_review"
    x0 = int(cfg["position"]["x"])
    y0 = int(cfg["position"]["y"])
    lane_positions = {
        target_node_id: {"x": x0 - 40, "y": y0},
        rf_node_id: {"x": x0 + 260, "y": y0},
        mpnn_node_id: {"x": x0 + 560, "y": y0},
        fold_node_id: {"x": x0 + 560, "y": y0 + 230},
        score_node_id: {"x": x0 + 260, "y": y0 + 230},
        review_node_id: {"x": x0 - 40, "y": y0 + 230},
    }
    node_layout = [
        {"node_run_id": node_id, "position": position}
        for node_id, position in lane_positions.items()
    ]
    edge_specs = [
        (target_node_id, "target_structure", rf_node_id, "target_structure"),
        (rf_node_id, "backbone_set", mpnn_node_id, "backbone_set"),
        (mpnn_node_id, "sequence_set", fold_node_id, "sequence_set"),
        (fold_node_id, "predicted_structure", score_node_id, "predicted_structure"),
        (score_node_id, "score_table", review_node_id, "score_table"),
    ]
    input_manifest = _read_json(DELIVERABLE_ROOT / family / "input_manifest.json")
    parameters = dict(input_manifest.get("parameters") or {})
    parameters.setdefault("scaffold", family)
    input_artifact_id = cfg["input_artifact_id"]

    connection.execute(
        """
        INSERT OR REPLACE INTO workflow_runs (
            workflow_run_id, task_id, status, start_time, end_time, compute_resource,
            summary_metrics_json, layout_json, output_directory
        ) VALUES (?, ?, 'running', '2026-06-26T00:00:00Z', NULL, 'remote_lsf', ?, ?, ?)
        """,
        (
            run_id,
            TASK_ID,
            _json({
                "route": family,
                "generated_backbones": 100,
                "next_step": "ProteinMPNN 5 sequences per backbone",
                "workflow_stage": "sequence_design",
            }),
            _json({
                "nodes": node_layout,
                "edges": [
                    {"source": source, "source_port": source_port, "target": target, "target_port": target_port, "edge_type": "data"}
                    for source, source_port, target, target_port in edge_specs
                ],
            }),
            f"backend/artifacts/jobs/{cfg['job_id']}/output",
        ),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO workflow_node_runs (
            node_run_id, workflow_run_id, node_type, node_name, status, model_name,
            model_version, input_files_json, output_files_json, parameters_json,
            metrics_json, logs, position_json
        ) VALUES (?, ?, 'target_intake', ?, 'completed', NULL, NULL, ?, ?, ?, ?, ?, ?)
        """,
        (
            target_node_id,
            run_id,
            f"{cfg['label']} scaffold input",
            _json({"target_structure": [{"artifact_id": input_artifact_id, "port": "target_structure"}]}),
            _json([input_artifact_id]),
            _json({"route": family, "input_artifact_id": input_artifact_id}),
            _json({"inputs_confirmed": 1}),
            "Curated scaffold input staged for RFdiffusion.",
            _json(lane_positions[target_node_id]),
        ),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO workflow_node_runs (
            node_run_id, workflow_run_id, node_type, node_name, status, model_name,
            model_version, input_files_json, output_files_json, parameters_json,
            metrics_json, logs, position_json
        ) VALUES (?, ?, 'backbone_generation', ?, 'completed', 'RFdiffusion', '1.1.0', ?, '[]', ?, ?, ?, ?)
        """,
        (
            rf_node_id,
            run_id,
            cfg["rf_node_name"],
            _json({"target_structure": [{"artifact_id": input_artifact_id, "port": "target_structure"}]}),
            _json(parameters),
            _json({"backbone_count": 100}),
            "Seeded from completed local RFdiffusion route output.",
            _json(lane_positions[rf_node_id]),
        ),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO workflow_node_runs (
            node_run_id, workflow_run_id, node_type, node_name, status, model_name,
            model_version, input_files_json, output_files_json, parameters_json,
            metrics_json, logs, position_json
        ) VALUES (?, ?, 'sequence_generation', ?, 'not_started', 'ProteinMPNN', '1.0.0', ?, '[]', ?, '{}', ?, ?)
        """,
        (
            mpnn_node_id,
            run_id,
            cfg["mpnn_node_name"],
            _json({"backbone_set": [{"source_node_run_id": rf_node_id, "source_port": "backbone_set"}]}),
            _json({
                "num_seq_per_target": 5,
                "pdb_path_chains": "A",
                "sampling_temp": "0.2",
                "batch_size": 1,
                "seed": 37,
                "script_asset_id": "script_sweet_proteinmpnn_5seq",
            }),
            "Ready to submit ProteinMPNN using the archived 5-sequences-per-backbone LSF script.",
            _json(lane_positions[mpnn_node_id]),
        ),
    )
    downstream_nodes = [
        (
            fold_node_id,
            "fold_prediction",
            f"Structure prediction for {cfg['label']} MPNN designs",
            "AlphaFold2",
            "2.3.0",
            {"sequence_set": [{"source_node_run_id": mpnn_node_id, "source_port": "sequence_set"}]},
            {
                "route": family,
                "planned": 500,
                "current": 0,
                "estimate_unit": "models",
                "input_sequence_set": "ProteinMPNN sequence_set",
                "folding_metrics": ["plddt", "ptm", "predicted_aligned_error"],
                "recommended_after": "ProteinMPNN",
            },
            lane_positions[fold_node_id],
            "Ready for fold prediction from ProteinMPNN sequence_set outputs; expected metrics include pLDDT.",
        ),
        (
            score_node_id,
            "scoring",
            f"Developability scoring for {cfg['label']} designs",
            "BDA developability filters",
            "1.0.0",
            {"predicted_structure": [{"source_node_run_id": fold_node_id, "source_port": "predicted_structure"}]},
            {"route": family, "planned": 500, "current": 0, "estimate_unit": "designs", "filters": ["aggregation", "solubility", "charge_patch", "pLDDT"]},
            lane_positions[score_node_id],
            "Pending folded structures.",
        ),
        (
            review_node_id,
            "selection",
            f"Candidate review and batch download for {cfg['label']}",
            "BDA candidate table",
            "1.0.0",
            {"score_table": [{"source_node_run_id": score_node_id, "source_port": "score_table"}]},
            {"route": family, "decision_gate": "select candidates for assay planning"},
            lane_positions[review_node_id],
            "Pending scored candidate table.",
        ),
    ]
    for node_id, node_type, node_name, model_name, model_version, input_files, node_params, position, logs in downstream_nodes:
        connection.execute(
            """
            INSERT OR REPLACE INTO workflow_node_runs (
                node_run_id, workflow_run_id, node_type, node_name, status, model_name,
                model_version, input_files_json, output_files_json, parameters_json,
                metrics_json, logs, position_json
            ) VALUES (?, ?, ?, ?, 'not_started', ?, ?, ?, '[]', ?, '{}', ?, ?)
            """,
            (
                node_id,
                run_id,
                node_type,
                node_name,
                model_name,
                model_version,
                _json(input_files),
                _json(node_params),
                logs,
                _json(position),
            ),
        )
    connection.execute("DELETE FROM workflow_edges WHERE workflow_run_id = ?", (run_id,))
    for source, source_port, target, target_port in edge_specs:
        connection.execute(
            """
            INSERT OR REPLACE INTO workflow_edges (
                edge_id, workflow_run_id, source_node_run_id, source_port,
                target_node_run_id, target_port, edge_type, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, 'data', ?)
            """,
            (
                f"edge_{source}_{target}",
                run_id,
                source,
                source_port,
                target,
                target_port,
                _json({"seeded": True, "route": family}),
            ),
        )

    input_path = DELIVERABLE_ROOT / cfg["input_path"]
    if input_path.exists():
        _artifact_row(
            connection,
            artifact_id=input_artifact_id,
            workflow_run_id=run_id,
            node_run_id=rf_node_id,
            artifact_type="target_structure",
            fmt="pdb",
            storage_uri=f"artifact://deliverables/sweet_protein_rfdiffusion_100x2_20260626/{cfg['input_path']}",
            display_name=input_path.name,
            size_bytes=input_path.stat().st_size,
            checksum=_sha256_file(input_path),
            metadata={"route": family, "seeded": True, "source": "deliverable_input"},
        )

    output_dir = ARTIFACTS_ROOT / "jobs" / cfg["job_id"] / "output"
    output_manifest = _read_json(output_dir / "manifest.json")
    connection.execute(
        """
        INSERT OR REPLACE INTO jobs (
            job_id, workflow_run_id, node_run_id, compute_node_id, status,
            plugin_id, input_artifacts, output_artifacts, logs, external_id,
            created_at, finished_at
        ) VALUES (?, ?, ?, NULL, ?, 'plugin_rfdiffusion', ?, ?, ?, NULL, ?, ?)
        """,
        (
            cfg["job_id"],
            run_id,
            rf_node_id,
            "completed" if output_manifest else "archived",
            _json({"target_structure": [{"artifact_id": input_artifact_id}]}),
            _json({"manifest_found": bool(output_manifest), "manifest": output_manifest, "metrics": output_manifest.get("metrics", {})}),
            "Seeded local RFdiffusion output record.",
            _now(),
            _now(),
        ),
    )

    artifact_ids: list[str] = []
    for pdb in sorted(output_dir.glob(f"{cfg['output_prefix']}*.pdb")):
        artifact_id = "art_" + hashlib.sha256(f"{cfg['job_id']}:{pdb.name}".encode("utf-8")).hexdigest()[:16]
        relative_path = f"jobs/{cfg['job_id']}/outputs/{pdb.name}"
        _artifact_row(
            connection,
            artifact_id=artifact_id,
            workflow_run_id=run_id,
            node_run_id=rf_node_id,
            artifact_type="backbone_set",
            fmt="pdb",
            storage_uri=f"artifact://{relative_path}",
            display_name=pdb.name,
            size_bytes=pdb.stat().st_size,
            checksum=_sha256_file(pdb),
            metadata={"route": family, "source_job_id": cfg["job_id"], "source_port": "backbone_set"},
        )
        artifact_ids.append(artifact_id)
        candidate_id = f"cand_{pdb.stem}"
        connection.execute(
            """
            INSERT OR REPLACE INTO candidates (
                candidate_id, project_id, task_id, workflow_run_id, family, sequence,
                structure_file_path, complex_file_path, interface_score, pred_kd,
                plddt, interface_pae, rosetta_score, interface_energy, clash_count,
                buried_sasa, solubility_score, aggregation_risk, expression_risk,
                status, decision, next_action
            ) VALUES (?, ?, ?, ?, ?, NULL, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                      'generated_backbone', 'Needs sequence design and scoring',
                      'Run ProteinMPNN with 5 sequences per backbone, then fold and score selected designs.')
            """,
            (candidate_id, PROJECT_ID, TASK_ID, run_id, family, relative_path),
        )
    connection.execute(
        "UPDATE workflow_node_runs SET output_files_json = ? WHERE node_run_id = ?",
        (_json(artifact_ids), rf_node_id),
    )


def seed_sweet_protein_project(connection: sqlite3.Connection) -> None:
    if not DELIVERABLE_ROOT.exists():
        return

    project_manifest = _read_json(DELIVERABLE_ROOT / "project_manifest.json")
    now = _now()
    connection.execute(
        """
        INSERT OR REPLACE INTO projects (
            project_id, project_name, project_type, status, owner_id,
            organization_id, summary, created_at, updated_at
        ) VALUES (?, ?, 'sweet_protein_design', 'active', 'demo-user',
                  COALESCE((SELECT organization_id FROM projects WHERE project_id = ?), 'org_default'),
                  ?, COALESCE((SELECT created_at FROM projects WHERE project_id = ?), ?), ?)
        """,
        (
            PROJECT_ID,
            PROJECT_NAME,
            PROJECT_ID,
            "Two-route sweet-protein RFdiffusion project with Monellin and Brazzein backbone generation, archived inputs, LSF scripts, and downstream ProteinMPNN sequence-design plan.",
            PROJECT_ID,
            now,
            now,
        ),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO design_tasks (
            task_id, project_id, task_type, objective, constraints_json,
            model_route_json, status, created_by
        ) VALUES (?, ?, 'sweet_protein_design', ?, ?, ?, 'running', 'demo-user')
        """,
        (
            TASK_ID,
            PROJECT_ID,
            "Generate 100 Monellin-route and 100 Brazzein-route RFdiffusion backbones, then design 5 ProteinMPNN sequences per backbone for folding and scoring.",
            _json({"routes": ["monellin", "brazzein"], "sequences_per_backbone": 5, "cluster": "SUSTech LSF"}),
            _json(["rfdiffusion_monellin", "rfdiffusion_brazzein", "proteinmpnn_5seq", "folding", "scoring", "candidate_review"]),
        ),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO targets (
            target_id, project_id, target_name, target_type, pdb_id, chain_ids,
            sequence, structure_file_path, cleaned_structure_file_path,
            epitope_residues, metadata_json
        ) VALUES (?, ?, ?, 'sweet_protein_scaffold', ?, ?, NULL, ?, ?, NULL, ?)
        """,
        (
            "target_sweetprotein_monellin",
            PROJECT_ID,
            "Monellin single-chain redesign input",
            "2O9U",
            "A,B",
            "deliverables/sweet_protein_rfdiffusion_100x2_20260626/monellin/2O9U_monellin_B50_A44_for_linker_design.pdb",
            "deliverables/sweet_protein_rfdiffusion_100x2_20260626/monellin/2O9U_monellin_B50_A44_for_linker_design.pdb",
            _json({"route": "monellin", "seeded": True}),
        ),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO targets (
            target_id, project_id, target_name, target_type, pdb_id, chain_ids,
            sequence, structure_file_path, cleaned_structure_file_path,
            epitope_residues, metadata_json
        ) VALUES (?, ?, ?, 'sweet_protein_scaffold', ?, ?, NULL, ?, ?, NULL, ?)
        """,
        (
            "target_sweetprotein_brazzein",
            PROJECT_ID,
            "Brazzein partial-diffusion input",
            "4HE7",
            "A",
            "deliverables/sweet_protein_rfdiffusion_100x2_20260626/brazzein/4HE7_brazzein_clean_A1-54.pdb",
            "deliverables/sweet_protein_rfdiffusion_100x2_20260626/brazzein/4HE7_brazzein_clean_A1-54.pdb",
            _json({"route": "brazzein", "seeded": True}),
        ),
    )

    _seed_script_assets(connection)
    for family, cfg in ROUTES.items():
        _seed_route(connection, family, cfg, project_manifest)

    user = connection.execute("SELECT user_id FROM users WHERE username = 'admin'").fetchone()
    if user is not None:
        connection.execute(
            "INSERT OR IGNORE INTO project_members (project_id, user_id, role) VALUES (?, ?, 'owner')",
            (PROJECT_ID, user["user_id"]),
        )


def main() -> None:
    db_path = BACKEND_ROOT / "db" / "bda.sqlite3"
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        seed_sweet_protein_project(connection)
        connection.commit()
    finally:
        connection.close()
    print(f"Seeded sweet protein project into {db_path}")


if __name__ == "__main__":
    main()
