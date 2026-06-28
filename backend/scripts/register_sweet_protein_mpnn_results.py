from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.job_service import collect_job_outputs  # noqa: E402

DB_PATH = ROOT / "db" / "bda.sqlite3"
SOURCE_JOB_ID = "3860487"
SOURCE_DIR = ROOT / "artifacts" / "jobs" / "job_manual_mpnn_3860487" / "output"
PROJECT_ID = "proj_sweetprotein_rfdiffusion_100x2_160d28"

ROUTES = {
    "monellin": {
        "workflow_run_id": "run_proj_sweetprotein_rfdiffusion_100x2_160d28_449a8216",
        "node_run_id": "node_monellin_proteinmpnn_5seq",
        "job_id": "job_manual_mpnn_3860487_monellin",
    },
    "brazzein": {
        "workflow_run_id": "run_proj_sweetprotein_rfdiffusion_100x2_160d28_bbe4a091",
        "node_run_id": "node_brazzein_proteinmpnn_5seq",
        "job_id": "job_manual_mpnn_3860487_brazzein",
    },
}

TASK_ID = f"task_{PROJECT_ID}_round1"

SCORE_RE = re.compile(r"(?:score|global_score)=(-?\d+(?:\.\d+)?)")


def read_fasta(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    header: str | None = None
    chunks: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                records[header] = "".join(chunks)
            header = line[1:]
            chunks = []
        else:
            chunks.append(line)
    if header is not None:
        records[header] = "".join(chunks)
    return records


def score_from_header(header: str) -> float | None:
    match = SCORE_RE.search(header)
    return float(match.group(1)) if match else None


def write_route_outputs(route: str, cfg: dict[str, str], records: list[dict[str, Any]], fasta_records: dict[str, str]) -> None:
    output_dir = ROOT / "artifacts" / "jobs" / cfg["job_id"] / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    fasta_path = output_dir / f"{route}_mpnn5_designs.fasta"
    score_path = output_dir / f"{route}_mpnn5_scores.csv"
    run_path = output_dir / f"{route}_mpnn5_run.json"

    with fasta_path.open("w", encoding="utf-8") as handle:
        for record in records:
            design_id = str(record["design_id"])
            sequence = fasta_records.get(design_id, "")
            if not sequence:
                continue
            handle.write(f">{design_id}\n")
            for start in range(0, len(sequence), 60):
                handle.write(sequence[start:start + 60] + "\n")

    with score_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["design_id", "backbone", "sequence_index", "sequence_length", "mpnn_score", "source_header"],
        )
        writer.writeheader()
        for record in records:
            writer.writerow({
                "design_id": record["design_id"],
                "backbone": record["backbone"],
                "sequence_index": record["sequence_index"],
                "sequence_length": record["sequence_length"],
                "mpnn_score": score_from_header(str(record.get("source_header") or "")),
                "source_header": record.get("source_header") or "",
            })

    run_payload = {
        "source_lsf_job_id": SOURCE_JOB_ID,
        "route": route,
        "sequence_count": len(records),
        "backbone_count": len({record["backbone"] for record in records}),
        "records": records,
    }
    run_path.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "outputs": {
                    "sequence_set": [
                        {
                            "path": fasta_path.name,
                            "format": "fasta",
                            "artifact_type": "sequence_set",
                            "display_name": fasta_path.name,
                            "metadata": {"route": route, "source_lsf_job_id": SOURCE_JOB_ID},
                        }
                    ],
                    "score_table": [
                        {
                            "path": score_path.name,
                            "format": "csv",
                            "artifact_type": "score_table",
                            "display_name": score_path.name,
                            "metadata": {"route": route, "source_lsf_job_id": SOURCE_JOB_ID},
                        }
                    ],
                    "run_manifest": [
                        {
                            "path": run_path.name,
                            "format": "json",
                            "artifact_type": "manifest",
                            "display_name": run_path.name,
                            "metadata": {"route": route, "source_lsf_job_id": SOURCE_JOB_ID},
                        }
                    ],
                },
                "metrics": {
                    "designed": len(records),
                    "backbone_count": len({record["backbone"] for record in records}),
                    "sequences_per_backbone": 5,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def upsert_job(connection: sqlite3.Connection, cfg: dict[str, str], logs: str) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO jobs (
            job_id, workflow_run_id, node_run_id, compute_node_id, status,
            plugin_id, input_artifacts, output_artifacts, logs, error_message,
            external_id, started_at, finished_at
        ) VALUES (?, ?, ?, 'compute_gpu_local', 'collecting_outputs',
                  'plugin_proteinmpnn', '{}', '{}', ?, NULL, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (cfg["job_id"], cfg["workflow_run_id"], cfg["node_run_id"], logs, SOURCE_JOB_ID),
    )


def upsert_sequence_candidates(
    connection: sqlite3.Connection,
    *,
    route: str,
    cfg: dict[str, str],
    records: list[dict[str, Any]],
    fasta_records: dict[str, str],
) -> None:
    for record in records:
        design_id = str(record["design_id"])
        backbone = str(record["backbone"])
        source_header = str(record.get("source_header") or "")
        score = score_from_header(source_header)
        sequence = fasta_records.get(design_id, "")
        sequence_index = int(record.get("sequence_index") or 0)
        candidate_id = f"cand_{design_id}"
        connection.execute(
            """
            INSERT OR REPLACE INTO candidates (
                candidate_id, project_id, task_id, workflow_run_id, family, sequence,
                structure_file_path, complex_file_path, interface_score, pred_kd,
                plddt, interface_pae, rosetta_score, interface_energy, clash_count,
                buried_sasa, solubility_score, aggregation_risk, expression_risk,
                status, decision, next_action
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, NULL,
                      NULL, NULL, NULL, NULL, NULL,
                      NULL, NULL, NULL, NULL,
                      'sequence_designed', ?, ?)
            """,
            (
                candidate_id,
                PROJECT_ID,
                TASK_ID,
                cfg["workflow_run_id"],
                route,
                sequence,
                backbone,
                score,
                f"ProteinMPNN sequence {sequence_index} of 5 for {backbone}",
                "Fold with AlphaFold2/structure prediction and record pLDDT, pTM, and PAE before scoring.",
            ),
        )


def main() -> None:
    manifest_path = SOURCE_DIR / "sweetprotein_mpnn5_manifest.json"
    fasta_path = SOURCE_DIR / "sweetprotein_mpnn5_designs.fasta"
    log_path = SOURCE_DIR / "3860487.out"
    if not manifest_path.exists() or not fasta_path.exists():
        raise SystemExit(f"Missing downloaded ProteinMPNN outputs in {SOURCE_DIR}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fasta_records = read_fasta(fasta_path)
    route_records = {route: [] for route in ROUTES}
    for record in manifest.get("records") or []:
        backbone = str(record.get("backbone") or "")
        if backbone.startswith("monellin_"):
            route_records["monellin"].append(record)
        elif backbone.startswith("brazzein_"):
            route_records["brazzein"].append(record)

    logs = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        for route, cfg in ROUTES.items():
            write_route_outputs(route, cfg, route_records[route], fasta_records)
            upsert_job(connection, cfg, logs)
            collect_job_outputs(connection, cfg["job_id"])
            upsert_sequence_candidates(
                connection,
                route=route,
                cfg=cfg,
                records=route_records[route],
                fasta_records=fasta_records,
            )
        connection.commit()
    finally:
        connection.close()
    print({route: len(records) for route, records in route_records.items()})


if __name__ == "__main__":
    main()
