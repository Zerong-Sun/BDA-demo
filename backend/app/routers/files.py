import json
import re
import sqlite3
import tempfile
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..auth.deps import get_current_user, require_candidate_access, require_project_access
from ..auth.service import verify_project_access
from ..config import REPO_ROOT
from ..db import get_connection
from ..repositories import artifacts as artifact_repo
from ..repositories import catalog
from ..services.artifact_store import get_artifact_store
from ..services.artifacts import (
    artifact_format_for_filename,
    candidate_structure_path,
    ensure_artifact_dirs,
    infer_artifact_metadata,
    media_type_for_format,
    parse_pdb_metadata,
    preview_artifact,
    resolve_artifact_path,
    sha256_file,
)
from ..settings import get_settings
from ..utils.response import envelope

router = APIRouter()

SAFE_FILENAME_RE = re.compile(r"^[\w.\-]+$")
ARTIFACT_STORAGE_PREFIX = "artifact://"
FILE_ARTIFACT_STORAGE_PREFIX = "file://"
WORKSPACE_ROOT = REPO_ROOT.parent
LEGACY_ARTIFACT_STORAGE_PREFIXES = ("local://",)


class BatchArtifactDownloadRequest(BaseModel):
    artifact_ids: list[str] = Field(default_factory=list, min_length=1, max_length=200)
    filename: str = "artifacts.zip"


class BatchCandidateDownloadRequest(BaseModel):
    candidate_ids: list[str] = Field(default_factory=list, min_length=1, max_length=500)
    filename: str = "candidate_structures.zip"


def _safe_upload_filename(filename: str) -> str:
    base = Path(filename).name
    if not base or not SAFE_FILENAME_RE.match(base):
        raise HTTPException(status_code=400, detail="invalid_filename")
    return base


def _artifact_key(storage_uri: str) -> str:
    if not storage_uri.startswith(ARTIFACT_STORAGE_PREFIX):
        for prefix in LEGACY_ARTIFACT_STORAGE_PREFIXES:
            if storage_uri.startswith(prefix):
                return storage_uri[len(prefix):]
        raise HTTPException(status_code=400, detail="unsupported_artifact_storage")
    return storage_uri[len(ARTIFACT_STORAGE_PREFIX):]


def _artifact_file_path(storage_uri: str):
    if storage_uri.startswith(FILE_ARTIFACT_STORAGE_PREFIX):
        raw = storage_uri[len(FILE_ARTIFACT_STORAGE_PREFIX):]
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = WORKSPACE_ROOT / raw
        resolved = candidate.resolve()
        if not str(resolved).startswith(str(WORKSPACE_ROOT.resolve())):
            raise HTTPException(status_code=400, detail="invalid_artifact_path")
        if not resolved.exists() or not resolved.is_file():
            raise HTTPException(status_code=404, detail="artifact_not_found")
        return resolved
    return resolve_artifact_path(_artifact_key(storage_uri))


def _artifact_payload(artifact: dict) -> dict:
    artifact_id = artifact["artifact_id"]
    return {
        **artifact,
        "download_url": f"/api/v1/artifacts/{artifact_id}/download",
        "preview_url": f"/api/v1/artifacts/{artifact_id}/preview",
    }


def _metadata_from_form(metadata_json: str | None) -> dict:
    if not metadata_json:
        return {}
    try:
        payload = json.loads(metadata_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid_metadata_json") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="metadata_json_must_be_object")
    return payload


def _require_artifact_access(connection: sqlite3.Connection, user: dict, artifact: dict) -> None:
    project_id = artifact.get("project_id")
    if project_id and not verify_project_access(connection, user, project_id):
        raise HTTPException(status_code=403, detail="forbidden")


def _resolve_project_for_artifact(
    connection: sqlite3.Connection,
    *,
    project_id: str | None,
    workflow_run_id: str | None,
    node_run_id: str | None,
) -> str | None:
    resolved = project_id
    if node_run_id:
        node = catalog.get_workflow_node(connection, node_run_id)
        if node is None:
            raise HTTPException(status_code=404, detail="node_not_found")
        workflow_run_id = workflow_run_id or node.get("workflow_run_id")
    if workflow_run_id:
        workflow_project_id = catalog.get_workflow_run_project_id(connection, workflow_run_id)
        if workflow_project_id is None:
            raise HTTPException(status_code=404, detail="workflow_run_not_found")
        if resolved and resolved != workflow_project_id:
            raise HTTPException(status_code=400, detail="project_workflow_mismatch")
        resolved = workflow_project_id
    return resolved


def _save_artifact_upload(
    connection: sqlite3.Connection,
    *,
    source_path: Path,
    filename: str,
    stored_name: str,
    relative_path: str,
    project_id: str | None,
    workflow_run_id: str | None,
    node_run_id: str | None,
    artifact_type: str,
    metadata: dict,
    created_by: str | None,
) -> dict:
    artifact_format = artifact_format_for_filename(filename)
    inferred = infer_artifact_metadata(source_path, artifact_format)
    merged_metadata = {**inferred, **metadata}
    store = get_artifact_store()
    store.save_file(relative_path, source_path)
    artifact = artifact_repo.create_artifact(
        connection,
        artifact_id=f"art_{uuid.uuid4().hex[:16]}",
        project_id=project_id,
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
        artifact_type=artifact_type,
        format=artifact_format,
        storage_uri=f"{ARTIFACT_STORAGE_PREFIX}{relative_path}",
        display_name=filename,
        size_bytes=source_path.stat().st_size,
        checksum=sha256_file(source_path),
        metadata=merged_metadata,
        created_by=created_by,
    )
    return _artifact_payload({
        **artifact,
        "file_id": stored_name.split(".")[0],
    })


def _process_pdb_upload(
    connection: sqlite3.Connection,
    *,
    filename: str,
    suffix: str,
    stored_name: str,
    relative_path: str,
    project_id: str | None,
    tmp_path: Path,
    created_by: str | None,
) -> dict:
    content_preview = tmp_path.read_text(encoding="utf-8", errors="replace")
    metadata = parse_pdb_metadata(content_preview)
    store = get_artifact_store()
    store.save_file(relative_path, tmp_path)
    artifact_format = artifact_format_for_filename(filename)
    artifact = artifact_repo.create_artifact(
        connection,
        artifact_id=f"art_{uuid.uuid4().hex[:16]}",
        project_id=project_id,
        workflow_run_id=None,
        node_run_id=None,
        artifact_type="target_structure",
        format=artifact_format,
        storage_uri=f"{ARTIFACT_STORAGE_PREFIX}{relative_path}",
        display_name=filename,
        size_bytes=tmp_path.stat().st_size,
        checksum=sha256_file(tmp_path),
        metadata=metadata,
        created_by=created_by,
    )

    target = None
    if project_id:
        target = catalog.upsert_target_upload(
            connection,
            project_id=project_id,
            filename=filename,
            structure_file_path=relative_path,
            metadata=metadata,
        )

    return {
        "file_id": stored_name.split(".")[0],
        "filename": filename,
        "project_id": project_id,
        "atom_count": metadata["atom_count"],
        "chain_count": metadata["chain_count"],
        "chains": metadata["chains"],
        "residue_count": metadata.get("residue_count"),
        "preview_url": f"/api/v1/artifacts/uploads/{stored_name}",
        "artifact": _artifact_payload(artifact),
        "target": target,
    }


@router.post("/artifacts/upload")
async def upload_artifact(
    file: UploadFile = File(...),
    project_id: str | None = Form(default=None),
    workflow_run_id: str | None = Form(default=None),
    node_run_id: str | None = Form(default=None),
    artifact_type: str = Form(default="uploaded_file"),
    metadata_json: str | None = Form(default=None),
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    ensure_artifact_dirs()
    resolved_project_id = _resolve_project_for_artifact(
        connection,
        project_id=project_id,
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
    )
    if resolved_project_id and not verify_project_access(connection, user, resolved_project_id):
        raise HTTPException(status_code=403, detail="forbidden")

    filename = _safe_upload_filename(file.filename or "upload.dat")
    artifact_format_for_filename(filename)
    metadata = _metadata_from_form(metadata_json)
    suffix = Path(filename).suffix
    stored_name = f"{uuid.uuid4()}{suffix}"
    relative_path = f"uploads/{stored_name}"
    max_bytes = get_settings().bda_max_upload_bytes

    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        written = 0
        while chunk := await file.read(1024 * 1024):
            written += len(chunk)
            if written > max_bytes:
                tmp.flush()
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"file_too_large_max_{max_bytes}_bytes")
            tmp.write(chunk)
        tmp.flush()

    try:
        payload = await run_in_threadpool(
            _save_artifact_upload,
            connection,
            source_path=tmp_path,
            filename=filename,
            stored_name=stored_name,
            relative_path=relative_path,
            project_id=resolved_project_id,
            workflow_run_id=workflow_run_id,
            node_run_id=node_run_id,
            artifact_type=artifact_type,
            metadata=metadata,
            created_by=user.get("user_id") or user.get("username"),
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    return envelope(payload)


@router.get("/projects/{project_id}/artifacts")
def project_artifacts(
    project_id: str,
    artifact_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_project_access),
):
    items, total = artifact_repo.list_project_artifacts(
        connection,
        project_id,
        artifact_type=artifact_type,
        limit=max(1, min(limit, 200)),
        offset=max(0, offset),
    )
    return envelope({
        "items": [_artifact_payload(item) for item in items],
        "total": total,
        "limit": max(1, min(limit, 200)),
        "offset": max(0, offset),
    })


@router.get("/artifacts/{artifact_id}")
def artifact_detail(
    artifact_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    artifact = artifact_repo.get_artifact(connection, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    _require_artifact_access(connection, user, artifact)
    return envelope(_artifact_payload(artifact))


@router.post("/artifacts/batch-download")
def batch_download_artifacts(
    payload: BatchArtifactDownloadRequest,
    background_tasks: BackgroundTasks,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    safe_filename = _safe_upload_filename(payload.filename)
    if not safe_filename.lower().endswith(".zip"):
        safe_filename = f"{safe_filename}.zip"

    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for artifact_id in payload.artifact_ids:
                artifact = artifact_repo.get_artifact(connection, artifact_id)
                if artifact is None:
                    raise HTTPException(status_code=404, detail=f"artifact_not_found:{artifact_id}")
                _require_artifact_access(connection, user, artifact)
                path = _artifact_file_path(artifact["storage_uri"])
                archive.write(path, arcname=artifact["display_name"])
        background_tasks.add_task(tmp_path.unlink, missing_ok=True)
        return FileResponse(tmp_path, media_type="application/zip", filename=safe_filename)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


@router.post("/candidates/batch-download")
def batch_download_candidate_structures(
    payload: BatchCandidateDownloadRequest,
    background_tasks: BackgroundTasks,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    safe_filename = _safe_upload_filename(payload.filename)
    if not safe_filename.lower().endswith(".zip"):
        safe_filename = f"{safe_filename}.zip"

    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    manifest: list[dict] = []
    missing: list[str] = []
    written = 0

    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for candidate_id in dict.fromkeys(payload.candidate_ids):
                candidate = catalog.get_candidate(connection, candidate_id)
                if candidate is None:
                    missing.append(f"{candidate_id}: candidate_not_found")
                    continue
                if not verify_project_access(connection, user, candidate["project_id"]):
                    raise HTTPException(status_code=403, detail="forbidden")

                relative = candidate_structure_path(
                    candidate.get("structure_file_path"),
                    candidate.get("complex_file_path"),
                )
                if not relative:
                    missing.append(f"{candidate_id}: structure_not_available")
                    continue

                try:
                    path = resolve_artifact_path(relative)
                except HTTPException as exc:
                    missing.append(f"{candidate_id}: {exc.detail}")
                    continue

                arcname = f"{candidate_id}/{path.name}"
                archive.write(path, arcname=arcname)
                written += 1
                manifest.append({
                    "candidate_id": candidate_id,
                    "project_id": candidate.get("project_id"),
                    "family": candidate.get("family"),
                    "structure_file_path": relative,
                    "archive_path": arcname,
                    "interface_score": candidate.get("interface_score"),
                    "plddt": candidate.get("plddt"),
                    "status": candidate.get("status"),
                    "decision": candidate.get("decision"),
                })

            archive.writestr("manifest.json", json.dumps(manifest, indent=2))
            if missing:
                archive.writestr("missing_files.txt", "\n".join(missing) + "\n")

        if written == 0:
            tmp_path.unlink(missing_ok=True)
            raise HTTPException(status_code=404, detail="no_candidate_structures_available")

        background_tasks.add_task(tmp_path.unlink, missing_ok=True)
        return FileResponse(tmp_path, media_type="application/zip", filename=safe_filename)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


@router.get("/artifacts/{artifact_id}/preview")
def artifact_preview(
    artifact_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    artifact = artifact_repo.get_artifact(connection, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    _require_artifact_access(connection, user, artifact)
    path = _artifact_file_path(artifact["storage_uri"])
    return envelope({
        "artifact": _artifact_payload(artifact),
        "preview": preview_artifact(path, artifact["format"]),
    })


@router.get("/artifacts/{artifact_id}/download")
def artifact_download(
    artifact_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    artifact = artifact_repo.get_artifact(connection, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    _require_artifact_access(connection, user, artifact)
    path = _artifact_file_path(artifact["storage_uri"])
    return FileResponse(
        path,
        media_type=media_type_for_format(artifact["format"]),
        filename=artifact["display_name"],
    )


@router.post("/targets/upload-pdb")
async def upload_pdb(
    file: UploadFile = File(...),
    project_id: str | None = Form(default=None),
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    if project_id and not verify_project_access(connection, user, project_id):
        raise HTTPException(status_code=403, detail="forbidden")

    ensure_artifact_dirs()
    filename = _safe_upload_filename(file.filename or "upload.pdb")
    lower = filename.lower()
    if not (lower.endswith(".pdb") or lower.endswith(".cif") or lower.endswith(".mmcif")):
        raise HTTPException(status_code=400, detail="unsupported_structure_format")

    file_id = str(uuid.uuid4())
    suffix = Path(filename).suffix or ".pdb"
    stored_name = f"{file_id}{suffix}"
    relative_path = f"uploads/{stored_name}"

    max_bytes = get_settings().bda_max_upload_bytes
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        written = 0
        while chunk := await file.read(1024 * 1024):
            written += len(chunk)
            if written > max_bytes:
                tmp.flush()
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"file_too_large_max_{max_bytes}_bytes",
                )
            tmp.write(chunk)
        tmp.flush()

    try:
        payload = await run_in_threadpool(
            _process_pdb_upload,
            connection,
            filename=filename,
            suffix=suffix,
            stored_name=stored_name,
            relative_path=relative_path,
            project_id=project_id,
            tmp_path=tmp_path,
            created_by=user.get("user_id") or user.get("username"),
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    payload["file_id"] = file_id
    return envelope(payload)


@router.get("/candidates/{candidate_id}/structure-file")
def candidate_structure_file(
    candidate_id: str,
    connection=Depends(get_connection),
    _user: dict = Depends(require_candidate_access),
):
    candidate = catalog.get_candidate(connection, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="candidate_not_found")

    relative = candidate_structure_path(
        candidate.get("structure_file_path"),
        candidate.get("complex_file_path"),
    )
    if not relative:
        raise HTTPException(status_code=404, detail="structure_not_available")

    path = resolve_artifact_path(relative)
    media_type = "chemical/x-pdb" if path.suffix.lower() == ".pdb" else "chemical/x-mmcif"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.head("/candidates/{candidate_id}/structure-file")
def candidate_structure_file_head(
    candidate_id: str,
    connection=Depends(get_connection),
    _user: dict = Depends(require_candidate_access),
):
    candidate = catalog.get_candidate(connection, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="candidate_not_found")
    relative = candidate_structure_path(
        candidate.get("structure_file_path"),
        candidate.get("complex_file_path"),
    )
    if not relative:
        raise HTTPException(status_code=404, detail="structure_not_available")
    path = resolve_artifact_path(relative)
    media_type = "chemical/x-pdb" if path.suffix.lower() == ".pdb" else "chemical/x-mmcif"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/artifacts/uploads/{filename}")
def uploaded_structure_preview(
    filename: str,
    _user: dict = Depends(get_current_user),
):
    safe_name = _safe_upload_filename(filename)
    path = resolve_artifact_path(f"uploads/{safe_name}")
    media_type = "chemical/x-pdb" if path.suffix.lower() == ".pdb" else "chemical/x-mmcif"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/artifacts/{artifact_path:path}")
def download_artifact(
    artifact_path: str,
    _user: dict = Depends(get_current_user),
):
    normalized = artifact_path.lstrip("/")
    if normalized.startswith("uploads/"):
        filename = normalized.split("/", 1)[1]
        return uploaded_structure_preview(filename, _user=_user)
    path = resolve_artifact_path(normalized)
    return FileResponse(path, filename=path.name)


@router.head("/artifacts/{artifact_path:path}")
def download_artifact_head(
    artifact_path: str,
    _user: dict = Depends(get_current_user),
):
    normalized = artifact_path.lstrip("/")
    if normalized.startswith("uploads/"):
        filename = normalized.split("/", 1)[1]
        safe_name = _safe_upload_filename(filename)
        path = resolve_artifact_path(f"uploads/{safe_name}")
    else:
        path = resolve_artifact_path(normalized)
    return FileResponse(path, filename=path.name)


@router.get("/projects/{project_id}/delivery-package/download")
def download_delivery_package(
    project_id: str,
    background_tasks: BackgroundTasks,
    connection=Depends(get_connection),
    _user: dict = Depends(require_project_access),
):
    package = catalog.get_project_delivery_package(connection, project_id)
    if package is None:
        raise HTTPException(status_code=404, detail="delivery_package_not_found")

    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as archive:
            readme = (
                "BDA Workbench delivery package (demo).\n"
                f"Project: {project_id}\n"
                f"Summary: {package.get('experiment_summary') or 'N/A'}\n"
            )
            archive.writestr("README.txt", readme)

            for key in ("report_file", "fasta_file", "structure_bundle", "score_table"):
                relative = package.get(key)
                if not relative:
                    continue
                try:
                    path = resolve_artifact_path(str(relative))
                    archive.write(path, arcname=Path(str(relative)).name)
                except HTTPException:
                    archive.writestr(
                        f"missing/{Path(str(relative)).name}.txt",
                        f"Placeholder for missing artifact: {relative}\n",
                    )

        background_tasks.add_task(tmp_path.unlink, missing_ok=True)
        return FileResponse(
            tmp_path,
            media_type="application/zip",
            filename=f"{project_id}_delivery.zip",
        )
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
