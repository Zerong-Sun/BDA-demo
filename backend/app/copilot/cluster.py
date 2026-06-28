from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from ..config import ARTIFACTS_ROOT
from ..settings import get_settings

DRAFTS_ROOT = ARTIFACTS_ROOT / "copilot-cluster-drafts"
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
BLOCKED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bsudo\b",
        r"\brm\s+-[^\n]*r[^\n]*f\b",
        r"\b(?:shutdown|reboot|halt|poweroff|mkfs|fdisk)\b",
        r"\bdd\s+if=",
        r":\(\)\s*\{\s*:\|:&\s*\};:",
        r"\b(?:ssh|scp|sftp)\b",
        r"\bcurl\b[^\n|]*\|\s*(?:ba)?sh\b",
        r"\bwget\b[^\n|]*\|\s*(?:ba)?sh\b",
        r"/etc/(?:passwd|shadow|sudoers)",
        r"(?:password|api[_-]?key|token)\s*=",
    )
]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _draft_path(draft_id: str) -> Path:
    if not re.fullmatch(r"draft_[a-f0-9]{16}", draft_id):
        raise ValueError("invalid_draft_id")
    return DRAFTS_ROOT / f"{draft_id}.json"


def _save(draft: dict[str, Any]) -> dict[str, Any]:
    DRAFTS_ROOT.mkdir(parents=True, exist_ok=True)
    _draft_path(draft["draft_id"]).write_text(
        json.dumps(draft, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return draft


def get_draft(draft_id: str) -> dict[str, Any]:
    path = _draft_path(draft_id)
    if not path.exists():
        raise ValueError("draft_not_found")
    return json.loads(path.read_text(encoding="utf-8"))


def list_drafts(*, project_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    DRAFTS_ROOT.mkdir(parents=True, exist_ok=True)
    items = []
    for path in sorted(DRAFTS_ROOT.glob("draft_*.json"), reverse=True):
        item = json.loads(path.read_text(encoding="utf-8"))
        if project_id and item.get("project_id") != project_id:
            continue
        items.append(item)
        if len(items) >= max(1, min(limit, 100)):
            break
    return items


def _validate_lines(lines: list[str]) -> list[str]:
    cleaned = []
    for raw in lines:
        line = str(raw).strip()
        if not line:
            continue
        if len(line) > 2000:
            raise ValueError("cluster_command_too_long")
        for pattern in BLOCKED_PATTERNS:
            if pattern.search(line):
                raise ValueError(f"blocked_cluster_command:{pattern.pattern}")
        cleaned.append(line)
    if not cleaned:
        raise ValueError("cluster_command_required")
    return cleaned


def create_draft(
    *,
    project_id: str | None,
    created_by: str,
    job_name: str,
    command: str,
    queue: str | None = None,
    gpu_count: int = 0,
    cpu_count: int = 1,
    setup_lines: list[str] | None = None,
    expected_outputs: list[str] | None = None,
    rationale: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    safe_name = job_name.strip()
    if not SAFE_NAME.fullmatch(safe_name):
        raise ValueError("invalid_cluster_job_name")
    gpu_count = max(0, min(int(gpu_count), 8))
    cpu_count = max(1, min(int(cpu_count), 128))
    selected_queue = (queue or (
        settings.bda_lsf_default_gpu_queue if gpu_count else settings.bda_lsf_default_cpu_queue
    )).strip()
    if not SAFE_NAME.fullmatch(selected_queue):
        raise ValueError("invalid_cluster_queue")
    setup = _validate_lines(setup_lines or ["module purge"])
    commands = _validate_lines([command])
    outputs = [str(item).strip() for item in (expected_outputs or []) if str(item).strip()]
    draft_id = f"draft_{uuid.uuid4().hex[:16]}"
    remote_dir = f"{settings.bda_lsf_remote_root.rstrip('/')}/copilot-jobs/{draft_id}"
    directives = [
        "#!/bin/bash",
        f"#BSUB -J {safe_name}",
        f"#BSUB -q {selected_queue}",
        f"#BSUB -n {cpu_count}",
        '#BSUB -R "span[ptile=1]"',
        "#BSUB -o logs/%J.out",
        "#BSUB -e logs/%J.err",
    ]
    if gpu_count:
        directives.append(f'#BSUB -gpu "num={gpu_count}"')
    script = "\n".join([
        *directives,
        "",
        "set -Eeuo pipefail",
        f"cd {shlex.quote(remote_dir)}",
        "mkdir -p input output work logs",
        *setup,
        *commands,
        "",
    ])
    digest = hashlib.sha256(script.encode("utf-8")).hexdigest()
    return _save({
        "draft_id": draft_id,
        "project_id": project_id,
        "created_by": created_by,
        "created_at": _now(),
        "status": "awaiting_confirmation",
        "job_name": safe_name,
        "queue": selected_queue,
        "gpu_count": gpu_count,
        "cpu_count": cpu_count,
        "setup_lines": setup,
        "command": commands[0],
        "expected_outputs": outputs,
        "rationale": rationale,
        "remote_dir": remote_dir,
        "script": script,
        "script_sha256": digest,
        "external_id": None,
    })


def _ssh(command: str, *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    settings = get_settings()
    try:
        return subprocess.run(
            [
                "ssh",
                "-o", "BatchMode=yes",
                "-o", f"ConnectTimeout={settings.bda_lsf_connect_timeout_seconds}",
                settings.bda_lsf_ssh_host,
                command,
            ],
            input=input_text,
            text=True,
            capture_output=True,
            timeout=30,
            check=check,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"cluster_ssh_failed:{exc}") from exc


def submit_draft(draft_id: str, *, confirmed_by: str) -> dict[str, Any]:
    draft = get_draft(draft_id)
    if draft["status"] != "awaiting_confirmation":
        raise ValueError("draft_not_awaiting_confirmation")
    if hashlib.sha256(draft["script"].encode("utf-8")).hexdigest() != draft["script_sha256"]:
        raise ValueError("draft_integrity_failed")
    remote_dir = draft["remote_dir"]
    _ssh(f"umask 077 && mkdir -p {shlex.quote(remote_dir)}/logs {shlex.quote(remote_dir)}/output")
    _ssh(
        f"cat > {shlex.quote(remote_dir)}/submit.lsf",
        input_text=draft["script"],
    )
    result = _ssh(
        f"cd {shlex.quote(remote_dir)} && bsub < submit.lsf",
    )
    match = re.search(r"Job <(\d+)>", result.stdout)
    if not match:
        raise RuntimeError(f"cluster_submit_unrecognized:{result.stdout.strip()}")
    draft.update({
        "status": "submitted",
        "external_id": match.group(1),
        "confirmed_by": confirmed_by,
        "confirmed_at": _now(),
        "submit_output": result.stdout.strip(),
    })
    return _save(draft)


def refresh_draft(draft_id: str) -> dict[str, Any]:
    draft = get_draft(draft_id)
    external_id = draft.get("external_id")
    if not external_id:
        return draft
    result = _ssh(
        f"bjobs -noheader -o stat {shlex.quote(str(external_id))}",
        check=False,
    )
    raw_status = result.stdout.strip().split()
    lsf_status = raw_status[0] if raw_status else ""
    status_map = {
        "PEND": "queued", "WAIT": "queued", "RUN": "running",
        "DONE": "completed", "EXIT": "failed", "PSUSP": "queued",
        "USUSP": "queued", "SSUSP": "queued", "ZOMBI": "failed",
    }
    if not lsf_status:
        history = _ssh(
            f"bhist -n 1 -noheader -o stat {shlex.quote(str(external_id))}",
            check=False,
        )
        history_status = history.stdout.strip().split()
        lsf_status = history_status[0] if history_status else ""
    draft["status"] = status_map.get(lsf_status, draft.get("status", "submitted"))
    logs = _ssh(
        f"cd {shlex.quote(draft['remote_dir'])} && "
        f"tail -n 200 logs/{shlex.quote(str(external_id))}.out "
        f"logs/{shlex.quote(str(external_id))}.err 2>/dev/null",
        check=False,
    )
    draft["logs"] = logs.stdout[-20000:]
    if draft["status"] == "completed":
        files = _ssh(
            f"cd {shlex.quote(draft['remote_dir'])} && "
            "find output -maxdepth 3 -type f -printf '%p\\t%s\\n' | head -n 200",
            check=False,
        )
        draft["output_files"] = [
            {"path": line.split("\t", 1)[0], "size_bytes": int(line.split("\t", 1)[1])}
            for line in files.stdout.splitlines()
            if "\t" in line and line.split("\t", 1)[1].isdigit()
        ]
    return _save(draft)


def download_output(draft_id: str, path: str) -> tuple[str, bytes]:
    draft = get_draft(draft_id)
    normalized = PurePosixPath(path)
    if (
        normalized.is_absolute()
        or ".." in normalized.parts
        or not normalized.parts
        or normalized.parts[0] != "output"
    ):
        raise ValueError("invalid_output_path")
    settings = get_settings()
    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", "BatchMode=yes",
                "-o", f"ConnectTimeout={settings.bda_lsf_connect_timeout_seconds}",
                settings.bda_lsf_ssh_host,
                f"cd {shlex.quote(draft['remote_dir'])} && cat -- {shlex.quote(str(normalized))}",
            ],
            capture_output=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"cluster_download_failed:{exc}") from exc
    if result.returncode != 0:
        raise ValueError("output_not_found")
    return normalized.name, result.stdout
