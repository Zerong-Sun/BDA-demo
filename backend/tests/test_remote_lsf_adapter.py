from pathlib import Path
from subprocess import CompletedProcess

import pytest

from backend.app.compute.adapter import JobSpec
from backend.app.compute.factory import RemoteLsfAdapter


def make_adapter() -> RemoteLsfAdapter:
    adapter = RemoteLsfAdapter.__new__(RemoteLsfAdapter)
    adapter._host = "qm"
    adapter._remote_root = "/work/bme-sunzr/bda"
    adapter._cpu_queue = "v3-64"
    adapter._gpu_queue = "gpu-bme-liz"
    adapter._connect_timeout = 10
    adapter._plugin_commands = {
        "plugin_proteinmpnn": "bash /work/bme-sunzr/bda/scripts/run_proteinmpnn.sh",
    }
    return adapter


def make_job(tmp_path: Path, *, gpu: bool = False) -> JobSpec:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    work_dir = tmp_path / "work"
    input_dir.mkdir()
    output_dir.mkdir()
    work_dir.mkdir()
    (input_dir / "manifest.json").write_text("{}")
    return JobSpec(
        job_id="job_test123",
        workflow_run_id="run_test",
        node_run_id="node_test",
        plugin_id="plugin_proteinmpnn",
        container_image="unused",
        command="untrusted command from database",
        env={"BDA_GPU": "1"} if gpu else {},
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        work_dir=str(work_dir),
    )


def test_lsf_script_renders_builtin_proteinmpnn_runner(tmp_path: Path):
    adapter = make_adapter()
    job = make_job(tmp_path, gpu=True)

    script = adapter.render_script(job)

    assert "#BSUB -q 4v100-16-e5" in script
    assert '#BSUB -gpu "num=1"' in script
    assert "protein_mpnn_run.py" in script
    assert "manifest.json" in script
    assert job.command not in script
    assert "parsed_pdbs.jsonl" in script


def test_submit_rejects_plugin_without_admin_wrapper(tmp_path: Path):
    adapter = make_adapter()
    job = make_job(tmp_path)
    job.plugin_id = "plugin_unknown"

    with pytest.raises(RuntimeError, match="remote_lsf_plugin_not_configured"):
        adapter.submit(job)


def test_status_maps_lsf_states(monkeypatch):
    adapter = make_adapter()

    def fake_run(command: str, **_kwargs):
        if command.startswith("bjobs"):
            return CompletedProcess([], 0, stdout=b"RUN\n", stderr=b"")
        return CompletedProcess([], 0, stdout=b"model is running\n", stderr=b"")

    monkeypatch.setattr(adapter, "_run_ssh", fake_run)

    status = adapter.status("job_test123", "12345")

    assert status.status == "running"
    assert "model is running" in status.logs
