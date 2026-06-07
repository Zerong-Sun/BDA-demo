from __future__ import annotations

import shlex

from ..compute.adapter import ComputeAdapter, JobHandle, JobSpec, JobStatus


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

        env = {"BDA_OUTPUT_DIR": "/output", **(job.env or {})}
        run_kwargs: dict = {
            "image": job.container_image,
            "command": shlex.split(job.command) if job.command else None,
            "detach": True,
            "remove": False,
            "environment": env,
        }
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


def get_compute_adapter() -> ComputeAdapter:
    from ..settings import get_settings

    mode = get_settings().bda_compute_mode
    if mode == "docker":
        return LocalDockerAdapter()
    return DemoComputeAdapter()
