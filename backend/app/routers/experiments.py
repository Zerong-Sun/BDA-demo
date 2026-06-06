import csv
import io
import json
import uuid
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..db import get_connection
from ..repositories import catalog

router = APIRouter()


def envelope(data):
    return {"data": data, "trace_id": str(uuid4())}


@router.post("/experiment-results/upload")
async def upload_experiment_results(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    connection=Depends(get_connection),
):
    raw = await file.read()
    filename = (file.filename or "").lower()
    batch_id = f"batch_upload_{uuid.uuid4().hex[:8]}"
    imported = 0

    if filename.endswith(".json"):
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid_json") from exc
        rows = payload if isinstance(payload, list) else payload.get("results", [])
        for row in rows:
            if not isinstance(row, dict) or not row.get("candidate_id"):
                continue
            if not catalog.candidate_belongs_to_project(connection, row["candidate_id"], project_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"candidate_not_in_project:{row['candidate_id']}",
                )
            connection.execute(
                """
                INSERT OR REPLACE INTO experiment_results
                (result_id, experiment_batch_id, candidate_id, experiment_type, pass_status, value, unit, conclusion, failure_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("result_id") or f"result_upload_{uuid.uuid4().hex[:8]}",
                    row.get("experiment_batch_id") or batch_id,
                    row["candidate_id"],
                    row.get("experiment_type", "unknown"),
                    row.get("pass_status", "unknown"),
                    row.get("value"),
                    row.get("unit"),
                    row.get("conclusion"),
                    row.get("failure_reason"),
                ),
            )
            imported += 1
    elif filename.endswith(".csv"):
        text = raw.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            candidate_id = row.get("candidate_id")
            if not candidate_id:
                continue
            if not catalog.candidate_belongs_to_project(connection, candidate_id, project_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"candidate_not_in_project:{candidate_id}",
                )
            connection.execute(
                """
                INSERT OR REPLACE INTO experiment_results
                (result_id, experiment_batch_id, candidate_id, experiment_type, pass_status, value, unit, conclusion, failure_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
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
    else:
        raise HTTPException(status_code=400, detail="unsupported_upload_format")

    connection.commit()
    return envelope({"imported": imported, "batch_id": batch_id, "project_id": project_id})
