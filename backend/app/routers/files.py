import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..config import STRUCTURES_ROOT, UPLOADS_ROOT
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
