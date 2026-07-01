# ruff: noqa: E402,I001
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.repositories import knowledge
from backend.app.schemas import KnowledgeEntryUpsertRequest
from backend.scripts.init_db import DB_PATH


MANUAL_ENTRIES = [
    {
        "knowledge_entry_id": "kb_bda_deepseek_openai_compatible",
        "title": "BDA Copilot DeepSeek OpenAI-compatible runtime",
        "category": "copilot",
        "subcategory": "llm_provider",
        "summary": "BDA Copilot uses the same OpenAI-compatible chat interface for DeepSeek and other compatible providers.",
        "content": (
            "Configure BDA Copilot with llm_api_base=https://api.deepseek.com/v1, "
            "llm_model=deepseek-v4-pro, and a server-side API key. Runtime chat enters "
            "backend/app/copilot/runtime.py, then backend/app/copilot/service.py, then "
            "backend/app/copilot/provider.py. Provider-specific secrets must stay on the "
            "backend and must never be returned in API responses."
        ),
        "tags": ["DeepSeek", "OpenAI-compatible", "Copilot", "configuration"],
        "citation": "BDA manual curated knowledge, 2026-07-01.",
        "metadata": {"entry_mode": "manual", "owner": "BDA"},
    },
    {
        "knowledge_entry_id": "kb_bda_manual_curated_knowledge",
        "title": "Manual curated BDA knowledge entry workflow",
        "category": "knowledge",
        "subcategory": "curation",
        "summary": "Manual knowledge entries are stable reviewed guidance; automated literature claims remain pending until reviewed.",
        "content": (
            "Use manual curated entries for BDA operating rules, model routing guidance, "
            "assay interpretation rules, and project-specific decisions that have already "
            "been reviewed. Use automated literature ingestion for discoverable evidence, "
            "but keep extracted claims as pending evidence until a researcher or admin accepts them."
        ),
        "tags": ["manual", "curated", "literature", "review"],
        "citation": "BDA manual curated knowledge, 2026-07-01.",
        "metadata": {"entry_mode": "manual", "owner": "BDA"},
    },
    {
        "knowledge_entry_id": "kb_bda_copilot_context_order",
        "title": "BDA Copilot context order",
        "category": "copilot",
        "subcategory": "context",
        "summary": "Copilot should prefer project facts, curated knowledge, accepted evidence, and then LLM synthesis.",
        "content": (
            "When answering BDA questions, resolve context in this order: current project "
            "records and artifacts, curated knowledge_entries, accepted literature claims, "
            "pending literature evidence with a clear pending label, and finally LLM synthesis. "
            "Do not treat model output as experimental fact."
        ),
        "tags": ["context", "RAG", "evidence", "project"],
        "citation": "BDA manual curated knowledge, 2026-07-01.",
        "metadata": {"entry_mode": "manual", "owner": "BDA"},
    },
    {
        "knowledge_entry_id": "kb_bda_route_plan_manual_automation_boundary",
        "title": "Route planning manual and automation boundary",
        "category": "workflow",
        "subcategory": "route_planning",
        "summary": "Manual route constraints and automated campaign decisions must be reviewable before compute submission.",
        "content": (
            "Manual route notes can define target, constraints, preferred modules, disabled "
            "modules, and acceptance gates. Automated campaign evaluation can propose parameter "
            "patches, but reviewed approval is required before creating the next round or submitting cluster jobs."
        ),
        "tags": ["workflow", "route", "campaign", "review"],
        "citation": "BDA manual curated knowledge, 2026-07-01.",
        "metadata": {"entry_mode": "manual", "owner": "BDA"},
    },
]


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        for entry in MANUAL_ENTRIES:
            knowledge.upsert_entry(connection, KnowledgeEntryUpsertRequest(**entry))
        print(f"Imported {len(MANUAL_ENTRIES)} manual BDA knowledge entries into {DB_PATH}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
