from __future__ import annotations

import sqlite3
from typing import Any

from ..repositories import literature_subscriptions
from .literature_ingestion import ingest_europe_pmc_query


def run_subscription(connection: sqlite3.Connection, item: dict[str, Any]) -> dict[str, Any]:
    savepoint = f"literature_subscription_{item['subscription_id'].replace('-', '_')}"
    connection.execute(f"SAVEPOINT {savepoint}")
    try:
        result = ingest_europe_pmc_query(
            connection,
            item["query"],
            limit=int(item["result_limit"]),
            fetch_full_text=bool(item["fetch_full_text"]),
            extract_claims=bool(item["extract_claims"]),
        )
        status = "completed"
        connection.execute(f"RELEASE SAVEPOINT {savepoint}")
    except Exception as exc:
        connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        connection.execute(f"RELEASE SAVEPOINT {savepoint}")
        result = {"error": str(exc)[:500]}
        status = "failed"
    literature_subscriptions.record_run(
        connection,
        item["subscription_id"],
        status=status,
        result=result,
    )
    return {
        "subscription_id": item["subscription_id"],
        "status": status,
        "result": result,
    }


def run_due_subscriptions(connection: sqlite3.Connection) -> dict[str, Any]:
    items = literature_subscriptions.due_subscriptions(connection)
    results = []
    for item in items:
        claimed = literature_subscriptions.claim_due_subscription(
            connection,
            item["subscription_id"],
        )
        if claimed is not None:
            results.append(run_subscription(connection, claimed))
    return {"subscriptions_run": len(results), "results": results}
