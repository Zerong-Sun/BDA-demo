import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from ..config import ARTIFACTS_ROOT, STRUCTURES_ROOT, UPLOADS_ROOT
from ..db import get_connection
from ..repositories import catalog
from ..services.artifacts import (
    candidate_structure_path,
    ensure_artifact_dirs,
    parse_pdb_metadata,
    resolve_artifact_path,
)

router = APIRouter()


def envelope(data):
    from uuid import uuid4

    return {"data": data, "trace_id": str(uuid4())}


@router.post("/targets/upload-pdb")
async def upload_pdb(
    file: UploadFile = File(...),
    project_id: str | None = Form(default=None),
    connection=Depends(get_connection),
):
    ensure_artifact_dirs()
    filename = file.filename or "upload.pdb"
    lower = filename.lower()
    if not (lower.endswith(".pdb") or lower.endswith(".cif") or lower.endswith(".mmcif")):
        raise HTTPException(status_code=400, detail="unsupported_structure_format")

    content = (await file.read()).decode("utf-8", errors="replace")
    metadata = parse_pdb_metadata(content)

    file_id = str(uuid.uuid4())
    suffix = Path(filename).suffix or ".pdb"
    stored_name = f"{file_id}{suffix}"
    stored_path = UPLOADS_ROOT / stored_name
    stored_path.write_text(content, encoding="utf-8")
    relative_path = f"uploads/{stored_name}"

    target = None
    if project_id:
        target = catalog.upsert_target_upload(
            connection,
            project_id=project_id,
            filename=filename,
            structure_file_path=relative_path,
            metadata=metadata,
        )

    return envelope(
        {
            "file_id": file_id,
            "filename": filename,
            "project_id": project_id,
            "atom_count": metadata["atom_count"],
            "chain_count": metadata["chain_count"],
            "chains": metadata["chains"],
            "residue_count": metadata.get("residue_count"),
            "preview_url": f"/artifacts/uploads/{stored_name}",
            "target": target,
        }
    )


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
    path = UPLOADS_ROOT / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="upload_not_found")
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

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
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

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{project_id}_delivery.zip"'},
    )
