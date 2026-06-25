import json

from backend.cluster_wrappers import rfdiffusion_job


def test_wrapper_builds_allowlisted_command_and_manifest(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    rf_root = tmp_path / "RFdiffusion"
    input_dir.mkdir()
    output_dir.mkdir()
    (rf_root / "scripts").mkdir(parents=True)
    inference = rf_root / "scripts" / "run_inference.py"
    inference.write_text("# test inference entrypoint\n")
    pdb = input_dir / "scaffold.pdb"
    pdb.write_text("ATOM\n")
    manifest = {
        "inputs": [{"port": "target_structure", "path": "/input/scaffold.pdb"}],
        "parameters": {
            "contigmap.contigs": "[A1-50/2-4/B1-44]",
            "inference.num_designs": 100,
            "linker_design": {"output_chain_count": 1},
        },
    }
    manifest_path = input_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setenv("BDA_RFDIFFUSION_ROOT", str(rf_root))
    command = rfdiffusion_job.build_command(manifest, manifest_path, output_dir)
    assert f"inference.input_pdb={pdb}" in command
    assert "contigmap.contigs=[A1-50/2-4/B1-44]" in command
    assert "inference.num_designs=100" in command
    assert not any("linker_design" in item for item in command)

    for index in range(2):
        (output_dir / f"design_{index}.pdb").write_text("ATOM\n")
    rfdiffusion_job._write_output_manifest(
        output_dir=output_dir,
        command=command,
        source_manifest=manifest,
    )
    output_manifest = json.loads((output_dir / "manifest.json").read_text())
    assert len(output_manifest["outputs"]["backbone_set"]) == 2
    assert output_manifest["metrics"]["backbone_count"] == 2
