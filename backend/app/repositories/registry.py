import sqlite3

from .base import get_by_id, list_table


def list_servers(connection: sqlite3.Connection) -> list[dict]:
    return list_table(connection, "server_connections", "server_name")


def get_server(connection: sqlite3.Connection, server_id: str) -> dict | None:
    return get_by_id(connection, "server_connections", "server_id", server_id)


def list_compute_nodes(connection: sqlite3.Connection) -> list[dict]:
    return list_table(connection, "compute_nodes", "node_name")


def get_compute_node(connection: sqlite3.Connection, compute_node_id: str) -> dict | None:
    return get_by_id(connection, "compute_nodes", "compute_node_id", compute_node_id)


def list_model_plugins(connection: sqlite3.Connection) -> list[dict]:
    return list_table(connection, "model_plugins", "model_name")


def get_model_plugin(connection: sqlite3.Connection, model_plugin_id: str) -> dict | None:
    return get_by_id(connection, "model_plugins", "model_plugin_id", model_plugin_id)


def list_method_plugins(connection: sqlite3.Connection) -> list[dict]:
    return list_table(connection, "method_plugins", "method_name")


def get_method_plugin(connection: sqlite3.Connection, method_plugin_id: str) -> dict | None:
    return get_by_id(connection, "method_plugins", "method_plugin_id", method_plugin_id)

