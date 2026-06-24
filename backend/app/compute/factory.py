from __future__ import annotations

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

    def _render_lsf_script(self, job: JobSpec, trusted_command: str) -> str:
        gpu = job.env.get("BDA_GPU") == "1"
        queue = job.env.get("BDA_LSF_QUEUE") or (self._gpu_queue if gpu else self._cpu_queue)
        cpu_count = max(1, int(job.env.get("BDA_CPU_COUNT", "1")))
        remote_dir = self._remote_job_dir(job.job_id)
        directives = [
            "#!/bin/bash",
            f"#BSUB -J bda-{job.job_id}",
            f"#BSUB -q {queue}",
            f"#BSUB -n {cpu_count}",
            '#BSUB -R "span[ptile=1]"',
            "#BSUB -o logs/%J.out",
            "#BSUB -e logs/%J.err",
        ]
        if gpu:
            directives.append('#BSUB -gpu "num=1"')
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
        result = self._run_ssh(
            "command -v bsub >/dev/null && command -v bjobs >/dev/null && "
            "printf 'BDA_LSF_OK\\n' && "
            f"bqueues -noheader -o 'queue_name status njobs pend run' {queues} 2>/dev/null",
            timeout=25,
            check=False,
        )
        text = result.stdout.decode("utf-8", errors="replace")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        connected = result.returncode == 0 and bool(lines) and lines[0] == "BDA_LSF_OK"
        return {
            "mode": "remote_lsf",
            "connected": connected,
            "host": self._host,
            "remote_root": self._remote_root,
            "queues": lines[1:] if connected else [],
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
