from __future__ import annotations

import shlex
import os
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
    else:
        adapter = DemoComputeAdapter()
    _adapter_cache[mode] = adapter
    return adapter


def reset_compute_adapter_cache() -> None:
    """Clear the cached adapters (useful in tests or after a settings change)."""
    _adapter_cache.clear()
