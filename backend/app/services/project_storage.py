from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import ARTIFACTS_ROOT

PROJECTS_ROOT = ARTIFACTS_ROOT / "projects"
PROJECT_SUBDIRS = ("metadata", "inputs", "workflows", "jobs", "results", "research", "exports")
MANIFEST_VERSION = 1


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def project_root(project_id: str) -> Path:
    return PROJECTS_ROOT / project_id


def project_manifest_path(project_id: str) -> Path:
    return project_root(project_id) / "metadata" / "project.json"


def relative_to_artifacts(path: Path) -> str:
    return str(path.relative_to(ARTIFACTS_ROOT))


def ensure_project_directory(project: dict[str, Any], *, source: str = "api") -> dict[str, Any]:
    root = project_root(str(project["project_id"]))
    for subdir in PROJECT_SUBDIRS:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    manifest_path = project_manifest_path(str(project["project_id"]))
    existing = read_project_manifest(str(project["project_id"])) or {}
    created_at = existing.get("created_at") or project.get("created_at") or now_iso()
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "project_id": project["project_id"],
        "project_name": project["project_name"],
        "project_type": project["project_type"],
        "status": project.get("status", "draft"),
        "owner_id": project.get("owner_id"),
        "organization_id": project.get("organization_id"),
        "summary": project.get("summary"),
        "created_at": created_at,
        "updated_at": now_iso(),
        "source": source,
        "storage": {
            "backend": "local",
            "root": relative_to_artifacts(root),
            "layout": list(PROJECT_SUBDIRS),
        },
        "sync": {
            "cloud_status": existing.get("sync", {}).get("cloud_status", "not_configured")
            if isinstance(existing.get("sync"), dict)
            else "not_configured",
            "cloud_uri": existing.get("sync", {}).get("cloud_uri")
            if isinstance(existing.get("sync"), dict)
            else None,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def read_project_manifest(project_id: str) -> dict[str, Any] | None:
    path = project_manifest_path(project_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict) or payload.get("project_id") != project_id:
        return None
    return payload


def list_project_manifests() -> list[dict[str, Any]]:
    if not PROJECTS_ROOT.exists():
        return []
    manifests: list[dict[str, Any]] = []
    for manifest_path in sorted(PROJECTS_ROOT.glob("*/metadata/project.json")):
        project_id = manifest_path.parents[1].name
        manifest = read_project_manifest(project_id)
        if manifest:
            manifests.append(manifest)
    return manifests


def storage_summary(project_id: str) -> dict[str, Any]:
    root = project_root(project_id)
    manifest = read_project_manifest(project_id)
    return {
        "backend": "local",
        "status": "available" if manifest and root.exists() else "missing",
        "root": relative_to_artifacts(root),
        "manifest": relative_to_artifacts(project_manifest_path(project_id)),
        "layout": list(PROJECT_SUBDIRS),
    }


def cloud_sync_summary(project_id: str) -> dict[str, Any]:
    manifest = read_project_manifest(project_id) or {}
    sync = manifest.get("sync") if isinstance(manifest.get("sync"), dict) else {}
    return {
        "status": sync.get("cloud_status", "not_configured"),
        "cloud_uri": sync.get("cloud_uri"),
        "last_synced_at": sync.get("last_synced_at"),
    }


def sync_project_manifest(project: dict[str, Any], *, target: str = "local") -> dict[str, Any]:
    manifest = ensure_project_directory(project, source="sync")
    if target == "local":
        manifest["sync"] = {
            **manifest.get("sync", {}),
            "local_status": "synced",
            "last_synced_at": now_iso(),
        }
        project_manifest_path(str(project["project_id"])).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {"target": "local", "status": "synced", "manifest": manifest}
    if target == "cloud":
        return {
            "target": "cloud",
            "status": "not_configured",
            "message": "Cloud project sync API boundary is reserved; configure a backend sync service before upload.",
            "manifest": manifest,
        }
    return {"target": target, "status": "unsupported_target", "manifest": manifest}
