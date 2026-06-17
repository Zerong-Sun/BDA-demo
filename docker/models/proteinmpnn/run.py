#!/usr/bin/env python3
"""Stub ProteinMPNN runner for BDA integration testing."""
import json
import os
import signal
import sys
from pathlib import Path


def _handle_sigterm(signum, frame):
    # Exit cleanly so the orchestrator records a cancellation instead of a crash.
    print(json.dumps({"status": "cancelled", "signal": signum}))
    sys.exit(143)


signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)


def _load_input_manifest() -> dict:
    manifest_path = Path(os.environ.get("BDA_INPUT_MANIFEST", "/input/manifest.json"))
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"inputs": [], "parameters": {}}


def _find_input(manifest: dict, *ports: str) -> dict | None:
    for item in manifest.get("inputs") or []:
        if item.get("port") in ports or item.get("artifact_type") in ports:
            return item
    return None


manifest_in = _load_input_manifest()
backbone = _find_input(manifest_in, "backbone_set", "structure", "cleaned_structure")
parameters = manifest_in.get("parameters") or {}
output_dir = Path(os.environ.get("BDA_OUTPUT_DIR", "/output"))
output_dir.mkdir(parents=True, exist_ok=True)

fasta = output_dir / "designed.fasta"
fasta.write_text(">design_1\nACDEFGHIKLMNPQRSTVWY\n")
scores = output_dir / "proteinmpnn_scores.csv"
scores.write_text(
    "sequence_id,source_backbone,temperature,mpnn_score\n"
    f"design_1,{backbone.get('artifact_id') if backbone else 'none'},{parameters.get('sampling_temperature', 0.1)},-2.5\n"
)

manifest = {
    "status": "completed",
    "model": "ProteinMPNN",
    "consumed_inputs": {"backbone_set": backbone.get("artifact_id") if backbone else None},
    "outputs": {
        "sequence_set": [{
            "path": str(fasta),
            "format": "fasta",
            "artifact_type": "sequence_set",
            "display_name": "designed.fasta",
            "metadata": {"count": 1, "source_model": "ProteinMPNN"},
        }],
        "score_table": [{
            "path": str(scores),
            "format": "csv",
            "artifact_type": "score_table",
            "display_name": "proteinmpnn_scores.csv",
        }],
    },
    "metrics": {"designed": 1, "model": "ProteinMPNN"},
}
(output_dir / "manifest.json").write_text(json.dumps(manifest))
print(json.dumps(manifest))
sys.exit(0)
