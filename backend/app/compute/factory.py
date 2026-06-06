from __future__ import annotations

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
        self._client = docker.DockerClient(base_url=settings.bda_docker_host)
        self._containers: dict[str, str] = {}

    def submit(self, job: JobSpec) -> JobHandle:
        run_kwargs: dict = {
            "image": job.container_image,
            "command": job.command.split() if job.command else None,
            "detach": True,
            "remove": False,
            "environment": job.env or None,
        }
        if (job.env or {}).get("BDA_GPU") == "1":
            run_kwargs["device_requests"] = [
                self._client.types.DeviceRequest(count=-1, capabilities=[["gpu"]])
            ]

        container = self._client.containers.run(**run_kwargs)
        self._containers[job.job_id] = container.id
        return JobHandle(job_id=job.job_id, external_id=container.id)

    def status(self, job_id: str, external_id: str | None = None) -> JobStatus:
        cid = external_id or self._containers.get(job_id)
        if not cid:
            return JobStatus(job_id=job_id, status="not_found")
        container = self._client.containers.get(cid)
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
        cid = external_id or self._containers.get(job_id)
        if not cid:
            return False
        container = self._client.containers.get(cid)
        container.stop(timeout=10)
        return True

    def logs(self, job_id: str, external_id: str | None = None, tail: int = 100) -> str:
        cid = external_id or self._containers.get(job_id)
        if not cid:
            return ""
        container = self._client.containers.get(cid)
        return container.logs(tail=tail).decode("utf-8", errors="replace")


def get_compute_adapter() -> ComputeAdapter:
    from ..settings import get_settings

    mode = get_settings().bda_compute_mode
    if mode == "docker":
        return LocalDockerAdapter()
    return DemoComputeAdapter()
