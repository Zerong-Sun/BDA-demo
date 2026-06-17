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
structure = _find_input(manifest_in, "complex_structure", "predicted_structure", "structure")
parameters = manifest_in.get("parameters") or {}
out = Path(os.environ.get("BDA_OUTPUT_DIR", "/output"))
out.mkdir(parents=True, exist_ok=True)
pdb = out / "relaxed.pdb"
pdb.write_text(
    "\n".join([
        "REMARK BDA stub Rosetta output",
        f"REMARK input_structure {structure.get('artifact_id') if structure else 'none'}",
        f"REMARK protocol {parameters.get('protocol', 'interface_score')}",
        "ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00 80.00           N",
        "ATOM      2  CA  ALA A   1       1.400   0.000   0.000  1.00 80.00           C",
        "TER",
        "END",
        "",
    ])
)
scores = out / "rosetta_scores.csv"
scores.write_text("structure_id,source_structure,interface_score,clash_count,buried_sasa\nrelaxed,%s,-12.5,0,860.0\n" % (structure.get("artifact_id") if structure else "none"))
metrics = out / "interface_metrics.json"
metrics.write_text(json.dumps({"interface_score": -12.5, "clash_count": 0, "buried_sasa": 860.0}))
manifest = {
    "status": "completed",
    "model": "Rosetta",
    "consumed_inputs": {"structure": structure.get("artifact_id") if structure else None},
    "outputs": {
        "relaxed_structure": [{
            "path": str(pdb),
            "format": "pdb",
            "artifact_type": "relaxed_structure",
            "display_name": "relaxed.pdb",
            "metadata": {"source_model": "Rosetta"},
        }],
        "score_table": [{
            "path": str(scores),
            "format": "csv",
            "artifact_type": "score_table",
            "display_name": "rosetta_scores.csv",
        }],
        "interface_metrics": [{
            "path": str(metrics),
            "format": "json",
            "artifact_type": "interface_metrics",
            "display_name": "interface_metrics.json",
        }],
    },
    "metrics": {"scored": 1, "interface_score": -12.5, "clash_count": 0, "buried_sasa": 860.0},
}
(out / "manifest.json").write_text(json.dumps(manifest))
print(json.dumps(manifest))
