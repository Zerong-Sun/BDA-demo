from __future__ import annotations

from celery import Celery

from .settings import get_settings

settings = get_settings()

celery_app = Celery(
    "bda",
    broker=settings.celery_broker_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(name="bda.poll_job_status")
def poll_job_status(job_id: str) -> dict:
    from .db import connect
    from .compute.factory import get_compute_adapter
    from .services import job_service

    connection = connect()
    try:
        job = job_service.get_job(connection, job_id)
        if not job:
            return {"job_id": job_id, "status": "not_found"}
        adapter = get_compute_adapter()
        live = adapter.status(job_id, job.get("external_id"))
        if live.status != job.get("status"):
            job_service.update_job_status(
                connection,
                job_id,
                status=live.status,
                logs=live.logs,
                output_artifacts=live.output_artifacts or None,
                error_message=live.error_message,
            )
        return {"job_id": job_id, "status": live.status}
    finally:
        connection.close()


@celery_app.task(name="bda.submit_node_job")
def submit_node_job_task(node_run_id: str, compute_node_id: str | None = None) -> dict:
    from .db import connect
    from .services import job_service

    connection = connect()
    try:
        job = job_service.submit_node_job(connection, node_run_id, compute_node_id)
        poll_job_status.delay(job["job_id"])
        return job
    finally:
        connection.close()
