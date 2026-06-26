from __future__ import annotations

import json
import operator
import sqlite3
import uuid
from copy import deepcopy
from statistics import mean
from typing import Any

from ..repositories import campaigns, catalog, registry
from ..repositories.base import decode_rows

OPERATORS = {
    ">=": operator.ge,
    ">": operator.gt,
    "<=": operator.le,
    "<": operator.lt,
    "==": operator.eq,
}


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _flatten_numeric(value: Any, prefix: str = "") -> dict[str, float]:
    result: dict[str, float] = {}
    if isinstance(value, dict):
        for key, nested in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            result.update(_flatten_numeric(nested, path))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        result[prefix] = float(value)
    return result


def _aggregate_workflow_metrics(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> dict[str, Any]:
    nodes = catalog.list_workflow_nodes(connection, workflow_run_id)
    jobs = decode_rows(connection.execute(
        "SELECT * FROM jobs WHERE workflow_run_id = ?",
        (workflow_run_id,),
    ).fetchall())
    candidates = decode_rows(connection.execute(
        "SELECT * FROM candidates WHERE workflow_run_id = ?",
        (workflow_run_id,),
    ).fetchall())
    metrics: dict[str, Any] = {
        "workflow.node_count": len(nodes),
        "workflow.completed_nodes": sum(node.get("status") == "completed" for node in nodes),
        "workflow.failed_nodes": sum(node.get("status") == "failed" for node in nodes),
        "jobs.total": len(jobs),
        "jobs.completed": sum(job.get("status") == "completed" for job in jobs),
        "jobs.failed": sum(job.get("status") == "failed" for job in jobs),
        "candidates.count": len(candidates),
    }
    experiment_rows = decode_rows(connection.execute(
        """
        SELECT er.* FROM experiment_results er
        JOIN candidates c ON c.candidate_id = er.candidate_id
        WHERE c.workflow_run_id = ?
        """,
        (workflow_run_id,),
    ).fetchall())
    metrics["experiments.total"] = len(experiment_rows)
    experiment_types = sorted({
        str(item.get("experiment_type") or "").strip()
        for item in experiment_rows
        if item.get("experiment_type")
    })
    for experiment_type in experiment_types:
        items = [
            item for item in experiment_rows
            if str(item.get("experiment_type") or "") == experiment_type
        ]
        passed = sum(item.get("pass_status") == "pass" for item in items)
        key = experiment_type.lower().replace(" ", "_")
        metrics[f"experiments.{key}.total"] = len(items)
        metrics[f"experiments.{key}.passed"] = passed
        metrics[f"experiments.{key}.pass_rate"] = passed / len(items) if items else 0.0
    for node in nodes:
        model_key = str(node.get("model_name") or node.get("node_type") or "node").replace(" ", "_")
        for key, value in _flatten_numeric(node.get("metrics_json") or {}).items():
            metrics[f"node.{model_key}.{key}"] = value
    for field in (
        "plddt", "interface_pae", "rosetta_score", "interface_energy",
        "clash_count", "buried_sasa", "solubility_score",
    ):
        values = [float(item[field]) for item in candidates if item.get(field) is not None]
        if values:
            metrics[f"candidates.{field}.mean"] = mean(values)
            metrics[f"candidates.{field}.min"] = min(values)
            metrics[f"candidates.{field}.max"] = max(values)
    return metrics


def _criteria_results(
    metrics: dict[str, Any],
    conditions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []
    for condition in conditions:
        metric = str(condition.get("metric") or "")
        op_name = str(condition.get("operator") or ">=")
        target = condition.get("value")
        actual = metrics.get(metric)
        passed = False
        if op_name in OPERATORS and isinstance(actual, (int, float)) and isinstance(target, (int, float)):
            passed = bool(OPERATORS[op_name](actual, target))
        results.append({
            "metric": metric,
            "operator": op_name,
            "target": target,
            "actual": actual,
            "passed": passed,
            "required": bool(condition.get("required", True)),
        })
    return results


def _parameter_patch(
    connection: sqlite3.Connection,
    metrics: dict[str, Any],
    strategy: dict[str, Any],
) -> dict[str, Any]:
    patch: dict[str, dict[str, Any]] = {}
    allowed_by_model = {
        plugin["model_name"]: {
            str(field.get("key"))
            for field in (plugin.get("parameter_schema_json") or {}).get("fields", [])
            if field.get("key")
        }
        for plugin in registry.list_model_plugins(connection)
    }
    for rule in strategy.get("parameter_rules") or []:
        metric = str(rule.get("metric") or "")
        op_name = str(rule.get("operator") or "<")
        threshold = rule.get("value")
        actual = metrics.get(metric)
        if (
            op_name not in OPERATORS
            or not isinstance(actual, (int, float))
            or not isinstance(threshold, (int, float))
            or not OPERATORS[op_name](actual, threshold)
        ):
            continue
        model_name = str(rule.get("model_name") or "").strip()
        parameter = str(rule.get("parameter") or "").strip()
        if (
            not model_name
            or not parameter
            or parameter not in allowed_by_model.get(model_name, set())
        ):
            continue
        patch.setdefault(model_name, {})[parameter] = rule.get("set")
    return {"models": patch}


def create_campaign(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    name: str,
    objective: str,
    initial_workflow_run_id: str | None,
    max_rounds: int,
    budget: dict[str, Any],
    stop_conditions: list[dict[str, Any]],
    strategy: dict[str, Any],
    created_by: str,
) -> dict:
    workflow = (
        catalog.get_workflow_run(connection, initial_workflow_run_id)
        if initial_workflow_run_id
        else catalog.get_latest_project_workflow_run(connection, project_id)
    )
    if workflow is not None and initial_workflow_run_id is None:
        claimed = connection.execute(
            "SELECT 1 FROM campaign_rounds WHERE workflow_run_id = ? LIMIT 1",
            (workflow["workflow_run_id"],),
        ).fetchone()
        if claimed:
            workflow = clone_workflow_with_patch(
                connection,
                workflow["workflow_run_id"],
                {"models": {}},
            )
    if workflow is None:
        workflow = catalog.create_draft_workflow_run(connection, project_id)
    if catalog.get_workflow_run_project_id(connection, workflow["workflow_run_id"]) != project_id:
        raise ValueError("workflow_project_mismatch")
    claimed = connection.execute(
        "SELECT campaign_id FROM campaign_rounds WHERE workflow_run_id = ? LIMIT 1",
        (workflow["workflow_run_id"],),
    ).fetchone()
    if claimed:
        raise ValueError("workflow_already_in_campaign")
    campaign_id = _id("campaign")
    campaigns.create_campaign(
        connection,
        campaign_id=campaign_id,
        project_id=project_id,
        name=name,
        objective=objective,
        max_rounds=max_rounds,
        budget=budget,
        stop_conditions=stop_conditions,
        strategy=strategy,
        created_by=created_by,
    )
    connection.execute(
        """
        INSERT INTO campaign_rounds (
            campaign_round_id, campaign_id, round_number, workflow_run_id,
            status, approval_status
        ) VALUES (?, ?, 1, ?, 'active', 'not_required')
        """,
        (_id("round"), campaign_id, workflow["workflow_run_id"]),
    )
    return campaigns.get_campaign_detail(connection, campaign_id) or {}


def evaluate_round(
    connection: sqlite3.Connection,
    campaign_id: str,
    round_number: int,
) -> dict[str, Any]:
    campaign = campaigns.get_campaign(connection, campaign_id)
    round_item = campaigns.get_round_by_number(connection, campaign_id, round_number)
    if campaign is None or round_item is None:
        raise ValueError("campaign_round_not_found")
    existing = connection.execute(
        "SELECT 1 FROM campaign_evaluations WHERE campaign_round_id = ? LIMIT 1",
        (round_item["campaign_round_id"],),
    ).fetchone()
    if existing:
        raise ValueError("campaign_round_already_evaluated")
    active_jobs = connection.execute(
        """
        SELECT COUNT(*) AS total FROM jobs
        WHERE workflow_run_id = ? AND status IN ('queued', 'staging', 'running')
        """,
        (round_item["workflow_run_id"],),
    ).fetchone()["total"]
    if active_jobs:
        raise ValueError("campaign_round_has_active_jobs")
    workflow = catalog.get_workflow_run(connection, round_item["workflow_run_id"])
    nodes = catalog.list_workflow_nodes(connection, round_item["workflow_run_id"])
    terminal = {"completed", "failed", "cancelled"}
    if (
        workflow is None
        or not nodes
        or (
            workflow.get("status") != "completed"
            and any(node.get("status") not in terminal for node in nodes)
        )
    ):
        raise ValueError("campaign_round_not_terminal")
    metrics = _aggregate_workflow_metrics(connection, round_item["workflow_run_id"])
    rounds = campaigns.list_rounds(connection, campaign_id)
    workflow_ids = [item["workflow_run_id"] for item in rounds]
    placeholders = ",".join("?" for _ in workflow_ids)
    cumulative_jobs = connection.execute(
        f"SELECT COUNT(*) AS total FROM jobs WHERE workflow_run_id IN ({placeholders})",
        workflow_ids,
    ).fetchone()["total"] if workflow_ids else 0
    cumulative_candidates = connection.execute(
        f"SELECT COUNT(*) AS total FROM candidates WHERE workflow_run_id IN ({placeholders})",
        workflow_ids,
    ).fetchone()["total"] if workflow_ids else 0
    metrics["campaign.rounds_used"] = round_number
    metrics["campaign.jobs_used"] = int(cumulative_jobs)
    metrics["campaign.candidates_generated"] = int(cumulative_candidates)
    criteria = _criteria_results(metrics, campaign.get("stop_conditions_json") or [])
    required = [item for item in criteria if item["required"]]
    goals_met = bool(required) and all(item["passed"] for item in required)
    max_rounds_reached = round_number >= int(campaign["max_rounds"])
    budget = campaign.get("budget_json") or {}
    max_jobs = budget.get("max_jobs")
    max_candidates = budget.get("max_candidates")
    budget_reached = (
        isinstance(max_jobs, int) and cumulative_jobs >= max_jobs
    ) or (
        isinstance(max_candidates, int) and cumulative_candidates >= max_candidates
    )
    failed = metrics["workflow.failed_nodes"] > 0 or metrics["jobs.failed"] > 0
    if goals_met:
        recommendation = "stop_success"
        rationale = "All required stop conditions are satisfied."
    elif max_rounds_reached or budget_reached:
        recommendation = "stop_budget"
        rationale = "A configured round or workload budget has been reached."
    elif failed:
        recommendation = "retry"
        rationale = "One or more workflow nodes or jobs failed."
    else:
        recommendation = "continue"
        rationale = "Required success conditions are not yet satisfied."
    patch = _parameter_patch(connection, metrics, campaign.get("strategy_json") or {})
    if recommendation in {"continue", "retry"}:
        validate_parameter_patch(connection, patch)
    evaluation_id = _id("evaluation")
    try:
        connection.execute(
            """
            INSERT INTO campaign_evaluations (
                evaluation_id, campaign_round_id, metrics_json,
                criteria_results_json, recommendation, rationale
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                evaluation_id,
                round_item["campaign_round_id"],
                json.dumps(metrics),
                json.dumps(criteria),
                recommendation,
                rationale,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError("campaign_round_already_evaluated") from exc
    decision_type = "continue" if recommendation == "continue" else (
        "retry" if recommendation == "retry" else "stop"
    )
    decision_id = _id("decision")
    connection.execute(
        """
        INSERT INTO campaign_decisions (
            decision_id, campaign_round_id, decision_type,
            parameter_patch_json, rationale, status, proposed_by
        ) VALUES (?, ?, ?, ?, ?, 'proposed', 'rule_based_evaluator')
        """,
        (
            decision_id,
            round_item["campaign_round_id"],
            decision_type,
            json.dumps(patch),
            rationale,
        ),
    )
    connection.execute(
        """
        UPDATE campaign_rounds
        SET status = 'evaluated', completed_at = CURRENT_TIMESTAMP,
            approval_status = 'awaiting_approval'
        WHERE campaign_round_id = ?
        """,
        (round_item["campaign_round_id"],),
    )
    campaigns.update_campaign_status(
        connection,
        campaign_id,
        status="awaiting_approval",
    )
    return {
        "evaluation_id": evaluation_id,
        "decision_id": decision_id,
        "recommendation": recommendation,
        "metrics": metrics,
        "criteria": criteria,
        "parameter_patch": patch,
        "rationale": rationale,
    }


def _merge_parameters(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(current)
    merged.update(patch)
    return merged


def validate_parameter_patch(
    connection: sqlite3.Connection,
    parameter_patch: dict[str, Any],
) -> None:
    models = parameter_patch.get("models")
    if not isinstance(models, dict):
        raise ValueError("invalid_parameter_patch")
    plugins = {
        plugin["model_name"]: {
            str(field.get("key")): field
            for field in (plugin.get("parameter_schema_json") or {}).get("fields", [])
            if field.get("key")
        }
        for plugin in registry.list_model_plugins(connection)
    }
    for model_name, values in models.items():
        if model_name not in plugins or not isinstance(values, dict):
            raise ValueError(f"invalid_patch_model:{model_name}")
        unknown = sorted(set(values) - set(plugins[model_name]))
        if unknown:
            raise ValueError(f"invalid_patch_parameters:{model_name}:{','.join(unknown)}")
        for key, value in values.items():
            field = plugins[model_name][key]
            field_type = field.get("type")
            valid_type = (
                (field_type == "integer" and isinstance(value, int) and not isinstance(value, bool))
                or (field_type == "number" and isinstance(value, (int, float)) and not isinstance(value, bool))
                or (field_type == "boolean" and isinstance(value, bool))
                or (field_type in {"string", "artifact_ref", "enum"} and isinstance(value, str))
                or (field_type == "json")
            )
            if not valid_type:
                raise ValueError(f"invalid_patch_value_type:{model_name}:{key}")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if field.get("min") is not None and value < field["min"]:
                    raise ValueError(f"invalid_patch_value_range:{model_name}:{key}")
                if field.get("max") is not None and value > field["max"]:
                    raise ValueError(f"invalid_patch_value_range:{model_name}:{key}")
            if field_type == "enum" and value not in (field.get("options") or []):
                raise ValueError(f"invalid_patch_value_option:{model_name}:{key}")


def clone_workflow_with_patch(
    connection: sqlite3.Connection,
    workflow_run_id: str,
    parameter_patch: dict[str, Any],
) -> dict[str, Any]:
    source = catalog.get_workflow_run(connection, workflow_run_id)
    if source is None:
        raise ValueError("workflow_run_not_found")
    project_id = catalog.get_workflow_run_project_id(connection, workflow_run_id)
    if project_id is None:
        raise ValueError("workflow_project_not_found")
    validate_parameter_patch(connection, parameter_patch)
    new_run = catalog.create_draft_workflow_run(connection, project_id)
    node_map: dict[str, str] = {}
    patches = parameter_patch.get("models") or {}
    for node in catalog.list_workflow_nodes(connection, workflow_run_id):
        model_patch = patches.get(node.get("model_name")) or {}
        new_node = catalog.add_workflow_node(
            connection,
            new_run["workflow_run_id"],
            node_type=node["node_type"],
            node_name=node["node_name"],
            model_name=node.get("model_name"),
            model_version=node.get("model_version"),
            parameters_json=json.dumps(_merge_parameters(node.get("parameters_json") or {}, model_patch)),
            position_json=json.dumps(node.get("position_json") or {"x": 0, "y": 0}),
        )
        connection.execute(
            "UPDATE workflow_node_runs SET input_files_json = ? WHERE node_run_id = ?",
            (json.dumps(node.get("input_files_json") or []), new_node["node_run_id"]),
        )
        node_map[node["node_run_id"]] = new_node["node_run_id"]
    edges = []
    for edge in catalog.list_workflow_edges(connection, workflow_run_id):
        edges.append({
            "source_node_run_id": node_map[edge["source_node_run_id"]],
            "source_port": edge.get("source_port"),
            "target_node_run_id": node_map[edge["target_node_run_id"]],
            "target_port": edge.get("target_port"),
            "edge_type": edge.get("edge_type"),
            "metadata_json": edge.get("metadata_json") or {},
        })
    catalog.replace_workflow_edges(connection, new_run["workflow_run_id"], edges)
    return new_run


def review_decision(
    connection: sqlite3.Connection,
    decision_id: str,
    *,
    approve: bool,
    reviewed_by: str,
) -> dict[str, Any]:
    decision = campaigns.get_decision(connection, decision_id)
    if decision is None:
        raise ValueError("campaign_decision_not_found")
    if decision["status"] != "proposed":
        raise ValueError("campaign_decision_already_reviewed")
    round_item = campaigns.get_round(connection, decision["campaign_round_id"])
    campaign = campaigns.get_campaign(connection, round_item["campaign_id"]) if round_item else None
    if round_item is None or campaign is None:
        raise ValueError("campaign_round_not_found")
    claimed = connection.execute(
        """
        UPDATE campaign_decisions
        SET status='reviewing', reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP
        WHERE decision_id=? AND status='proposed'
        """,
        (reviewed_by, decision_id),
    )
    if claimed.rowcount != 1:
        raise ValueError("campaign_decision_already_reviewed")

    if not approve:
        connection.execute(
            """
            UPDATE campaign_decisions
            SET status = 'rejected'
            WHERE decision_id = ?
            """,
            (decision_id,),
        )
        connection.execute(
            "UPDATE campaign_rounds SET approval_status='rejected' WHERE campaign_round_id=?",
            (round_item["campaign_round_id"],),
        )
        campaigns.update_campaign_status(connection, campaign["campaign_id"], status="paused")
        return {"decision_id": decision_id, "status": "rejected"}

    if decision["decision_type"] == "stop":
        connection.execute(
            """
            UPDATE campaign_decisions
            SET status='executed'
            WHERE decision_id=?
            """,
            (decision_id,),
        )
        connection.execute(
            "UPDATE campaign_rounds SET approval_status='approved', approved_by=?, approved_at=CURRENT_TIMESTAMP WHERE campaign_round_id=?",
            (reviewed_by, round_item["campaign_round_id"]),
        )
        campaigns.update_campaign_status(connection, campaign["campaign_id"], status="completed")
        return {"decision_id": decision_id, "status": "executed", "campaign_status": "completed"}

    validate_parameter_patch(connection, decision.get("parameter_patch_json") or {})
    next_number = int(round_item["round_number"]) + 1
    if next_number > int(campaign["max_rounds"]):
        raise ValueError("campaign_max_rounds_reached")
    new_run = clone_workflow_with_patch(
        connection,
        round_item["workflow_run_id"],
        decision.get("parameter_patch_json") or {},
    )
    new_round_id = _id("round")
    connection.execute(
        """
        INSERT INTO campaign_rounds (
            campaign_round_id, campaign_id, round_number, workflow_run_id,
            parent_round_id, status, parameter_patch_json, approval_status,
            approved_by, approved_at
        ) VALUES (?, ?, ?, ?, ?, 'draft', ?, 'approved', ?, CURRENT_TIMESTAMP)
        """,
        (
            new_round_id,
            campaign["campaign_id"],
            next_number,
            new_run["workflow_run_id"],
            round_item["campaign_round_id"],
            json.dumps(decision.get("parameter_patch_json") or {}),
            reviewed_by,
        ),
    )
    connection.execute(
        """
        UPDATE campaign_decisions
        SET status='executed', next_campaign_round_id=?
        WHERE decision_id=?
        """,
        (new_round_id, decision_id),
    )
    connection.execute(
        "UPDATE campaign_rounds SET approval_status='approved', approved_by=?, approved_at=CURRENT_TIMESTAMP WHERE campaign_round_id=?",
        (reviewed_by, round_item["campaign_round_id"]),
    )
    campaigns.update_campaign_status(
        connection,
        campaign["campaign_id"],
        status="active",
        current_round=next_number,
    )
    return {
        "decision_id": decision_id,
        "status": "executed",
        "next_round_number": next_number,
        "next_campaign_round_id": new_round_id,
        "workflow_run_id": new_run["workflow_run_id"],
        "compute_submitted": False,
    }


def update_proposed_decision(
    connection: sqlite3.Connection,
    decision_id: str,
    *,
    parameter_patch: dict[str, Any],
    rationale: str | None,
) -> dict[str, Any]:
    decision = campaigns.get_decision(connection, decision_id)
    if decision is None:
        raise ValueError("campaign_decision_not_found")
    if decision["status"] != "proposed":
        raise ValueError("campaign_decision_already_reviewed")
    if decision["decision_type"] != "stop":
        validate_parameter_patch(connection, parameter_patch)
    connection.execute(
        """
        UPDATE campaign_decisions
        SET parameter_patch_json = ?, rationale = COALESCE(?, rationale)
        WHERE decision_id = ?
        """,
        (json.dumps(parameter_patch), rationale, decision_id),
    )
    return campaigns.get_decision(connection, decision_id) or {}


def sync_round_status(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM campaign_rounds WHERE workflow_run_id = ?",
        (workflow_run_id,),
    ).fetchone()
    if row is None:
        return None
    round_item = dict(row)
    jobs = decode_rows(connection.execute(
        "SELECT * FROM jobs WHERE workflow_run_id = ?",
        (workflow_run_id,),
    ).fetchall())
    nodes = catalog.list_workflow_nodes(connection, workflow_run_id)
    active_jobs = any(job.get("status") in {"queued", "staging", "running"} for job in jobs)
    terminal_nodes = bool(nodes) and all(
        node.get("status") in {"completed", "failed", "cancelled"}
        for node in nodes
    )
    if active_jobs:
        status = "running"
    elif terminal_nodes:
        status = "ready_for_evaluation"
    else:
        status = "draft"
    connection.execute(
        "UPDATE campaign_rounds SET status = ? WHERE campaign_round_id = ?",
        (status, round_item["campaign_round_id"]),
    )
    if status == "ready_for_evaluation":
        failed = any(node.get("status") == "failed" for node in nodes)
        connection.execute(
            "UPDATE workflow_runs SET status = ?, end_time = CURRENT_TIMESTAMP WHERE workflow_run_id = ?",
            ("failed" if failed else "completed", workflow_run_id),
        )
    campaigns.update_campaign_status(
        connection,
        round_item["campaign_id"],
        status="active",
        current_round=int(round_item["round_number"]),
    )
    return {
        "campaign_round_id": round_item["campaign_round_id"],
        "workflow_run_id": workflow_run_id,
        "status": status,
    }
