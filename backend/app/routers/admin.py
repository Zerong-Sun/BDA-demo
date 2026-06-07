from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from ..auth.service import require_role
from ..db import get_connection
from ..settings import get_settings
from ..utils.response import envelope

router = APIRouter(prefix="/admin")


@router.get("/metrics")
def admin_metrics(
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    job_counts = {}
    try:
        rows = connection.execute(
            "SELECT status, COUNT(*) AS cnt FROM jobs GROUP BY status"
        ).fetchall()
        job_counts = {row["status"]: row["cnt"] for row in rows}
    except sqlite3.OperationalError:
        job_counts = {}

    return envelope({
        "jobs": job_counts,
        "compute_mode": get_settings().bda_compute_mode,
        "artifacts_backend": get_settings().bda_artifacts_backend,
    })


@router.get("/audit-logs")
def audit_logs(
    project_id: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    from ..repositories.base import decode_rows

    if project_id:
        rows = connection.execute(
            "SELECT * FROM audit_logs WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
            (project_id, limit),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return envelope(decode_rows(rows))


@router.get("/health-detail")
def health_detail(
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    settings = get_settings()
    checks = {"api": "ok", "database": "unknown", "redis": "unknown", "minio": "unknown"}

    try:
        connection.execute("SELECT 1").fetchone()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error:{exc}"

    try:
        import redis

        r = redis.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"unavailable:{exc}"

    if settings.bda_artifacts_backend == "minio":
        try:
            from minio import Minio

            client = Minio(
                settings.bda_minio_endpoint,
                access_key=settings.bda_minio_access_key,
                secret_key=settings.bda_minio_secret_key,
                secure=settings.bda_minio_secure,
            )
            client.bucket_exists(settings.bda_minio_bucket)
            checks["minio"] = "ok"
        except Exception as exc:
            checks["minio"] = f"error:{exc}"
    else:
        checks["minio"] = "local_mode"

    checks["compute"] = settings.bda_compute_mode
    checks["timestamp"] = datetime.now(timezone.utc).isoformat()
    return envelope(checks)
