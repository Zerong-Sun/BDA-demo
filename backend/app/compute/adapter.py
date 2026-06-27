from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class JobSpec:
    job_id: str
    workflow_run_id: str | None
    node_run_id: str | None
    plugin_id: str
    container_image: str
    command: str
    input_artifacts: dict[str, Any] = field(default_factory=dict)
    compute_node_id: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    input_dir: str | None = None
    output_dir: str | None = None
    work_dir: str | None = None
    queue_name: str | None = None
    resource_requirement: str | None = None
    gpu_requirement: str | None = None


@dataclass
class JobHandle:
    job_id: str
    external_id: str | None = None


@dataclass
class JobStatus:
    job_id: str
    status: str
    logs: str = ""
    output_artifacts: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class ComputeAdapter(Protocol):
    def render_script(self, job: JobSpec) -> str: ...

    def submit(self, job: JobSpec) -> JobHandle: ...

    def status(self, job_id: str, external_id: str | None = None) -> JobStatus: ...

    def cancel(self, job_id: str, external_id: str | None = None) -> bool: ...

    def logs(self, job_id: str, external_id: str | None = None, tail: int = 100) -> str: ...
