from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import ARTIFACTS_ROOT
from ..compute.adapter import JobSpec
from ..compute.factory import get_compute_adapter
from ..repositories import artifacts as artifact_repo
from ..repositories import catalog, registry
from ..repositories.base import decode_row, decode_rows, get_by_id
from ..services.artifact_store import get_artifact_store
from ..services.artifacts import artifact_format_for_filename, infer_artifact_metadata, sha256_file


ARTIFACT_STORAGE_PREFIX = "artifact://"
LEGACY_ARTIFACT_STORAGE_PREFIXES = ("local://",)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str | None,
    node_run_id: str | None,
    plugin_id: str,
    input_artifacts: dict[str, Any] | None = None,
    compute_node_id: str | None = None,
) -> dict[str, Any]:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    connection.execute(
        """
        INSERT INTO jobs (
            job_id, workflow_run_id, node_run_id, compute_node_id,
            status, plugin_id, input_artifacts, output_artifacts, created_at
        ) VALUES (?, ?, ?, ?, 'queued', ?, ?, '{}', ?)
        """,
        (
            job_id,
            workflow_run_id,
            node_run_id,
            compute_node_id,
            plugin_id,
            json.dumps(input_artifacts or {}),
            _now_iso(),
        ),
    )
    return get_job(connection, job_id) or {}


def _artifact_key(storage_uri: str) -> str:
    if storage_uri.startswith(ARTIFACT_STORAGE_PREFIX):
        return storage_uri[len(ARTIFACT_STORAGE_PREFIX):]
    for prefix in LEGACY_ARTIFACT_STORAGE_PREFIXES:
        if storage_uri.startswith(prefix):
            return storage_uri[len(prefix):]
    raise ValueError("unsupported_artifact_storage")


def _job_workspace(job_id: str) -> dict[str, Path]:
    root = ARTIFACTS_ROOT / "jobs" / job_id
    paths = {
        "root": root,
        "input": root / "input",
        "output": root / "output",
        "work": root / "work",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _normalize_input_refs(input_artifacts: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if isinstance(input_artifacts, str):
        refs.append({"artifact_id": input_artifacts})
    elif isinstance(input_artifacts, list):
        for item in input_artifacts:
            if isinstance(item, str):
                refs.append({"artifact_id": item})
            elif isinstance(item, dict):
                refs.append(item)
    elif isinstance(input_artifacts, dict):
        for port, value in input_artifacts.items():
            if isinstance(value, str):
                refs.append({"port": port, "artifact_id": value})
            elif isinstance(value, list):
                for nested in value:
                    if isinstance(nested, str):
                        refs.append({"port": port, "artifact_id": nested})
                    elif isinstance(nested, dict):
                        refs.append({"port": port, **nested})
            elif isinstance(value, dict):
                refs.append({"port": port, **value})
    return [ref for ref in refs if ref.get("artifact_id")]


def _stage_input_artifacts(
    connection: sqlite3.Connection,
    input_dir: Path,
    input_artifacts: Any,
) -> list[dict[str, Any]]:
    staged: list[dict[str, Any]] = []
    store = get_artifact_store()
    for ref in _normalize_input_refs(input_artifacts):
        artifact = artifact_repo.get_artifact(connection, ref["artifact_id"])
        if artifact is None:
            staged.append({"artifact_id": ref["artifact_id"], "missing": True, "port": ref.get("port")})
            continue
        source = store.get_local_path(_artifact_key(artifact["storage_uri"]))
        dest_name = f"{artifact['artifact_id']}_{Path(artifact['display_name']).name}"
        dest = input_dir / dest_name
        shutil.copy2(source, dest)
        staged.append({
            "port": ref.get("port") or artifact.get("artifact_type"),
            "artifact_id": artifact["artifact_id"],
            "path": f"/input/{dest_name}",
            "format": artifact.get("format"),
            "artifact_type": artifact.get("artifact_type"),
            "metadata": artifact.get("metadata_json") or {},
        })
    return staged


def _merge_input_artifact_refs(left: Any, right: Any) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for ref in _normalize_input_refs(left):
        port = ref.get("port") or "input"
        merged.setdefault(port, [])
        merged[port].append(ref)
    for ref in _normalize_input_refs(right):
        port = ref.get("port") or "input"
        merged.setdefault(port, [])
        artifact_id = ref.get("artifact_id")
        if artifact_id and not any(item.get("artifact_id") == artifact_id for item in merged[port]):
            merged[port].append(ref)
    return merged


def _artifact_matches_source_port(artifact: dict[str, Any], source_port: str) -> bool:
    if source_port in ("output", "outputs", "*"):
        return True
    metadata = artifact.get("metadata_json") or {}
    return source_port in {
        artifact.get("artifact_type"),
        metadata.get("source_port"),
    }


def resolve_node_input_artifacts(connection: sqlite3.Connection, node: dict[str, Any]) -> dict[str, Any]:
    """Resolve explicit node inputs plus workflow-edge inherited artifacts.

    Node ``input_files_json`` stores direct artifact references. DAG edges add
    implicit references from upstream node outputs by mapping source_port to
    target_port. This keeps model runners decoupled: every runner only reads the
    staged ``/input/manifest.json`` contract.
    """
    explicit = node.get("input_files_json") or {}
    edge_inputs: dict[str, list[dict[str, Any]]] = {}
    workflow_run_id = node.get("workflow_run_id")
    node_run_id = node.get("node_run_id")
    if workflow_run_id and node_run_id:
        for edge in catalog.list_workflow_edges(connection, workflow_run_id):
            if edge.get("target_node_run_id") != node_run_id:
                continue
            if edge.get("edge_type", "data") not in {"data", "control", "review_gate"}:
                continue
            source_node_id = edge.get("source_node_run_id")
            source_port = edge.get("source_port") or "output"
            target_port = edge.get("target_port") or "input"
            for artifact in artifact_repo.list_node_artifacts(connection, source_node_id):
                if not _artifact_matches_source_port(artifact, source_port):
                    continue
                edge_inputs.setdefault(target_port, []).append({
                    "port": target_port,
                    "artifact_id": artifact["artifact_id"],
                    "source_node_run_id": source_node_id,
                    "source_port": source_port,
                })
    return _merge_input_artifact_refs(explicit, edge_inputs)


def prepare_job_workspace(
    connection: sqlite3.Connection,
    *,
    job: dict[str, Any],
    node: dict[str, Any],
    plugin: dict | None,
) -> dict[str, Any]:
    paths = _job_workspace(job["job_id"])
    parameters = node.get("parameters_json") or {}
    input_artifacts = job.get("input_artifacts") or resolve_node_input_artifacts(connection, node)
    staged_inputs = _stage_input_artifacts(connection, paths["input"], input_artifacts)
    manifest = {
        "job_id": job["job_id"],
        "project_id": catalog.get_workflow_run_project_id(connection, node["workflow_run_id"]),
        "workflow_run_id": node.get("workflow_run_id"),
        "node_run_id": node.get("node_run_id"),
        "plugin_id": (plugin or {}).get("model_plugin_id") or job.get("plugin_id"),
        "model_name": (plugin or {}).get("model_name") or node.get("model_name"),
        "inputs": staged_inputs,
        "parameters": parameters,
    }
    manifest_path = paths["input"] / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {
        "input_dir": str(paths["input"]),
        "output_dir": str(paths["output"]),
        "work_dir": str(paths["work"]),
        "input_manifest": manifest,
    }


def _manifest_outputs(output_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = output_manifest.get("outputs")
    if isinstance(outputs, dict):
        normalized: list[dict[str, Any]] = []
        for port, entries in outputs.items():
            if isinstance(entries, dict):
                entries = [entries]
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        normalized.append({"port": port, **entry})
        return normalized
    legacy_keys = {
        "backbone_pdbs": "backbone_set",
        "sequences": "sequence_set",
        "structure": "predicted_structure",
        "relaxed_pdb": "relaxed_structure",
    }
    normalized = []
    for key, port in legacy_keys.items():
        value = output_manifest.get(key)
        if isinstance(value, str):
            normalized.append({"port": port, "path": value})
        elif isinstance(value, list):
            normalized.extend({"port": port, "path": item} for item in value if isinstance(item, str))
    return normalized


def collect_job_outputs(connection: sqlite3.Connection, job_id: str) -> dict[str, Any]:
    job = get_job(connection, job_id)
    if job is None:
        raise ValueError("job_not_found")
    existing_outputs = job.get("output_artifacts") or {}
    if existing_outputs.get("manifest_found") is True:
        return existing_outputs
    output_dir = _job_workspace(job_id)["output"]
    adapter = get_compute_adapter()
    collect_remote = getattr(adapter, "collect_outputs", None)
    if callable(collect_remote):
        collect_remote(job_id, str(output_dir))
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        result = {
            "manifest_found": False,
            "contract_valid": False,
            "contract_errors": ["missing_output_manifest"],
            "artifacts": [],
        }
        update_job_status(
            connection,
            job_id,
            status="failed",
            output_artifacts=result,
            error_message="output_contract_failed:missing_output_manifest",
        )
        if job.get("node_run_id"):
            catalog.update_workflow_node(
                connection,
                job["node_run_id"],
                status="failed",
                error_message="output_contract_failed:missing_output_manifest",
            )
        return result
    try:
        output_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        result = {
            "manifest_found": True,
            "contract_valid": False,
            "contract_errors": [f"invalid_output_manifest:{exc.__class__.__name__}"],
            "artifacts": [],
        }
        update_job_status(
            connection,
            job_id,
            status="failed",
            output_artifacts=result,
            error_message="output_contract_failed:invalid_output_manifest",
        )
        if job.get("node_run_id"):
            catalog.update_workflow_node(
                connection,
                job["node_run_id"],
                status="failed",
                error_message="output_contract_failed:invalid_output_manifest",
            )
        return result
    project_id = None
    if job.get("workflow_run_id"):
        project_id = catalog.get_workflow_run_project_id(connection, job["workflow_run_id"])
    registered: list[dict[str, Any]] = []
    store = get_artifact_store()
    for entry in _manifest_outputs(output_manifest):
        raw_path = entry.get("path")
        if not raw_path:
            continue
        source = Path(raw_path)
        if source.is_absolute():
            try:
                source = output_dir / source.relative_to("/output")
            except ValueError:
                source = output_dir / source.name
        else:
            source = output_dir / source
        if not source.exists() or not source.is_file():
            continue
        artifact_format = entry.get("format") or artifact_format_for_filename(source.name)
        relative_path = f"jobs/{job_id}/outputs/{source.name}"
        store.save_file(relative_path, source)
        metadata = {
            **infer_artifact_metadata(source, artifact_format),
            **(entry.get("metadata") or {}),
            "source_job_id": job_id,
            "source_port": entry.get("port"),
        }
        artifact = artifact_repo.create_artifact(
            connection,
            artifact_id=f"art_{uuid.uuid4().hex[:16]}",
            project_id=project_id,
            workflow_run_id=job.get("workflow_run_id"),
            node_run_id=job.get("node_run_id"),
            artifact_type=entry.get("artifact_type") or entry.get("port") or "model_output",
            format=artifact_format,
            storage_uri=f"{ARTIFACT_STORAGE_PREFIX}{relative_path}",
            display_name=entry.get("display_name") or source.name,
            size_bytes=source.stat().st_size,
            checksum=sha256_file(source),
            metadata=metadata,
            created_by="system",
        )
        registered.append(artifact)

    plugin = registry.get_model_plugin(connection, job.get("plugin_id")) if job.get("plugin_id") else None
    output_schema = (plugin or {}).get("output_schema_json") or {}
    if isinstance(output_schema.get("ports"), list):
        required_ports = {
            port["name"]
            for port in output_schema["ports"]
            if port.get("required", True) and port.get("name") != "run_manifest"
        }
    else:
        legacy_port_aliases = {
            "fasta": "sequence_set",
            "backbone_pdbs": "backbone_set",
            "structure": "predicted_structure",
            "relaxed_pdb": "relaxed_structure",
        }
        required_ports = {
            legacy_port_aliases.get(name, name)
            for name in output_schema
            if name not in {"manifest", "run_manifest"}
        }
    produced_ports = {
        (artifact.get("metadata_json") or {}).get("source_port")
        for artifact in registered
    }
    missing_ports = sorted(required_ports - produced_ports)
    result = {
        "manifest_found": True,
        "manifest": output_manifest,
        "artifacts": registered,
        "metrics": output_manifest.get("metrics") or {},
        "contract_valid": not missing_ports,
        "contract_errors": [f"missing_required_output:{port}" for port in missing_ports],
    }
    terminal_status = "completed" if result["contract_valid"] else "failed"
    error_message = (
        None
        if result["contract_valid"]
        else f"output_contract_failed:{','.join(missing_ports)}"
    )
    update_job_status(
        connection,
        job_id,
        status=terminal_status,
        output_artifacts=result,
        error_message=error_message,
    )
    if job.get("node_run_id"):
        catalog.update_workflow_node(
            connection,
            job["node_run_id"],
            status=terminal_status,
            metrics_json=json.dumps(result["metrics"]),
            output_files_json=json.dumps([artifact["artifact_id"] for artifact in registered]),
            error_message=error_message,
        )
    return result


def get_job(connection: sqlite3.Connection, job_id: str) -> dict[str, Any] | None:
    row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    return decode_row(row)


def list_workflow_jobs(connection: sqlite3.Connection, workflow_run_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM jobs WHERE workflow_run_id = ? ORDER BY created_at",
        (workflow_run_id,),
    ).fetchall()
    return decode_rows(rows)


def update_job_status(
    connection: sqlite3.Connection,
    job_id: str,
    *,
    status: str,
    logs: str | None = None,
    output_artifacts: dict | None = None,
    error_message: str | None = None,
    external_id: str | None = None,
) -> dict[str, Any] | None:
    updates = ["status = ?"]
    params: list[Any] = [status]
    if logs is not None:
        updates.append("logs = ?")
        params.append(logs)
    if output_artifacts is not None:
        updates.append("output_artifacts = ?")
        params.append(json.dumps(output_artifacts))
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)
    if external_id is not None:
        updates.append("external_id = ?")
        params.append(external_id)
    if status == "running":
        updates.append("started_at = ?")
        params.append(_now_iso())
    if status in ("completed", "failed", "cancelled"):
        updates.append("finished_at = ?")
        params.append(_now_iso())
    params.append(job_id)
    connection.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?", params)
    return get_job(connection, job_id)


def _plugin_runtime_env(plugin: dict | None) -> dict[str, str]:
    if not plugin:
        return {}
    requirements = plugin.get("resource_requirement_json") or {}
    if isinstance(requirements, str):
        requirements = json.loads(requirements)
    env = dict((requirements.get("runtime_env") or {}))
    gpu_count = requirements.get("gpu_count") or 0
    if gpu_count:
        env.setdefault("BDA_GPU", "1")
    cpu_count = requirements.get("cpu_count")
    if cpu_count:
        env.setdefault("BDA_CPU_COUNT", str(cpu_count))
    memory_gb = requirements.get("memory_gb")
    if memory_gb:
        env.setdefault("BDA_MEMORY_GB", str(memory_gb))
    return env


def parameter_checksum(parameters: dict[str, Any]) -> str:
    payload = json.dumps(parameters, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def node_submission_readiness(
    connection: sqlite3.Connection,
    node_run_id: str,
) -> dict[str, Any]:
    node = get_by_id(connection, "workflow_node_runs", "node_run_id", node_run_id)
    if node is None:
        raise ValueError("node_not_found")
    blockers: list[dict[str, Any]] = []
    plugin = None
    if node.get("model_name"):
        plugin = next(
            (
                item
                for item in registry.list_model_plugins(connection)
                if item.get("model_name") == node.get("model_name")
            ),
            None,
        )
    if plugin is None:
        blockers.append({
            "code": "manual_or_unregistered_node",
            "message": "This node requires manual review/completion and cannot be submitted to compute.",
        })
    if node.get("status") in {"queued", "staging", "running", "completed"}:
        blockers.append({
            "code": "node_not_submittable_status",
            "message": f"Node status is {node.get('status')}.",
        })
    active = connection.execute(
        """
        SELECT job_id, status FROM jobs
        WHERE node_run_id = ? AND status IN ('queued', 'staging', 'running')
        ORDER BY created_at DESC LIMIT 1
        """,
        (node_run_id,),
    ).fetchone()
    if active:
        blockers.append({
            "code": "active_job_exists",
            "message": f"Active job {active['job_id']} already exists.",
        })
    incoming = [
        edge
        for edge in catalog.list_workflow_edges(connection, node["workflow_run_id"])
        if edge.get("target_node_run_id") == node_run_id
        and edge.get("edge_type", "data") in {"data", "control", "review_gate"}
    ]
    for edge in incoming:
        source = get_by_id(
            connection,
            "workflow_node_runs",
            "node_run_id",
            edge["source_node_run_id"],
        )
        if source is None or source.get("status") != "completed":
            blockers.append({
                "code": "upstream_not_completed",
                "source_node_run_id": edge["source_node_run_id"],
                "source_node_name": (source or {}).get("node_name"),
                "source_status": (source or {}).get("status", "missing"),
                "message": "An upstream node or review gate is not completed.",
            })
    parameters = node.get("parameters_json") or {}
    validation: dict[str, Any] = {"valid": True, "errors": [], "warnings": []}
    strict_rfdiffusion = (
        node.get("model_name") == "RFdiffusion"
        and bool(parameters.get("design_mode") or parameters.get("requires_user_review"))
    )
    if strict_rfdiffusion:
        from .sweet_protein_planner import validate_rfdiffusion_parameters

        validation = validate_rfdiffusion_parameters(parameters)
        for error in validation["errors"]:
            blockers.append({
                "code": "invalid_parameter",
                "parameter": error["parameter"],
                "message": error["message"],
            })
        resolved_inputs = resolve_node_input_artifacts(connection, node)
        has_structure_artifact = False
        for ref in _normalize_input_refs(resolved_inputs):
            artifact = artifact_repo.get_artifact(connection, ref["artifact_id"])
            if artifact and artifact.get("artifact_type") in {
                "target_structure",
                "cleaned_structure",
                "structure",
            }:
                has_structure_artifact = True
                break
        if not has_structure_artifact:
            blockers.append({
                "code": "missing_target_structure",
                "message": (
                    "RFdiffusion requires a reviewed target/scaffold structure artifact "
                    "attached to this node before submission."
                ),
            })
    return {
        "ready": not blockers,
        "node": node,
        "plugin": plugin,
        "blockers": blockers,
        "parameter_checksum": parameter_checksum(parameters),
        "validation": validation,
    }


def preview_node_submission(
    connection: sqlite3.Connection,
    node_run_id: str,
) -> dict[str, Any]:
    readiness = node_submission_readiness(connection, node_run_id)
    node = readiness["node"]
    plugin = readiness["plugin"]
    parameters = node.get("parameters_json") or {}
    if (
        node.get("model_name") == "RFdiffusion"
        and bool(parameters.get("design_mode") or parameters.get("requires_user_review"))
    ):
        from .sweet_protein_planner import render_rfdiffusion_command

        model_command_preview = (
            render_rfdiffusion_command(parameters)
            if readiness["validation"]["valid"]
            else ""
        )
    else:
        model_command_preview = ""
    command = (plugin or {}).get("command_template") or ""
    resources = (plugin or {}).get("resource_requirement_json") or {}
    return {
        "node_run_id": node_run_id,
        "ready": readiness["ready"],
        "blockers": readiness["blockers"],
        "parameter_checksum": readiness["parameter_checksum"],
        "model_name": node.get("model_name"),
        "plugin_id": (plugin or {}).get("model_plugin_id"),
        "container_image": (plugin or {}).get("container_image"),
        "resources": resources,
        "command": command,
        "model_command_preview": model_command_preview,
        "inputs": resolve_node_input_artifacts(connection, node),
        "expected_outputs": (plugin or {}).get("output_schema_json") or {},
        "requires_confirmation": True,
        "validation": readiness["validation"],
    }


def _enqueue_poll(job_id: str) -> None:
    try:
        from ..celery_app import poll_job_status

        poll_job_status.delay(job_id)
    except Exception:
        pass


def submit_node_job(
    connection: sqlite3.Connection,
    node_run_id: str,
    compute_node_id: str | None = None,
    *,
    expected_parameter_checksum: str | None = None,
) -> dict:
    readiness = node_submission_readiness(connection, node_run_id)
    node = readiness["node"]
    plugin = readiness["plugin"]
    if readiness["blockers"]:
        codes = ",".join(item["code"] for item in readiness["blockers"])
        raise ValueError(f"node_not_ready:{codes}")
    if (
        (node.get("parameters_json") or {}).get("requires_user_review")
        and not expected_parameter_checksum
    ):
        raise ValueError("node_preview_confirmation_required")
    if (
        expected_parameter_checksum
        and expected_parameter_checksum != readiness["parameter_checksum"]
    ):
        raise ValueError("node_parameters_changed_after_preview")

    plugin_id = (plugin or {}).get("model_plugin_id", "unknown")
    job = create_job(
        connection,
        workflow_run_id=node.get("workflow_run_id"),
        node_run_id=node_run_id,
        plugin_id=plugin_id,
        input_artifacts=resolve_node_input_artifacts(connection, node),
        compute_node_id=compute_node_id,
    )

    runtime_env = _plugin_runtime_env(plugin)
    container_image = (plugin or {}).get("container_image") or "bda/demo:latest"
    command = (plugin or {}).get("command_template") or "echo demo"
    workspace = prepare_job_workspace(connection, job=job, node=node, plugin=plugin)
    update_job_status(
        connection,
        job["job_id"],
        status="staging",
        output_artifacts={"input_manifest": workspace["input_manifest"]},
    )

    spec = JobSpec(
        job_id=job["job_id"],
        workflow_run_id=node.get("workflow_run_id"),
        node_run_id=node_run_id,
        plugin_id=plugin_id,
        container_image=container_image,
        command=command,
        input_artifacts=job.get("input_artifacts") or {},
        compute_node_id=compute_node_id,
        env=runtime_env,
        input_dir=workspace["input_dir"],
        output_dir=workspace["output_dir"],
        work_dir=workspace["work_dir"],
    )
    adapter = get_compute_adapter()
    try:
        handle = adapter.submit(spec)
    except RuntimeError as exc:
        failed_job = update_job_status(
            connection,
            job["job_id"],
            status="failed",
            error_message=str(exc),
        )
        catalog.update_workflow_node(
            connection,
            node_run_id,
            status="failed",
            error_message=str(exc),
        )
        return failed_job or get_job(connection, job["job_id"]) or job

    st = adapter.status(job["job_id"], handle.external_id)
    update_job_status(
        connection,
        job["job_id"],
        status=st.status if st.status != "blocked" else "queued",
        logs=st.logs,
        external_id=handle.external_id,
    )
    if st.status in ("completed", "failed", "cancelled"):
        terminal_status = st.status
        if st.status == "completed":
            collected = collect_job_outputs(connection, job["job_id"])
            terminal_status = "completed" if collected.get("contract_valid") else "failed"
        catalog.update_workflow_node(
            connection,
            node_run_id,
            status="completed" if terminal_status == "completed" else terminal_status,
        )
        from .run_coordinator import handle_job_terminal

        handle_job_terminal(
            connection,
            job=get_job(connection, job["job_id"]) or job,
            status=terminal_status,
        )
    if st.status in ("queued", "running"):
        catalog.update_workflow_node(connection, node_run_id, status="queued")
        _enqueue_poll(job["job_id"])

    return get_job(connection, job["job_id"]) or job


def submit_workflow_jobs(connection: sqlite3.Connection, workflow_run_id: str, compute_node_id: str | None = None) -> list[dict]:
    nodes = catalog.list_workflow_nodes(connection, workflow_run_id)
    jobs = []
    for node in nodes:
        if node.get("status") in ("completed", "running", "queued"):
            continue
        if (node.get("parameters_json") or {}).get("requires_user_review"):
            continue
        try:
            job = submit_node_job(connection, node["node_run_id"], compute_node_id)
            jobs.append(job)
        except ValueError:
            continue
    return jobs
