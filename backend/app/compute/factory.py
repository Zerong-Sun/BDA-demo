from __future__ import annotations

import json
import shlex
import os
import re
import subprocess
import sys
from pathlib import Path

from ..compute.adapter import ComputeAdapter, JobHandle, JobSpec, JobStatus
from ..settings import REPO_ROOT


class DemoComputeAdapter:
    def submit(self, job: JobSpec) -> JobHandle:
        return JobHandle(job_id=job.job_id, external_id=f"demo-{job.job_id}")

    def status(self, job_id: str, external_id: str | None = None) -> JobStatus:
        return JobStatus(
            job_id=job_id,
            status="blocked",
            logs="Compute not connected (demo mode). Set BDA_COMPUTE_MODE=docker to enable.",
        )

    def cancel(self, job_id: str, external_id: str | None = None) -> bool:
        return False

    def logs(self, job_id: str, external_id: str | None = None, tail: int = 100) -> str:
        return "Compute not connected (demo mode)."


class LocalDockerAdapter:
    def __init__(self) -> None:
        import docker

        from ..settings import get_settings

        settings = get_settings()
        self._client = docker.from_env() if settings.bda_docker_host == "unix:///var/run/docker.sock" else docker.DockerClient(base_url=settings.bda_docker_host)

    def submit(self, job: JobSpec) -> JobHandle:
        import docker

        env = {
            "BDA_JOB_ID": job.job_id,
            "BDA_INPUT_MANIFEST": "/input/manifest.json",
            "BDA_OUTPUT_DIR": "/output",
            **(job.env or {}),
        }
        run_kwargs: dict = {
            "image": job.container_image,
            "command": shlex.split(job.command) if job.command else None,
            "detach": True,
            "remove": False,
            "environment": env,
        }
        volumes = {}
        if job.input_dir:
            volumes[job.input_dir] = {"bind": "/input", "mode": "ro"}
        if job.output_dir:
            volumes[job.output_dir] = {"bind": "/output", "mode": "rw"}
        if job.work_dir:
            volumes[job.work_dir] = {"bind": "/work", "mode": "rw"}
        if volumes:
            run_kwargs["volumes"] = volumes
        if env.get("BDA_GPU") == "1":
            run_kwargs["device_requests"] = [docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])]

        try:
            container = self._client.containers.run(**run_kwargs)
        except docker.errors.ImageNotFound as exc:
            raise RuntimeError(f"container_image_not_found:{job.container_image}") from exc

        return JobHandle(job_id=job.job_id, external_id=container.id)

    def status(self, job_id: str, external_id: str | None = None) -> JobStatus:
        if not external_id:
            return JobStatus(job_id=job_id, status="not_found")
        container = self._client.containers.get(external_id)
        state = container.attrs.get("State", {})
        status_map = {
            "created": "queued",
            "running": "running",
            "exited": "completed" if state.get("ExitCode") == 0 else "failed",
            "dead": "failed",
        }
        status = status_map.get(container.status, container.status)
        logs = container.logs(tail=200).decode("utf-8", errors="replace")
        error = state.get("Error") if status == "failed" else None
        return JobStatus(job_id=job_id, status=status, logs=logs, error_message=error)

    def cancel(self, job_id: str, external_id: str | None = None) -> bool:
        if not external_id:
            return False
        container = self._client.containers.get(external_id)
        container.stop(timeout=10)
        return True

    def logs(self, job_id: str, external_id: str | None = None, tail: int = 100) -> str:
        if not external_id:
            return ""
        container = self._client.containers.get(external_id)
        return container.logs(tail=tail).decode("utf-8", errors="replace")


class LocalProcessAdapter:
    """Run built-in stub model runners directly for local development and tests."""

    _IMAGE_DIRS = {
        "bda/rfdiffusion": "rfdiffusion",
        "bda/proteinmpnn": "proteinmpnn",
        "bda/alphafold2": "alphafold2",
        "bda/rosetta": "rosetta",
    }

    def __init__(self) -> None:
        self._statuses: dict[str, JobStatus] = {}

    def _runner_dir(self, image: str) -> Path:
        image_name = image.split(":", 1)[0]
        model_dir = self._IMAGE_DIRS.get(image_name)
        if not model_dir:
            raise RuntimeError(f"local_runner_not_available:{image}")
        path = REPO_ROOT.parent / "docker" / "models" / model_dir
        if not (path / "run.py").exists():
            raise RuntimeError(f"local_runner_missing:{model_dir}")
        return path

    def submit(self, job: JobSpec) -> JobHandle:
        runner_dir = self._runner_dir(job.container_image)
        env = {
            "BDA_JOB_ID": job.job_id,
            "BDA_INPUT_MANIFEST": str(Path(job.input_dir or "") / "manifest.json"),
            "BDA_OUTPUT_DIR": str(Path(job.output_dir or runner_dir)),
            **(job.env or {}),
        }
        command = shlex.split(job.command) if job.command else [sys.executable, "run.py"]
        if command and command[0] == "python":
            command[0] = sys.executable
        try:
            proc = subprocess.run(
                command,
                cwd=runner_dir,
                env={**os.environ, **env},
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except Exception as exc:  # noqa: BLE001 - adapter reports failure as job status
            self._statuses[job.job_id] = JobStatus(job_id=job.job_id, status="failed", error_message=str(exc))
            return JobHandle(job_id=job.job_id, external_id=f"local-{job.job_id}")

        status = "completed" if proc.returncode == 0 else "failed"
        logs = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
        self._statuses[job.job_id] = JobStatus(
            job_id=job.job_id,
            status=status,
            logs=logs,
            error_message=None if status == "completed" else f"exit_code:{proc.returncode}",
        )
        return JobHandle(job_id=job.job_id, external_id=f"local-{job.job_id}")

    def status(self, job_id: str, external_id: str | None = None) -> JobStatus:
        return self._statuses.get(job_id) or JobStatus(job_id=job_id, status="not_found")

    def cancel(self, job_id: str, external_id: str | None = None) -> bool:
        return False

    def logs(self, job_id: str, external_id: str | None = None, tail: int = 100) -> str:
        status = self._statuses.get(job_id)
        if not status:
            return ""
        lines = status.logs.splitlines()
        return "\n".join(lines[-tail:])


class RemoteLsfAdapter:
    """Stage jobs over SSH and execute trusted wrappers through IBM Spectrum LSF."""

    _SAFE_JOB_ID = re.compile(r"^job_[A-Za-z0-9_-]+$")
    _LSF_STATUS = {
        "PEND": "queued",
        "WAIT": "queued",
        "PROV": "queued",
        "RUN": "running",
        "DONE": "completed",
        "EXIT": "failed",
        "PSUSP": "queued",
        "USUSP": "queued",
        "SSUSP": "queued",
        "UNKWN": "running",
        "ZOMBI": "failed",
    }

    def __init__(self) -> None:
        from ..settings import get_settings

        settings = get_settings()
        self._host = settings.bda_lsf_ssh_host
        self._remote_root = settings.bda_lsf_remote_root.rstrip("/")
        self._cpu_queue = settings.bda_lsf_default_cpu_queue
        self._gpu_queue = settings.bda_lsf_default_gpu_queue
        self._connect_timeout = settings.bda_lsf_connect_timeout_seconds
        self._plugin_commands = settings.lsf_plugin_commands

    def _ssh_args(self) -> list[str]:
        return [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={self._connect_timeout}",
            self._host,
        ]

    def _remote_job_dir(self, job_id: str) -> str:
        if not self._SAFE_JOB_ID.fullmatch(job_id):
            raise RuntimeError("invalid_remote_job_id")
        return f"{self._remote_root}/jobs/{job_id}"

    def _run_ssh(
        self,
        command: str,
        *,
        input_data: bytes | None = None,
        timeout: int = 30,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(
                [*self._ssh_args(), command],
                input=input_data,
                capture_output=True,
                timeout=timeout,
                check=check,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(f"remote_lsf_ssh_failed:{exc}") from exc

    def _manifest_payload(self, job: JobSpec) -> dict:
        if not job.input_dir:
            return {}
        manifest_path = Path(job.input_dir) / "manifest.json"
        if not manifest_path.exists():
            return {}
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _staged_input_name(self, manifest: dict) -> str:
        for item in manifest.get("inputs") or []:
            if item.get("port") != "target_structure":
                continue
            path = str(item.get("path") or "")
            name = Path(path).name
            if name:
                return name
        return "input.pdb"

    def _rfdiffusion_arg(self, key: str, value: object) -> str | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (dict, list)):
            rendered = json.dumps(value, separators=(",", ":"))
        else:
            rendered = str(value)
        if any(char in rendered for char in "[] ,"):
            return f"{shlex.quote(f'{key}={rendered}')}"
        return f"{key}={shlex.quote(rendered)}"

    def _render_rfdiffusion_lsf_script(self, job: JobSpec) -> str:
        manifest = self._manifest_payload(job)
        parameters = manifest.get("parameters") or {}
        gpu = job.env.get("BDA_GPU") == "1"
        partial_t = int(parameters.get("diffuser.partial_T") or 0)
        default_queue = "8v100-32-sc" if partial_t > 0 else "4v100-16-e5"
        queue = job.queue_name or job.env.get("BDA_LSF_QUEUE") or default_queue
        resource_requirement = job.resource_requirement or job.env.get("BDA_LSF_RESOURCE") or "span[ptile=1]"
        gpu_requirement = job.gpu_requirement or job.env.get("BDA_LSF_GPU") or "num=1"
        remote_dir = self._remote_job_dir(job.job_id)
        input_name = self._staged_input_name(manifest)
        work_input = "rfdiffusion_input.pdb"
        output_prefix = str(parameters.get("inference.output_prefix") or "rfdiffusion_design")
        output_prefix = Path(output_prefix).name or "rfdiffusion_design"
        run_args = [
            f"inference.input_pdb=./{work_input}",
            self._rfdiffusion_arg("contigmap.contigs", parameters.get("contigmap.contigs")),
            self._rfdiffusion_arg("ppi.hotspot_res", parameters.get("ppi.hotspot_res")),
            self._rfdiffusion_arg("contigmap.provide_seq", parameters.get("contigmap.provide_seq")),
            self._rfdiffusion_arg("inference.num_designs", parameters.get("inference.num_designs") or 100),
            f"inference.output_prefix=../output/{shlex.quote(output_prefix)}",
            self._rfdiffusion_arg("diffuser.partial_T", parameters.get("diffuser.partial_T")),
            self._rfdiffusion_arg("diffuser.T", parameters.get("diffuser.T")),
            self._rfdiffusion_arg("denoiser.noise_scale_ca", parameters.get("denoiser.noise_scale_ca")),
            self._rfdiffusion_arg("denoiser.noise_scale_frame", parameters.get("denoiser.noise_scale_frame")),
            self._rfdiffusion_arg("contigmap.inpaint_seq", parameters.get("contigmap.inpaint_seq")),
            self._rfdiffusion_arg("contigmap.inpaint_str", parameters.get("contigmap.inpaint_str")),
            self._rfdiffusion_arg("inference.ckpt_override_path", parameters.get("inference.ckpt_override_path")),
            self._rfdiffusion_arg("inference.symmetry", parameters.get("inference.symmetry")),
            self._rfdiffusion_arg("potentials.guiding_potentials", parameters.get("potentials.guiding_potentials")),
            self._rfdiffusion_arg("potentials.guide_scale", parameters.get("potentials.guide_scale")),
        ]
        run_args = [arg for arg in run_args if arg]
        run_command = " \\\n".join(run_args) + " \\"
        collect_script = f"""
python - <<'PY' >> ../logs/$LSB_JOBID.log 2>&1
import json
from pathlib import Path

output_dir = Path("../output").resolve()
source_manifest = json.loads(Path("../input/manifest.json").read_text(encoding="utf-8"))
prefix = {output_prefix!r}
backbones = sorted(output_dir.glob(f"{{prefix}}*.pdb"))
if not backbones:
    raise RuntimeError(f"RFdiffusion produced no PDB files for prefix {{prefix}}")
route = (source_manifest.get("parameters") or {{}}).get("scaffold")
outputs = {{
    "backbone_set": [
        {{
            "path": path.name,
            "format": "pdb",
            "artifact_type": "backbone_set",
            "display_name": path.name,
            "metadata": {{"design_index": index, "route": route}},
        }}
        for index, path in enumerate(backbones)
    ],
    "run_record": [
        {{
            "path": "rfdiffusion_run.json",
            "format": "json",
            "artifact_type": "run_record",
            "display_name": "rfdiffusion_run.json",
        }}
    ],
}}
(output_dir / "rfdiffusion_run.json").write_text(
    json.dumps({{
        "backbone_count": len(backbones),
        "parameters": source_manifest.get("parameters") or {{}},
        "inputs": source_manifest.get("inputs") or [],
        "native_lsf_template": "qm-scripts/rfd",
    }}, indent=2),
    encoding="utf-8",
)
(output_dir / "manifest.json").write_text(
    json.dumps({{"outputs": outputs, "metrics": {{"backbone_count": len(backbones)}}}}, indent=2),
    encoding="utf-8",
)
PY"""
        directives = [
            "#!/bin/bash",
            "",
            f"#BSUB -J RFdiffusion_{job.job_id.removeprefix('job_')[:10]}",
            f"#BSUB -q {queue}",
            "#BSUB -n 1",
        ]
        if gpu:
            directives.append(f'#BSUB -gpu "{gpu_requirement}"')
        directives.extend([
            f'#BSUB -R "{resource_requirement}"',
            "#BSUB -o %J.out",
            "#BSUB -e %J.err",
            "",
            f"cd {shlex.quote(remote_dir)}",
            "mkdir -p output work logs",
            f"cp input/{shlex.quote(input_name)} work/{work_input}",
            "",
            "source activate /work/bme-liz/miniconda3/envs/SE3nv-gpu",
            "",
            "cd work",
            "/work/bme-liz/software/RFdiffusion/scripts/run_inference.py \\",
            run_command,
            f"> ../logs/$LSB_JOBID.log 2>&1",
            collect_script.strip(),
        ])
        return "\n".join(directives) + "\n"

    def _render_lsf_script(self, job: JobSpec, trusted_command: str) -> str:
        if job.plugin_id == "plugin_rfdiffusion":
            return self._render_rfdiffusion_lsf_script(job)
        gpu = job.env.get("BDA_GPU") == "1"
        queue = job.queue_name or job.env.get("BDA_LSF_QUEUE") or (self._gpu_queue if gpu else self._cpu_queue)
        cpu_count = max(1, int(job.env.get("BDA_CPU_COUNT", "1")))
        resource_requirement = job.resource_requirement or job.env.get("BDA_LSF_RESOURCE") or "span[ptile=1]"
        gpu_requirement = job.gpu_requirement or job.env.get("BDA_LSF_GPU") or "num=1"
        remote_dir = self._remote_job_dir(job.job_id)
        directives = [
            "#!/bin/bash",
            f"#BSUB -J bda-{job.job_id}",
            f"#BSUB -q {queue}",
            f"#BSUB -n {cpu_count}",
            f'#BSUB -R "{resource_requirement}"',
            "#BSUB -o logs/%J.out",
            "#BSUB -e logs/%J.err",
        ]
        if gpu:
            directives.append(f'#BSUB -gpu "{gpu_requirement}"')
        directives.extend([
            "",
            "set -Eeuo pipefail",
            f"cd {shlex.quote(remote_dir)}",
            "mkdir -p output work logs",
            f"export BDA_JOB_ID={shlex.quote(job.job_id)}",
            "export BDA_INPUT_MANIFEST=\"$PWD/input/manifest.json\"",
            "export BDA_OUTPUT_DIR=\"$PWD/output\"",
            "export BDA_WORK_DIR=\"$PWD/work\"",
            trusted_command,
        ])
        return "\n".join(directives) + "\n"

    def _upload_workspace(self, job: JobSpec, script: str) -> None:
        if not job.input_dir or not job.work_dir:
            raise RuntimeError("remote_lsf_workspace_missing")
        remote_dir = self._remote_job_dir(job.job_id)
        self._run_ssh(
            f"umask 077 && mkdir -p {shlex.quote(remote_dir)}/input "
            f"{shlex.quote(remote_dir)}/output {shlex.quote(remote_dir)}/work "
            f"{shlex.quote(remote_dir)}/logs"
        )
        script_path = Path(job.work_dir) / "submit.lsf"
        script_path.write_text(script, encoding="utf-8")
        archive = subprocess.run(
            ["tar", "-C", str(Path(job.input_dir).parent), "-cf", "-", "input", "work/submit.lsf"],
            capture_output=True,
            check=True,
        ).stdout
        self._run_ssh(
            f"tar -C {shlex.quote(remote_dir)} -xf -",
            input_data=archive,
            timeout=120,
        )

    def _download_outputs(self, job_id: str, output_dir: str) -> None:
        remote_dir = self._remote_job_dir(job_id)
        result = self._run_ssh(
            f"test -d {shlex.quote(remote_dir)}/output && "
            f"tar -C {shlex.quote(remote_dir)}/output -cf - .",
            timeout=120,
            check=False,
        )
        if result.returncode != 0 or not result.stdout:
            return
        local_output = Path(output_dir)
        local_output.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["tar", "-C", str(local_output), "-xf", "-"],
            input=result.stdout,
            capture_output=True,
            check=True,
        )

    def submit(self, job: JobSpec) -> JobHandle:
        trusted_command = self._plugin_commands.get(job.plugin_id)
        if not trusted_command:
            raise RuntimeError(f"remote_lsf_plugin_not_configured:{job.plugin_id}")
        script = self._render_lsf_script(job, trusted_command)
        self._upload_workspace(job, script)
        remote_dir = self._remote_job_dir(job.job_id)
        result = self._run_ssh(
            f"cd {shlex.quote(remote_dir)} && bsub < work/submit.lsf",
            timeout=30,
        )
        output = result.stdout.decode("utf-8", errors="replace")
        match = re.search(r"Job <(\d+)>", output)
        if not match:
            raise RuntimeError(f"remote_lsf_submit_unrecognized:{output.strip()}")
        return JobHandle(job_id=job.job_id, external_id=match.group(1))

    def status(self, job_id: str, external_id: str | None = None) -> JobStatus:
        if not external_id:
            return JobStatus(job_id=job_id, status="not_found")
        result = self._run_ssh(
            f"bjobs -noheader -o stat {shlex.quote(external_id)}",
            check=False,
        )
        raw = result.stdout.decode("utf-8", errors="replace").strip().split()
        lsf_status = raw[0] if raw else ""
        status = self._LSF_STATUS.get(lsf_status)
        if status is None:
            history = self._run_ssh(
                f"bhist -n 1 -noheader -o stat {shlex.quote(external_id)}",
                check=False,
            )
            history_raw = history.stdout.decode("utf-8", errors="replace").strip().split()
            status = self._LSF_STATUS.get(history_raw[0] if history_raw else "", "not_found")
        logs = self.logs(job_id, external_id, tail=200)
        return JobStatus(job_id=job_id, status=status, logs=logs)

    def cancel(self, job_id: str, external_id: str | None = None) -> bool:
        if not external_id:
            return False
        return self._run_ssh(f"bkill {shlex.quote(external_id)}", check=False).returncode == 0

    def logs(self, job_id: str, external_id: str | None = None, tail: int = 100) -> str:
        if not external_id:
            return ""
        remote_dir = self._remote_job_dir(job_id)
        safe_tail = min(max(int(tail), 1), 2000)
        result = self._run_ssh(
            f"cd {shlex.quote(remote_dir)} && "
            f"tail -n {safe_tail} logs/{shlex.quote(external_id)}.out "
            f"logs/{shlex.quote(external_id)}.err 2>/dev/null",
            check=False,
        )
        return result.stdout.decode("utf-8", errors="replace")

    def collect_outputs(self, job_id: str, output_dir: str) -> None:
        self._download_outputs(job_id, output_dir)

    def health(self) -> dict[str, object]:
        queues = " ".join(
            shlex.quote(queue)
            for queue in dict.fromkeys([self._gpu_queue, self._cpu_queue])
            if queue
        )
        queue_filter = f" {queues}" if queues else ""
        result = self._run_ssh(
            "command -v bsub >/dev/null && command -v bjobs >/dev/null && "
            "printf 'BDA_LSF_OK\\n' && "
            f"bqueues -noheader -o 'queue_name status njobs pend run' {queue_filter} 2>/dev/null && "
            "printf 'BDA_LSF_ALL_QUEUES\\n' && "
            "bqueues -noheader -o 'queue_name status njobs pend run' 2>/dev/null",
            timeout=60,
            check=False,
        )
        text = result.stdout.decode("utf-8", errors="replace")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        connected = result.returncode == 0 and bool(lines) and lines[0] == "BDA_LSF_OK"
        all_marker = lines.index("BDA_LSF_ALL_QUEUES") if "BDA_LSF_ALL_QUEUES" in lines else len(lines)
        return {
            "mode": "remote_lsf",
            "connected": connected,
            "host": self._host,
            "remote_root": self._remote_root,
            "queues": lines[1:all_marker] if connected else [],
            "all_queues": lines[all_marker + 1:] if connected and all_marker < len(lines) else [],
            "reason": None if connected else result.stderr.decode("utf-8", errors="replace").strip(),
        }


_adapter_cache: dict[str, ComputeAdapter] = {}


def get_compute_adapter() -> ComputeAdapter:
    """Return a cached compute adapter for the configured mode.

    Adapters (notably ``LocalDockerAdapter``, which opens a Docker client) are
    expensive to construct, so we memoize one instance per compute mode instead
    of building a fresh adapter on every call.
    """
    from ..settings import get_settings

    mode = get_settings().bda_compute_mode
    cached = _adapter_cache.get(mode)
    if cached is not None:
        return cached

    if mode == "docker":
        adapter: ComputeAdapter = LocalDockerAdapter()
    elif mode == "local":
        adapter = LocalProcessAdapter()
    elif mode == "remote_lsf":
        adapter = RemoteLsfAdapter()
    else:
        adapter = DemoComputeAdapter()
    _adapter_cache[mode] = adapter
    return adapter


def reset_compute_adapter_cache() -> None:
    """Clear the cached adapters (useful in tests or after a settings change)."""
    _adapter_cache.clear()
