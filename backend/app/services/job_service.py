from __future__ import annotations

import json
import re
import shutil
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..compute.adapter import JobSpec
from ..compute.factory import get_compute_adapter
from ..config import ARTIFACTS_ROOT
from ..repositories import artifacts as artifact_repo
from ..repositories import catalog, registry
from ..repositories.base import decode_row, decode_rows, get_by_id
from ..services.artifact_store import get_artifact_store
from ..services.artifacts import artifact_format_for_filename, infer_artifact_metadata, sha256_file

ARTIFACT_STORAGE_PREFIX = "artifact://"
LEGACY_ARTIFACT_STORAGE_PREFIXES = ("local://",)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


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


def _candidate_family_for_artifact(entry: dict[str, Any], artifact: dict[str, Any], job: dict[str, Any]) -> str:
    metadata = artifact.get("metadata_json") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return str(
        entry.get("family")
        or entry.get("route")
        or metadata.get("route")
        or metadata.get("source_port")
        or job.get("plugin_id")
        or "generated"
    )


def _register_generated_candidate(
    connection: sqlite3.Connection,
    *,
    project_id: str | None,
    job: dict[str, Any],
    artifact: dict[str, Any],
    entry: dict[str, Any],
) -> None:
    if not project_id or not job.get("workflow_run_id"):
        return
    artifact_format = str(artifact.get("format") or "").lower()
    artifact_type = str(artifact.get("artifact_type") or "").lower()
    source_port = str(entry.get("port") or "").lower()
    metadata = artifact.get("metadata_json") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    if artifact_type in {"predicted_structure", "complex_structure"} or source_port in {"predicted_structure", "complex_structure"}:
        raw_candidate_id = entry.get("candidate_id") or metadata.get("candidate_id")
        if not raw_candidate_id:
            return
        candidate_id = str(raw_candidate_id)
        if not candidate_id.startswith("cand_"):
            candidate_id = f"cand_{candidate_id}"
        storage_uri = str(artifact.get("storage_uri") or "")
        structure_file_path = storage_uri[len(ARTIFACT_STORAGE_PREFIX):] if storage_uri.startswith(ARTIFACT_STORAGE_PREFIX) else storage_uri
        connection.execute(
            """
            UPDATE candidates
            SET complex_file_path = ?,
                plddt = COALESCE(?, plddt),
                status = 'folded',
                next_action = 'Review AlphaFold2/Superfold pLDDT and continue developability scoring.'
            WHERE candidate_id = ? AND project_id = ?
            """,
            (structure_file_path, metadata.get("plddt"), candidate_id, project_id),
        )
        return
    if artifact_format not in {"pdb", "mmcif", "cif"} and not any(
        token in artifact_type or token in source_port
        for token in ("structure", "backbone", "pdb", "model")
    ):
        return
    task = catalog.get_project_design_task(connection, project_id)
    if task is None:
        return
    raw_id = entry.get("candidate_id") or Path(str(artifact.get("display_name") or artifact["artifact_id"])).stem
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(raw_id)).strip("_")[:80] or artifact["artifact_id"]
    candidate_id = safe_id if safe_id.startswith("cand_") else f"cand_{safe_id}"
    storage_uri = str(artifact.get("storage_uri") or "")
    structure_file_path = storage_uri[len(ARTIFACT_STORAGE_PREFIX):] if storage_uri.startswith(ARTIFACT_STORAGE_PREFIX) else storage_uri
    connection.execute(
        """
        INSERT INTO candidates (
            candidate_id, project_id, task_id, workflow_run_id, family, sequence,
            structure_file_path, complex_file_path, interface_score, pred_kd,
            plddt, interface_pae, rosetta_score, interface_energy, clash_count,
            buried_sasa, solubility_score, aggregation_risk, expression_risk,
            status, decision, next_action
        ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                  'generated_backbone', 'Needs scoring', 'Run sequence design, folding, and scoring.')
        ON CONFLICT(candidate_id) DO UPDATE SET
            project_id=excluded.project_id,
            task_id=excluded.task_id,
            workflow_run_id=excluded.workflow_run_id,
            family=excluded.family,
            sequence=COALESCE(excluded.sequence, candidates.sequence),
            structure_file_path=excluded.structure_file_path,
            status=excluded.status,
            decision=excluded.decision,
            next_action=excluded.next_action
        """,
        (
            candidate_id,
            project_id,
            task["task_id"],
            job["workflow_run_id"],
            _candidate_family_for_artifact(entry, artifact, job),
            entry.get("sequence") or metadata.get("sequence"),
            structure_file_path,
        ),
    )


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
        return {"manifest_found": False, "artifacts": []}
    output_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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
        _register_generated_candidate(
            connection,
            project_id=project_id,
            job=job,
            artifact=artifact,
            entry=entry,
        )

    result = {
        "manifest_found": True,
        "manifest": output_manifest,
        "artifacts": registered,
        "metrics": output_manifest.get("metrics") or {},
    }
    update_job_status(connection, job_id, status="completed", output_artifacts=result)
    if job.get("node_run_id"):
        catalog.update_workflow_node(
            connection,
            job["node_run_id"],
            status="completed",
            metrics_json=json.dumps(result["metrics"]),
            output_files_json=json.dumps([artifact["artifact_id"] for artifact in registered]),
        )
    return result


def get_job(connection: sqlite3.Connection, job_id: str) -> dict[str, Any] | None:
    row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    return decode_row(row)


def list_workflow_jobs(
    connection: sqlite3.Connection,
    workflow_run_id: str,
    *,
    chronological: bool = False,
) -> list[dict[str, Any]]:
    order_by = "created_at ASC, rowid ASC" if chronological else "created_at DESC, rowid DESC"
    rows = connection.execute(
        f"SELECT * FROM jobs WHERE workflow_run_id = ? ORDER BY {order_by}",
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
    env = dict(requirements.get("runtime_env") or {})
    gpu_count = requirements.get("gpu_count") or 0
    if gpu_count:
        env.setdefault("BDA_GPU", "1")
    return env


def _plugin_for_node(connection: sqlite3.Connection, node: dict[str, Any]) -> dict | None:
    if not node.get("model_name"):
        return None
    plugins = registry.list_model_plugins(connection)
    return next((p for p in plugins if p.get("model_name") == node.get("model_name")), None)


def _node_parameters(node: dict[str, Any]) -> dict[str, Any]:
    parameters = node.get("parameters_json") or {}
    if isinstance(parameters, str):
        try:
            parsed = json.loads(parameters)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return parameters if isinstance(parameters, dict) else {}


def _node_with_parameters(node: dict[str, Any], parameters: dict[str, Any] | None) -> dict[str, Any]:
    if parameters is None:
        return node
    merged = {**_node_parameters(node), **parameters}
    return {**node, "parameters_json": merged}


def _build_node_job_spec(
    connection: sqlite3.Connection,
    *,
    node: dict[str, Any],
    job: dict[str, Any],
    plugin: dict | None,
    compute_node_id: str | None = None,
    queue_name: str | None = None,
    cpu_count: int | None = None,
    resource_requirement: str | None = None,
    gpu_requirement: str | None = None,
) -> tuple[JobSpec, dict[str, Any]]:
    plugin_id = (plugin or {}).get("model_plugin_id") or job.get("plugin_id") or "unknown"
    runtime_env = _plugin_runtime_env(plugin)
    if queue_name:
        runtime_env["BDA_LSF_QUEUE"] = queue_name
    if cpu_count:
        runtime_env["BDA_CPU_COUNT"] = str(max(1, min(int(cpu_count), 256)))
    if resource_requirement:
        runtime_env["BDA_LSF_RESOURCE"] = resource_requirement
    if gpu_requirement:
        runtime_env["BDA_LSF_GPU"] = gpu_requirement

    workspace = prepare_job_workspace(connection, job=job, node=node, plugin=plugin)
    spec = JobSpec(
        job_id=job["job_id"],
        workflow_run_id=node.get("workflow_run_id"),
        node_run_id=node.get("node_run_id"),
        plugin_id=plugin_id,
        container_image=(plugin or {}).get("container_image") or "bda/demo:latest",
        command=(plugin or {}).get("command_template") or "echo demo",
        input_artifacts=job.get("input_artifacts") or {},
        compute_node_id=compute_node_id,
        env=runtime_env,
        input_dir=workspace["input_dir"],
        output_dir=workspace["output_dir"],
        work_dir=workspace["work_dir"],
        queue_name=queue_name,
        resource_requirement=resource_requirement,
        gpu_requirement=gpu_requirement,
    )
    return spec, workspace


def preview_node_job_script(
    connection: sqlite3.Connection,
    node_run_id: str,
    *,
    override_params: dict[str, Any] | None = None,
    compute_node_id: str | None = None,
    queue_name: str | None = None,
    cpu_count: int | None = None,
    resource_requirement: str | None = None,
    gpu_requirement: str | None = None,
) -> dict[str, Any]:
    node = get_by_id(connection, "workflow_node_runs", "node_run_id", node_run_id)
    if node is None:
        raise ValueError("node_not_found")
    preview_node = _node_with_parameters(node, override_params)
    plugin = _plugin_for_node(connection, preview_node)
    plugin_id = (plugin or {}).get("model_plugin_id", "unknown")
    job = {
        "job_id": f"job_preview_{uuid.uuid4().hex[:10]}",
        "workflow_run_id": preview_node.get("workflow_run_id"),
        "node_run_id": node_run_id,
        "plugin_id": plugin_id,
        "input_artifacts": resolve_node_input_artifacts(connection, preview_node),
        "compute_node_id": compute_node_id,
    }
    spec, workspace = _build_node_job_spec(
        connection,
        node=preview_node,
        job=job,
        plugin=plugin,
        compute_node_id=compute_node_id,
        queue_name=queue_name,
        cpu_count=cpu_count,
        resource_requirement=resource_requirement,
        gpu_requirement=gpu_requirement,
    )
    adapter = get_compute_adapter()
    try:
        script = adapter.render_script(spec)
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc
    return {
        "job_id": spec.job_id,
        "plugin_id": plugin_id,
        "script": script,
        "input_manifest": workspace["input_manifest"],
        "local_workspace": {
            "input_dir": workspace["input_dir"],
            "output_dir": workspace["output_dir"],
            "work_dir": workspace["work_dir"],
        },
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
    queue_name: str | None = None,
    cpu_count: int | None = None,
    resource_requirement: str | None = None,
    gpu_requirement: str | None = None,
    override_params: dict[str, Any] | None = None,
) -> dict:
    node = get_by_id(connection, "workflow_node_runs", "node_run_id", node_run_id)
    if node is None:
        raise ValueError("node_not_found")
    if override_params is not None:
        node = _node_with_parameters(node, override_params)
        catalog.update_workflow_node(
            connection,
            node_run_id,
            parameters_json=json.dumps(_node_parameters(node)),
        )

    plugin = _plugin_for_node(connection, node)

    plugin_id = (plugin or {}).get("model_plugin_id", "unknown")
    job = create_job(
        connection,
        workflow_run_id=node.get("workflow_run_id"),
        node_run_id=node_run_id,
        plugin_id=plugin_id,
        input_artifacts=resolve_node_input_artifacts(connection, node),
        compute_node_id=compute_node_id,
    )

    spec, workspace = _build_node_job_spec(
        connection,
        node=node,
        job=job,
        plugin=plugin,
        compute_node_id=compute_node_id,
        queue_name=queue_name,
        cpu_count=cpu_count,
        resource_requirement=resource_requirement,
        gpu_requirement=gpu_requirement,
    )
    update_job_status(
        connection,
        job["job_id"],
        status="staging",
        output_artifacts={"input_manifest": workspace["input_manifest"]},
    )
    adapter = get_compute_adapter()
    try:
        handle = adapter.submit(spec)
    except RuntimeError as exc:
        update_job_status(connection, job["job_id"], status="failed", error_message=str(exc))
        raise ValueError(str(exc)) from exc

    st = adapter.status(job["job_id"], handle.external_id)
    update_job_status(
        connection,
        job["job_id"],
        status=st.status if st.status != "blocked" else "queued",
        logs=st.logs,
        external_id=handle.external_id,
    )
    if st.status == "completed":
        collect_job_outputs(connection, job["job_id"])
    if st.status in ("queued", "running"):
        catalog.update_workflow_node(connection, node_run_id, status="queued")
        _enqueue_poll(job["job_id"])

    return get_job(connection, job["job_id"]) or job


def submit_workflow_jobs(
    connection: sqlite3.Connection,
    workflow_run_id: str,
    compute_node_id: str | None = None,
    *,
    queue_name: str | None = None,
    cpu_count: int | None = None,
    resource_requirement: str | None = None,
    gpu_requirement: str | None = None,
) -> list[dict]:
    nodes = catalog.list_workflow_nodes(connection, workflow_run_id)
    jobs = []
    for node in nodes:
        if node.get("status") in ("completed", "running", "queued"):
            continue
        try:
            job = submit_node_job(
                connection,
                node["node_run_id"],
                compute_node_id,
                queue_name=queue_name,
                cpu_count=cpu_count,
                resource_requirement=resource_requirement,
                gpu_requirement=gpu_requirement,
            )
            jobs.append(job)
        except ValueError:
            continue
    return jobs
