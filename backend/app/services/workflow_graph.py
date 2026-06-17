from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


DATA_EDGE_TYPES = {"data", "control", "review_gate"}


def _ports(plugin: dict | None, schema_key: str) -> list[dict[str, Any]]:
    if not plugin:
        return []
    schema = plugin.get(schema_key) or {}
    return schema.get("ports") or []


def _port_by_name(ports: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((port for port in ports if port.get("name") == name), None)


def _node_plugin(node: dict, plugins_by_name: dict[str, dict]) -> dict | None:
    model_name = node.get("model_name")
    return plugins_by_name.get(model_name) if model_name else None


def _edge_creates_cycle(nodes: list[dict], edges: list[dict]) -> bool:
    node_ids = {node["node_run_id"] for node in nodes}
    indegree = {node_id: 0 for node_id in node_ids}
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.get("edge_type", "data") not in DATA_EDGE_TYPES:
            continue
        source = edge.get("source_node_run_id")
        target = edge.get("target_node_run_id")
        if source not in node_ids or target not in node_ids:
            continue
        graph[source].append(target)
        indegree[target] += 1

    queue = deque([node_id for node_id, count in indegree.items() if count == 0])
    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for target in graph[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return visited != len(node_ids)


def validate_workflow_graph(nodes: list[dict], edges: list[dict], plugins: list[dict]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    plugins_by_name = {plugin.get("model_name"): plugin for plugin in plugins}
    nodes_by_id = {node["node_run_id"]: node for node in nodes}
    incoming_by_node: dict[str, list[dict]] = defaultdict(list)

    for edge in edges:
        source_id = edge.get("source_node_run_id")
        target_id = edge.get("target_node_run_id")
        if source_id not in nodes_by_id:
            errors.append({"code": "missing_source_node", "edge_id": edge.get("edge_id"), "node_run_id": source_id})
            continue
        if target_id not in nodes_by_id:
            errors.append({"code": "missing_target_node", "edge_id": edge.get("edge_id"), "node_run_id": target_id})
            continue
        incoming_by_node[target_id].append(edge)

        edge_type = edge.get("edge_type", "data")
        if edge_type not in DATA_EDGE_TYPES:
            continue

        source_plugin = _node_plugin(nodes_by_id[source_id], plugins_by_name)
        target_plugin = _node_plugin(nodes_by_id[target_id], plugins_by_name)
        source_port_name = edge.get("source_port") or "output"
        target_port_name = edge.get("target_port") or "input"
        source_port = _port_by_name(_ports(source_plugin, "output_schema_json"), source_port_name)
        target_port = _port_by_name(_ports(target_plugin, "input_schema_json"), target_port_name)

        if source_port is None:
            detail = {"code": "unknown_source_port", "edge_id": edge.get("edge_id"), "port": source_port_name}
            (warnings if source_port_name == "output" else errors).append(detail)
            continue
        if target_port is None:
            detail = {"code": "unknown_target_port", "edge_id": edge.get("edge_id"), "port": target_port_name}
            (warnings if target_port_name == "input" else errors).append(detail)
            continue

        source_types = set(source_port.get("artifact_types") or [])
        target_types = set(target_port.get("artifact_types") or [])
        if source_types and target_types and not source_types.intersection(target_types):
            errors.append({
                "code": "incompatible_ports",
                "edge_id": edge.get("edge_id"),
                "source_port": source_port_name,
                "target_port": target_port_name,
                "source_artifact_types": sorted(source_types),
                "target_artifact_types": sorted(target_types),
            })

    for node in nodes:
        plugin = _node_plugin(node, plugins_by_name)
        if not plugin:
            continue
        required_ports = [
            port
            for port in _ports(plugin, "input_schema_json")
            if port.get("required", True)
        ]
        connected_ports = {
            edge.get("target_port") or "input"
            for edge in incoming_by_node.get(node["node_run_id"], [])
            if edge.get("edge_type", "data") in DATA_EDGE_TYPES
        }
        for port in required_ports:
            if port.get("name") not in connected_ports:
                warnings.append({
                    "code": "missing_required_input",
                    "node_run_id": node["node_run_id"],
                    "port": port.get("name"),
                })

    if _edge_creates_cycle(nodes, edges):
        errors.append({"code": "cycle_detected", "message": "Data/control edges must form a DAG."})

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }
