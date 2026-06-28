#!/usr/bin/env python3
"""Trusted RFdiffusion LSF wrapper for a staged BDA job.

The wrapper reads the platform-created input manifest, renders only allowlisted
RFdiffusion arguments, executes the configured RFdiffusion installation without
a shell, and writes the artifact contract consumed by BDA.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ALLOWED_PARAMETERS = {
    "contigmap.contigs",
    "ppi.hotspot_res",
    "inference.num_designs",
    "diffuser.partial_T",
    "diffuser.T",
    "denoiser.noise_scale_ca",
    "denoiser.noise_scale_frame",
    "contigmap.inpaint_seq",
    "contigmap.inpaint_str",
    "contigmap.provide_seq",
    "inference.ckpt_override_path",
    "inference.symmetry",
    "potentials.guiding_potentials",
    "potentials.guide_scale",
}


def _manifest_path() -> Path:
    return Path(os.environ.get("BDA_INPUT_MANIFEST", "/input/manifest.json")).resolve()


def _output_dir() -> Path:
    path = Path(os.environ.get("BDA_OUTPUT_DIR", "/output")).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_staged_path(raw_path: str, manifest_path: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute() and path.parts[:2] == ("/", "input"):
        return manifest_path.parent / path.name
    if path.is_absolute():
        return path
    return manifest_path.parent / path


def _target_structure(manifest: dict[str, Any], manifest_path: Path) -> Path:
    for item in manifest.get("inputs") or []:
        if item.get("port") != "target_structure":
            continue
        path = _resolve_staged_path(str(item.get("path") or ""), manifest_path)
        if path.is_file():
            return path
    raise RuntimeError("missing_staged_target_structure")


def _inference_script() -> Path:
    configured = os.environ.get("BDA_RFDIFFUSION_ROOT", "").strip()
    candidates = [
        Path(configured) if configured else None,
        Path("/opt/RFdiffusion"),
        Path.home() / "RFdiffusion",
        Path.home() / "rfdiffusion",
    ]
    for root in candidates:
        if root and (root / "scripts" / "run_inference.py").is_file():
            return root / "scripts" / "run_inference.py"
    raise RuntimeError(
        "rfdiffusion_installation_not_found:"
        "set_BDA_RFDIFFUSION_ROOT_or_run_the_wrapper_inside_the_RFdiffusion_environment"
    )


def _render_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def build_command(manifest: dict[str, Any], manifest_path: Path, output_dir: Path) -> list[str]:
    parameters = manifest.get("parameters") or {}
    input_pdb = _target_structure(manifest, manifest_path)
    python = os.environ.get("BDA_RFDIFFUSION_PYTHON", "").strip() or sys.executable
    command = [
        python,
        str(_inference_script()),
        f"inference.input_pdb={input_pdb}",
    ]
    for key in sorted(ALLOWED_PARAMETERS):
        value = parameters.get(key)
        if value is None or value == "":
            continue
        command.append(f"{key}={_render_value(value)}")
    command.append(f"inference.output_prefix={output_dir / 'design'}")
    return command


def _write_output_manifest(
    *,
    output_dir: Path,
    command: list[str],
    source_manifest: dict[str, Any],
) -> None:
    backbones = sorted(output_dir.glob("design*.pdb"))
    if not backbones:
        raise RuntimeError("rfdiffusion_produced_no_backbone_pdbs")
    outputs = {
        "backbone_set": [
            {
                "path": path.name,
                "format": "pdb",
                "artifact_type": "backbone_set",
                "display_name": path.name,
                "metadata": {
                    "design_index": index,
                    "route": (source_manifest.get("parameters") or {}).get("scaffold"),
                },
            }
            for index, path in enumerate(backbones)
        ]
    }
    run_record = {
        "command_argv": command,
        "backbone_count": len(backbones),
        "parameters": source_manifest.get("parameters") or {},
        "inputs": source_manifest.get("inputs") or [],
    }
    (output_dir / "rfdiffusion_run.json").write_text(
        json.dumps(run_record, indent=2),
        encoding="utf-8",
    )
    outputs["run_record"] = [{
        "path": "rfdiffusion_run.json",
        "format": "json",
        "artifact_type": "run_record",
        "display_name": "rfdiffusion_run.json",
    }]
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "outputs": outputs,
                "metrics": {"backbone_count": len(backbones)},
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    manifest_path = _manifest_path()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_dir = _output_dir()
    command = build_command(manifest, manifest_path, output_dir)
    subprocess.run(command, check=True)
    _write_output_manifest(
        output_dir=output_dir,
        command=command,
        source_manifest=manifest,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
