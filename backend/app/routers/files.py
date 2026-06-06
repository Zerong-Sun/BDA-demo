import re
import tempfile
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..config import UPLOADS_ROOT
from ..db import get_connection
from ..repositories import catalog
from ..services.artifacts import (
    candidate_structure_path,
    ensure_artifact_dirs,
    parse_pdb_metadata,
    resolve_artifact_path,
)
from ..services.artifact_store import get_artifact_store
from ..utils.response import envelope

router = APIRouter()

SAFE_FILENAME_RE = re.compile(r"^[\w.\-]+$")


def _safe_upload_filename(filename: str) -> str:
    base = Path(filename).name
    if not base or not SAFE_FILENAME_RE.match(base):
        raise HTTPException(status_code=400, detail="invalid_filename")
    return base


@router.post("/targets/upload-pdb")
async def upload_pdb(
    file: UploadFile = File(...),
    project_id: str | None = Form(default=None),
    connection=Depends(get_connection),
):
    ensure_artifact_dirs()
    filename = _safe_upload_filename(file.filename or "upload.pdb")
    lower = filename.lower()
    if not (lower.endswith(".pdb") or lower.endswith(".cif") or lower.endswith(".mmcif")):
        raise HTTPException(status_code=400, detail="unsupported_structure_format")

    file_id = str(uuid.uuid4())
    suffix = Path(filename).suffix or ".pdb"
    stored_name = f"{file_id}{suffix}"
    relative_path = f"uploads/{stored_name}"

    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        content_preview = ""
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)
        tmp.flush()

    try:
        content_preview = tmp_path.read_text(encoding="utf-8", errors="replace")
        metadata = parse_pdb_metadata(content_preview)
        store = get_artifact_store()
        store.save_file(relative_path, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    target = None
    if project_id:
        target = catalog.upsert_target_upload(
            connection,
            project_id=project_id,
            filename=filename,
            structure_file_path=relative_path,
            metadata=metadata,
        )

    return envelope({
        "file_id": file_id,
        "filename": filename,
        "project_id": project_id,
        "atom_count": metadata["atom_count"],
        "chain_count": metadata["chain_count"],
        "chains": metadata["chains"],
        "residue_count": metadata.get("residue_count"),
        "preview_url": f"/api/v1/artifacts/uploads/{stored_name}",
        "target": target,
    })


@router.get("/candidates/{candidate_id}/structure-file")
def candidate_structure_file(candidate_id: str, connection=Depends(get_connection)):
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
def uploaded_structure_preview(filename: str):
    safe_name = _safe_upload_filename(filename)
    path = resolve_artifact_path(f"uploads/{safe_name}")
    media_type = "chemical/x-pdb" if path.suffix.lower() == ".pdb" else "chemical/x-mmcif"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/artifacts/{artifact_path:path}")
def download_artifact(artifact_path: str):
    normalized = artifact_path.lstrip("/")
    if normalized.startswith("uploads/"):
        filename = normalized.split("/", 1)[1]
        return uploaded_structure_preview(filename)
    path = resolve_artifact_path(normalized)
    return FileResponse(path, filename=path.name)


@router.get("/projects/{project_id}/delivery-package/download")
def download_delivery_package(project_id: str, connection=Depends(get_connection)):
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

        return FileResponse(
            tmp_path,
            media_type="application/zip",
            filename=f"{project_id}_delivery.zip",
            background=None,
        )
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
