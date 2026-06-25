import json

import pytest

from backend.app.db import connect, release_connection
from backend.app.services import llm_planning_service
from backend.app.settings import get_settings


class _FakeProvider:
    def __init__(self, payload):
        self.payload = payload

    def chat(self, messages, tools=None, response_format=None):
        return type("Response", (), {"content": json.dumps(self.payload)})()


@pytest.fixture
def db_connection():
    connection = connect()
    try:
        yield connection
    finally:
        release_connection(connection)


def test_generic_llm_route_is_restricted_to_known_templates(db_connection, monkeypatch):
    settings = get_settings()
    settings.llm_api_key = "test"
    monkeypatch.setattr(
        llm_planning_service,
        "get_llm_provider",
        lambda: _FakeProvider({
            "summary": "validated route",
            "steps": [
                {
                    "template_id": "rf",
                    "name": "Constrained backbone generation",
                    "methods": ["RFdiffusion"],
                    "parameters": {"planned_designs": 300, "command": "rm -rf /"},
                    "estimate": {"planned": 300, "unit": "backbones", "duration": "4h GPU"},
                },
                {
                    "template_id": "mpnn",
                    "name": "Sequence design",
                    "methods": ["ProteinMPNN"],
                    "parameters": {"sampling_temp": 0.1},
                    "estimate": {"planned": 1200, "unit": "sequences", "duration": "1h GPU"},
                },
                {"template_id": "unknown", "name": "Unsafe new model"},
            ],
        }),
    )

    result = llm_planning_service.plan_generic_workflow(
        db_connection,
        target="sweet protein",
        objective="protein_design",
        constraints={},
    )

    assert result["mode"] == "llm_validated"
    assert [item["template_id"] for item in result["steps"]] == ["rf", "mpnn"]
    assert "command" not in result["steps"][0]["parameters"]


def test_research_question_decomposition_rejects_unknown_tools(monkeypatch):
    settings = get_settings()
    settings.llm_api_key = "test"
    monkeypatch.setattr(
        llm_planning_service,
        "get_llm_provider",
        lambda: _FakeProvider({
            "questions": [
                {
                    "track": "mechanism",
                    "question": "Which receptor regions have functional evidence?",
                    "priority": 10,
                    "query": {"kind": "literature", "term": "sweet protein receptor activation"},
                },
                {
                    "track": "unsafe",
                    "question": "Run arbitrary shell",
                    "query": {"kind": "shell", "term": "rm"},
                },
            ],
        }),
    )

    questions = llm_planning_service.decompose_research_questions({
        "title": "Sweet protein",
        "objective": "Design a food-compatible sweet protein",
        "constraints_json": {},
        "source_material_json": [],
    })

    assert questions is not None
    assert len(questions) == 1
    assert questions[0]["query"]["kind"] == "literature"
