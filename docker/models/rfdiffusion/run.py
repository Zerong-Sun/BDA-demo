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
target = _find_input(manifest_in, "target_structure", "cleaned_structure", "structure")
parameters = manifest_in.get("parameters") or {}
num_designs = parameters.get("inference.num_designs", parameters.get("num_designs", 1))
out = Path(os.environ.get("BDA_OUTPUT_DIR", "/output"))
out.mkdir(parents=True, exist_ok=True)
pdb = out / "backbone_001.pdb"
pdb.write_text(
    "\n".join([
        "REMARK BDA stub RFdiffusion output",
        f"REMARK input_target {target.get('artifact_id') if target else 'none'}",
        f"REMARK num_designs {num_designs}",
        "ATOM      1  N   GLY B   1       0.000   0.000   0.000  1.00 20.00           N",
        "ATOM      2  CA  GLY B   1       1.200   0.000   0.000  1.00 20.00           C",
        "TER",
        "END",
        "",
    ])
)
scores = out / "rfdiffusion_scores.csv"
scores.write_text("design_id,source_target,rf_score\nbackbone_001,%s,-1.0\n" % (target.get("artifact_id") if target else "none"))
manifest = {
    "status": "completed",
    "model": "RFdiffusion",
    "consumed_inputs": {"target_structure": target.get("artifact_id") if target else None},
    "outputs": {
        "backbone_set": [{
            "path": str(pdb),
            "format": "pdb",
            "artifact_type": "backbone_set",
            "display_name": "backbone_001.pdb",
            "metadata": {"count": 1, "source_model": "RFdiffusion"},
        }],
        "score_table": [{
            "path": str(scores),
            "format": "csv",
            "artifact_type": "score_table",
            "display_name": "rfdiffusion_scores.csv",
        }],
    },
    "metrics": {"generated": 1},
}
(out / "manifest.json").write_text(json.dumps(manifest))
print(json.dumps(manifest))
