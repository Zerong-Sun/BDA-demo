#!/usr/bin/env python3
"""Write the small BDA output manifest after a native RFdiffusion LSF run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    source_manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    backbones = sorted(output_dir.glob(f"{args.prefix}*.pdb"))
    if not backbones:
        raise RuntimeError(f"RFdiffusion produced no PDB files for prefix {args.prefix}")

    route = (source_manifest.get("parameters") or {}).get("scaffold")
    outputs = {
        "backbone_set": [
            {
                "path": path.name,
                "format": "pdb",
                "artifact_type": "backbone_set",
                "display_name": path.name,
                "metadata": {"design_index": index, "route": route},
            }
            for index, path in enumerate(backbones)
        ]
    }
    run_record = {
        "backbone_count": len(backbones),
        "parameters": source_manifest.get("parameters") or {},
        "inputs": source_manifest.get("inputs") or [],
        "native_lsf_template": "qm-scripts/rfd",
    }
    (output_dir / "rfdiffusion_run.json").write_text(json.dumps(run_record, indent=2), encoding="utf-8")
    outputs["run_record"] = [
        {
            "path": "rfdiffusion_run.json",
            "format": "json",
            "artifact_type": "run_record",
            "display_name": "rfdiffusion_run.json",
        }
    ]
    (output_dir / "manifest.json").write_text(
        json.dumps({"outputs": outputs, "metrics": {"backbone_count": len(backbones)}}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
