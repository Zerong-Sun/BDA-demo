from __future__ import annotations

from celery import Celery

from .logging_config import get_logger
from .settings import get_settings

settings = get_settings()
logger = get_logger(__name__)

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
    # Reliability: redeliver on worker loss, retry transient failures with backoff,
    # and cap runaway tasks so a stuck container cannot block a worker forever.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=5,
    task_time_limit=60 * 30,
    task_soft_time_limit=60 * 25,
)

# Tasks autoretry on any unexpected error with exponential backoff and jitter.
_RETRY_KWARGS = {
    "autoretry_for": (Exception,),
    "max_retries": 3,
    "retry_backoff": True,
    "retry_backoff_max": 60,
    "retry_jitter": True,
}


@celery_app.task(name="bda.poll_job_status", bind=True, **_RETRY_KWARGS)
def poll_job_status(self, job_id: str) -> dict:
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
            updated = job_service.update_job_status(
                connection,
                job_id,
                status=live.status,
                logs=live.logs,
                output_artifacts=live.output_artifacts or None,
                error_message=live.error_message,
            )
            node_run_id = (updated or job).get("node_run_id")
            if node_run_id and live.status in ("completed", "failed", "cancelled"):
                from .repositories import catalog

                node_status = "completed" if live.status == "completed" else "failed"
                catalog.update_workflow_node(connection, node_run_id, status=node_status)
        if live.status in ("queued", "running"):
            poll_job_status.apply_async(args=[job_id], countdown=5)
        return {"job_id": job_id, "status": live.status}
    except Exception as exc:  # noqa: BLE001 - logged, then re-raised for autoretry
        logger.error("poll_job_status_failed", job_id=job_id, error=str(exc))
        raise
    finally:
        connection.close()


@celery_app.task(name="bda.submit_node_job", bind=True, **_RETRY_KWARGS)
def submit_node_job_task(self, node_run_id: str, compute_node_id: str | None = None) -> dict:
    from .db import connect
    from .repositories import catalog
    from .services import job_service

    connection = connect()
    try:
        job = job_service.submit_node_job(connection, node_run_id, compute_node_id)
        poll_job_status.delay(job["job_id"])
        return job
    except Exception as exc:  # noqa: BLE001
        # Once retries are exhausted, leave the node in a consistent 'failed'
        # state so the workflow does not appear permanently stuck in 'queued'.
        logger.error("submit_node_job_failed", node_run_id=node_run_id, error=str(exc))
        if self.request.retries >= self.max_retries:
            try:
                catalog.update_workflow_node(connection, node_run_id, status="failed")
            except Exception:  # noqa: BLE001
                logger.error("submit_node_job_cleanup_failed", node_run_id=node_run_id)
        raise
    finally:
        connection.close()
