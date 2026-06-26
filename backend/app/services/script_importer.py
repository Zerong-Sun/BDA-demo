from __future__ import annotations

import ast
import hashlib
import json
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from ..repositories import model_catalog, registry

SUPPORTED_SUFFIXES = {".lsf", ".sh", ".py", ".xml"}
MODEL_PATH_HINTS = {
    "af3": "plugin_alphafold3",
    "af2": "plugin_alphafold2",
    "rfd": "plugin_rfdiffusion",
    "mpnn": "plugin_proteinmpnn",
    "ros": "plugin_rosetta",
    "boltz": "plugin_boltz",
    "chai1": "plugin_chai1",
    "chai": "plugin_chai1",
    "bindcraft": "plugin_bindcraft",
    "maskrgn": "plugin_maskrgn",
}
CATALOG_MODEL_PLUGINS = {
    "rfdiffusion": "plugin_rfdiffusion",
    "proteinmpnn": "plugin_proteinmpnn",
    "alphafold2": "plugin_alphafold2",
    "alphafold3": "plugin_alphafold3",
    "rosetta": "plugin_rosetta",
    "boltz": "plugin_boltz",
    "chai1": "plugin_chai1",
    "bindcraft": "plugin_bindcraft",
    "maskrgn": "plugin_maskrgn",
}
CLI_PATTERN = re.compile(r"--([A-Za-z0-9_:-]+)(?:=|\s+)(\"[^\"]*\"|'[^']*'|[^\s\\]+)")
HYDRA_PATTERN = re.compile(r"(?<![-\w])([A-Za-z][A-Za-z0-9_]*\.[A-Za-z0-9_.]+)=(\"[^\"]*\"|'[^']*'|[^\s\\]+)")
ASSIGNMENT_PATTERN = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]+)=(.*)$")
BSUB_PATTERN = re.compile(r"^\s*#BSUB\s+(-\w+)\s*(.*)$")


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def _json_value(raw: str | None) -> Any:
    if raw is None:
        return None
    value = raw.strip().strip("\"'")
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return value


def _model_for_path(relative_path: str) -> str | None:
    parts = {part.lower() for part in Path(relative_path).parts}
    for hint, plugin_id in MODEL_PATH_HINTS.items():
        if hint in parts:
            return plugin_id
    return None


def _parse_python_arguments(text: str) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return observations
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_argument" or not node.args:
            continue
        option = node.args[0]
        if not isinstance(option, ast.Constant) or not isinstance(option.value, str):
            continue
        key = option.value.lstrip("-").replace("-", "_")
        default = None
        for keyword in node.keywords:
            if keyword.arg == "default":
                try:
                    default = ast.literal_eval(keyword.value)
                except (ValueError, TypeError):
                    default = None
        observations.append({
            "parameter_key": key,
            "raw_value": None if default is None else str(default),
            "normalized_value": default,
            "source_line": node.lineno,
            "source_kind": "argparse_definition",
        })
    return observations


def parse_script(path: Path, relative_path: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    resources: dict[str, Any] = {}
    environment: dict[str, Any] = {}
    observations: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen: set[tuple[str, int, str]] = set()

    def add(key: str, raw: str | None, line_number: int, kind: str) -> None:
        identity = (key, line_number, kind)
        if identity in seen:
            return
        seen.add(identity)
        observations.append({
            "parameter_key": key,
            "raw_value": raw,
            "normalized_value": _json_value(raw),
            "source_line": line_number,
            "source_kind": kind,
        })

    for line_number, line in enumerate(text.splitlines(), start=1):
        bsub = BSUB_PATTERN.match(line)
        if bsub:
            key, raw = bsub.groups()
            resources[key.lstrip("-")] = raw.strip().strip("\"")
            add(f"lsf.{key.lstrip('-')}", raw.strip(), line_number, "lsf_directive")

        assignment = ASSIGNMENT_PATTERN.match(line)
        if assignment:
            key, raw = assignment.groups()
            environment[key] = _json_value(raw)

        for match in CLI_PATTERN.finditer(line):
            add(match.group(1).replace("-", "_"), match.group(2), line_number, "cli_argument")
        for match in HYDRA_PATTERN.finditer(line):
            key = match.group(1)
            if key.startswith("BSUB"):
                continue
            add(key, match.group(2), line_number, "hydra_override")

    if path.suffix == ".py":
        observations.extend(_parse_python_arguments(text))
    if text.rstrip().endswith("\\"):
        warnings.append("file_ends_with_line_continuation")
    if re.search(r"/work/[A-Za-z0-9_-]+/", text):
        warnings.append("contains_hard_coded_cluster_path")
    if "fixed_positions" in text and not re.search(r"^\s*fixed_positions=", text, re.MULTILINE):
        warnings.append("references_undefined_fixed_positions")

    return {
        "content": text,
        "content_hash": hashlib.sha256(text.encode()).hexdigest(),
        "language": {
            ".py": "python",
            ".xml": "xml",
            ".sh": "shell",
            ".lsf": "shell",
        }.get(path.suffix, "text"),
        "scheduler": "lsf" if "#BSUB" in text else None,
        "resource_config": resources,
        "environment": environment,
        "observations": observations,
        "warnings": sorted(set(warnings)),
    }


def import_parameter_catalog(
    connection: sqlite3.Connection,
    catalog_path: Path,
) -> int:
    if not catalog_path.exists():
        return 0
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    imported = 0
    for model_name, model in (payload.get("models") or {}).items():
        plugin_id = CATALOG_MODEL_PLUGINS.get(model_name)
        if not plugin_id:
            continue
        upstream = {
            "repo": model.get("repo"),
            "commit": model.get("commit"),
            "entrypoint": model.get("entrypoint"),
            "group": None,
            "required": False,
        }
        for item in model.get("parameters") or []:
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            constraints = {
                **upstream,
                "group": item.get("group"),
                "required": bool(item.get("required")),
                "boolean_style": item.get("boolean_style"),
            }
            connection.execute(
                """
                INSERT INTO model_parameter_catalog (
                    parameter_catalog_id, model_plugin_id, parameter_key, label,
                    parameter_type, default_value_json, constraints_json,
                    description, advanced, provenance, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'upstream_catalog', 'active')
                ON CONFLICT(model_plugin_id, parameter_key) DO UPDATE SET
                    parameter_type=excluded.parameter_type,
                    default_value_json=excluded.default_value_json,
                    constraints_json=excluded.constraints_json,
                    description=COALESCE(excluded.description, model_parameter_catalog.description),
                    provenance='upstream_catalog',
                    status='active',
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    f"param_{plugin_id}_{key}".replace(".", "_").replace(":", "_"),
                    plugin_id,
                    key,
                    item.get("label") or key,
                    item.get("type") or "string",
                    json.dumps(item.get("default")),
                    json.dumps(constraints),
                    item.get("help") or None,
                    int(bool(item.get("advanced"))),
                ),
            )
            imported += 1
    return imported


def import_script_tree(
    connection: sqlite3.Connection,
    root: Path,
    *,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    repository_root = (repository_root or root.parent).resolve()
    plugins = registry.list_model_plugins(connection)
    model_catalog.sync_plugin_parameters(connection, plugins)
    catalog_parameter_count = import_parameter_catalog(
        connection, root / "library" / "catalog.json"
    )
    imported = 0
    observation_count = 0
    warning_count = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        relative_path = path.relative_to(repository_root).as_posix()
        parsed = parse_script(path, relative_path)
        source_id = _stable_id("source", relative_path)
        asset_id = _stable_id("script", relative_path)
        plugin_id = _model_for_path(relative_path)
        connection.execute(
            """
            INSERT INTO research_sources (
                source_id, source_type, title, uri, content_hash,
                metadata_json, status, last_ingested_at
            ) VALUES (?, 'local_script', ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
            ON CONFLICT(source_type, uri) DO UPDATE SET
                title=excluded.title,
                content_hash=excluded.content_hash,
                metadata_json=excluded.metadata_json,
                status='active',
                last_ingested_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                source_id,
                path.name,
                relative_path,
                parsed["content_hash"],
                json.dumps({"absolute_root": str(repository_root)}),
            ),
        )
        source_row = connection.execute(
            "SELECT source_id FROM research_sources WHERE source_type='local_script' AND uri=?",
            (relative_path,),
        ).fetchone()
        source_id = source_row["source_id"]
        connection.execute(
            """
            INSERT INTO script_assets (
                script_asset_id, source_id, model_plugin_id, relative_path,
                language, scheduler, content_hash, resource_config_json,
                environment_json, parse_warnings_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            ON CONFLICT(relative_path) DO UPDATE SET
                source_id=excluded.source_id,
                model_plugin_id=excluded.model_plugin_id,
                language=excluded.language,
                scheduler=excluded.scheduler,
                content_hash=excluded.content_hash,
                resource_config_json=excluded.resource_config_json,
                environment_json=excluded.environment_json,
                parse_warnings_json=excluded.parse_warnings_json,
                status='active',
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                asset_id,
                source_id,
                plugin_id,
                relative_path,
                parsed["language"],
                parsed["scheduler"],
                parsed["content_hash"],
                json.dumps(parsed["resource_config"]),
                json.dumps(parsed["environment"]),
                json.dumps(parsed["warnings"]),
            ),
        )
        asset_row = connection.execute(
            "SELECT script_asset_id FROM script_assets WHERE relative_path=?",
            (relative_path,),
        ).fetchone()
        asset_id = asset_row["script_asset_id"]
        connection.execute(
            "DELETE FROM script_parameter_observations WHERE script_asset_id=?",
            (asset_id,),
        )
        for observation in parsed["observations"]:
            connection.execute(
                """
                INSERT INTO script_parameter_observations (
                    observation_id, script_asset_id, model_plugin_id,
                    parameter_key, raw_value, normalized_value_json,
                    source_line, source_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"obs_{uuid.uuid4().hex[:16]}",
                    asset_id,
                    plugin_id,
                    observation["parameter_key"],
                    observation["raw_value"],
                    json.dumps(observation["normalized_value"]),
                    observation["source_line"],
                    observation["source_kind"],
                ),
            )
            observation_count += 1
        imported += 1
        warning_count += len(parsed["warnings"])

    return {
        "root": str(root),
        "scripts_imported": imported,
        "parameter_observations": observation_count,
        "parse_warnings": warning_count,
        "catalog_parameters": catalog_parameter_count,
    }


def consistency_report(
    connection: sqlite3.Connection,
    *,
    model_plugin_id: str | None = None,
) -> dict[str, Any]:
    catalog_items = model_catalog.list_parameters(
        connection, model_plugin_id=model_plugin_id
    )
    observations = model_catalog.list_observations(
        connection, model_plugin_id=model_plugin_id
    )
    catalog_by_model: dict[str, set[str]] = {}
    observed_by_model: dict[str, set[str]] = {}
    for item in catalog_items:
        catalog_by_model.setdefault(item["model_plugin_id"], set()).add(item["parameter_key"])
    for item in observations:
        plugin_id = item.get("model_plugin_id")
        if plugin_id and not item["parameter_key"].startswith("lsf."):
            observed_by_model.setdefault(plugin_id, set()).add(item["parameter_key"])

    plugin_ids = sorted(set(catalog_by_model) | set(observed_by_model))
    models = []
    for plugin_id in plugin_ids:
        canonical = catalog_by_model.get(plugin_id, set())
        observed = observed_by_model.get(plugin_id, set())
        models.append({
            "model_plugin_id": plugin_id,
            "matched": sorted(canonical & observed),
            "script_only": sorted(observed - canonical),
            "catalog_only": sorted(canonical - observed),
        })
    return {"models": models}
