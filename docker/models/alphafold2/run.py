#!/usr/bin/env python3
import json
import os
import signal
import sys
from pathlib import Path


def _handle_sigterm(signum, frame):
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
sequences = _find_input(manifest_in, "sequence_set")
target = _find_input(manifest_in, "target_structure", "cleaned_structure")
parameters = manifest_in.get("parameters") or {}
out = Path(os.environ.get("BDA_OUTPUT_DIR", "/output"))
out.mkdir(parents=True, exist_ok=True)
pdb = out / "predicted.pdb"
pdb.write_text(
    "\n".join([
        "REMARK BDA stub AlphaFold2 output",
        f"REMARK input_sequences {sequences.get('artifact_id') if sequences else 'none'}",
        f"REMARK model_preset {parameters.get('model_preset', 'multimer')}",
        "ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00 85.00           N",
        "ATOM      2  CA  ALA A   1       1.400   0.000   0.000  1.00 85.00           C",
        "TER",
        "END",
        "",
    ])
)
scores = out / "alphafold2_confidence.json"
scores.write_text(json.dumps({"plddt": 85.2, "iptm": 0.72, "ptm": 0.68}))
pae = out / "pae.json"
pae.write_text(json.dumps({"shape": [1, 1], "values": [[0.5]]}))
manifest = {
    "status": "completed",
    "model": "AlphaFold2",
    "consumed_inputs": {
        "sequence_set": sequences.get("artifact_id") if sequences else None,
        "target_structure": target.get("artifact_id") if target else None,
    },
    "outputs": {
        "predicted_structure": [{
            "path": str(pdb),
            "format": "pdb",
            "artifact_type": "predicted_structure",
            "display_name": "predicted.pdb",
            "metadata": {"source_model": "AlphaFold2", "plddt": 85.2},
        }],
        "score_table": [{
            "path": str(scores),
            "format": "json",
            "artifact_type": "score_table",
            "display_name": "alphafold2_confidence.json",
        }],
        "pae_matrix": [{
            "path": str(pae),
            "format": "json",
            "artifact_type": "pae_matrix",
            "display_name": "pae.json",
        }],
    },
    "metrics": {"folded": 1, "plddt": 85.2, "iptm": 0.72},
}
(out / "manifest.json").write_text(json.dumps(manifest))
print(json.dumps(manifest))
