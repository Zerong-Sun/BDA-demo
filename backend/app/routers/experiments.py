import csv
import io
import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..db import get_connection
from ..repositories import catalog
from ..settings import get_settings
from ..utils.response import envelope

router = APIRouter()

INSERT_RESULT_SQL = """
INSERT OR REPLACE INTO experiment_results
(result_id, experiment_batch_id, candidate_id, experiment_type, pass_status, value, unit, conclusion, failure_reason)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _parse_result_rows(filename: str, raw: bytes) -> list[dict]:
    """Normalize a CSV or JSON upload into a uniform list of row dicts."""
    if filename.endswith(".json"):
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid_json") from exc
        rows = payload if isinstance(payload, list) else payload.get("results", [])
        return [row for row in rows if isinstance(row, dict)]
    if filename.endswith(".csv"):
        text = raw.decode("utf-8", errors="replace")
        return list(csv.DictReader(io.StringIO(text)))
    raise HTTPException(status_code=400, detail="unsupported_upload_format")


@router.post("/experiment-results/upload")
async def upload_experiment_results(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    connection=Depends(get_connection),
):
    raw = await file.read()
    max_bytes = get_settings().bda_max_upload_bytes
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail=f"file_too_large_max_{max_bytes}_bytes")

    filename = (file.filename or "").lower()
    batch_id = f"batch_upload_{uuid.uuid4().hex[:8]}"
    imported = 0

    rows = _parse_result_rows(filename, raw)
    try:
        for row in rows:
            candidate_id = row.get("candidate_id")
            if not candidate_id:
                continue
            if not catalog.candidate_belongs_to_project(connection, candidate_id, project_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"candidate_not_in_project:{candidate_id}",
                )
            connection.execute(
                INSERT_RESULT_SQL,
                (
                    row.get("result_id") or f"result_upload_{uuid.uuid4().hex[:8]}",
                    row.get("experiment_batch_id") or batch_id,
                    candidate_id,
                    row.get("experiment_type", "unknown"),
                    row.get("pass_status", "unknown"),
                    row.get("value"),
                    row.get("unit"),
                    row.get("conclusion"),
                    row.get("failure_reason"),
                ),
            )
            imported += 1
        connection.commit()
    except Exception:
        # Keep the import atomic: a bad row must not leave a half-written batch.
        connection.rollback()
        raise

    catalog.get_project_results_summary(connection, project_id)
    return envelope({"imported": imported, "batch_id": batch_id, "project_id": project_id})
