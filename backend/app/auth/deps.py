"""FastAPI dependencies for authentication and project-level access control."""

from __future__ import annotations

import sqlite3

from fastapi import Depends, HTTPException, status

from ..db import get_connection
from ..repositories import catalog
from ..services import job_service
from .service import get_current_user, require_role, verify_project_access

__all__ = [
    "get_current_user",
    "require_role",
    "require_project_access",
    "require_workflow_run_access",
    "require_candidate_access",
    "require_job_access",
    "require_node_run_access",
]


def require_project_access(
    project_id: str,
    user: dict = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict:
    if not verify_project_access(connection, user, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return user


def require_workflow_run_access(
    workflow_run_id: str,
    user: dict = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict:
    project_id = catalog.get_workflow_run_project_id(connection, workflow_run_id)
    if project_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workflow_run_not_found")
    if not verify_project_access(connection, user, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return user


def require_candidate_access(
    candidate_id: str,
    user: dict = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict:
    candidate = catalog.get_candidate(connection, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate_not_found")
    if not verify_project_access(connection, user, candidate["project_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return user


def require_job_access(
    job_id: str,
    user: dict = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict:
    job = job_service.get_job(connection, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job_not_found")
    workflow_run_id = job.get("workflow_run_id")
    if not workflow_run_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    project_id = catalog.get_workflow_run_project_id(connection, workflow_run_id)
    if project_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workflow_run_not_found")
    if not verify_project_access(connection, user, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return user


def require_node_run_access(
    node_run_id: str,
    user: dict = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict:
    node = catalog.get_workflow_node(connection, node_run_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="node_not_found")
    return require_workflow_run_access(node["workflow_run_id"], user, connection)
