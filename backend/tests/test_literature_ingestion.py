import sqlite3
from pathlib import Path

import pytest
from backend.app.repositories import literature, literature_subscriptions
from backend.app.services import literature_ingestion
from backend.app.services.literature_subscription_service import (
    run_due_subscriptions,
    run_subscription,
)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    schema = Path(__file__).resolve().parents[1] / "db" / "schema.sql"
    connection.executescript(schema.read_text())
    return connection


FULL_TEXT_XML = """
<article>
  <front>
    <article-meta>
      <abstract><p>ProteinMPNN designed sequences for fixed backbones.</p></abstract>
    </article-meta>
  </front>
  <body>
    <sec>
      <title>Methods</title>
      <p>Sequences were sampled at temperature 0.1.</p>
    </sec>
    <sec>
      <title>Results</title>
      <p>The designed proteins showed improved recovery in this benchmark.</p>
    </sec>
  </body>
</article>
""".strip()


def _search_result():
    return {
        "query": "ProteinMPNN",
        "source": "Europe PMC",
        "total": 1,
        "results": [{
            "source": "PMC",
            "identifier": "PMC123",
            "title": "Protein sequence design",
            "authors": "A. Author",
            "journal": "Example Journal",
            "year": "2024",
            "doi": "10.1000/example",
            "pmid": "123",
            "pmcid": "PMC123",
            "cited_by_count": 4,
            "is_open_access": True,
            "abstract": "ProteinMPNN designed sequences for fixed backbones.",
            "url": "https://europepmc.org/article/PMC/PMC123",
        }],
    }


def test_parse_full_text_and_ingest_without_api_key(monkeypatch):
    connection = _connection()
    monkeypatch.setattr(literature_ingestion, "search_literature", lambda query, limit=5: _search_result())
    monkeypatch.setattr(literature_ingestion, "get_europe_pmc_full_text", lambda pmcid: FULL_TEXT_XML)
    settings = literature_ingestion.get_settings()
    original_key = settings.llm_api_key
    settings.llm_api_key = ""
    try:
        result = literature_ingestion.ingest_europe_pmc_query(
            connection,
            "ProteinMPNN",
            limit=1,
            fetch_full_text=True,
            extract_claims=True,
        )
        document_id = result["documents"][0]["document_id"]
        document = literature.get_document(connection, document_id)
    finally:
        settings.llm_api_key = original_key
        connection.close()

    assert result["documents_ingested"] == 1
    assert result["documents"][0]["content_kind"] == "full_text"
    assert result["documents"][0]["extraction"]["status"] == "skipped_no_api_key"
    assert document is not None
    assert len(document["chunks"]) == 3


def test_xml_parser_rejects_unsafe_or_oversized_input():
    with pytest.raises(ValueError, match="unsafe_xml_declaration"):
        literature_ingestion.parse_full_text_xml(
            '<!DOCTYPE article [<!ENTITY x "unsafe">]><article><body/></article>'
        )
    with pytest.raises(ValueError, match="full_text_too_large"):
        literature_ingestion.parse_full_text_xml(
            "<article>" + ("x" * (literature_ingestion.MAX_FULL_TEXT_BYTES + 1)) + "</article>"
        )


def test_llm_claim_requires_exact_evidence(monkeypatch):
    connection = _connection()
    monkeypatch.setattr(literature_ingestion, "search_literature", lambda query, limit=5: _search_result())
    monkeypatch.setattr(literature_ingestion, "get_europe_pmc_full_text", lambda pmcid: FULL_TEXT_XML)
    settings = literature_ingestion.get_settings()
    original_key = settings.llm_api_key
    settings.llm_api_key = "test-key"

    class FakeResponse:
        content = ""

    class FakeProvider:
        def chat(self, messages, tools=None, response_format=None):
            chunk_id = next(
                line.split(" |", 1)[0].removeprefix("[CHUNK ")
                for line in messages[-1]["content"].splitlines()
                if line.startswith("[CHUNK ") and "Methods" in line
            )
            response = FakeResponse()
            response.content = (
                '{"chunk_summaries":['
                f'{{"chunk_id":"{chunk_id}","summary":"Sequences were sampled at temperature 0.1."}}'
                '],"claims":['
                '{"statement":"The study sampled sequences at temperature 0.1.",'
                '"claim_type":"parameter",'
                '"evidence_excerpt":"Sequences were sampled at temperature 0.1.",'
                f'"chunk_id":"{chunk_id}",'
                '"context":{"model":"ProteinMPNN"},"confidence":0.95},'
                '{"statement":"Unsupported claim","claim_type":"finding",'
                '"evidence_excerpt":"This text is absent.",'
                f'"chunk_id":"{chunk_id}","context":{{}},"confidence":0.5}}'
                "]}"
            )
            return response

    monkeypatch.setattr(literature_ingestion, "get_llm_provider", lambda: FakeProvider())
    try:
        result = literature_ingestion.ingest_europe_pmc_query(
            connection,
            "ProteinMPNN",
            limit=1,
            fetch_full_text=True,
            extract_claims=True,
        )
        document_id = result["documents"][0]["document_id"]
        document = literature.get_document(connection, document_id)
        claims = literature.search_library(connection, "temperature 0.1")
    finally:
        settings.llm_api_key = original_key
        connection.close()

    extraction = result["documents"][0]["extraction"]
    assert extraction["claims_created"] == 1
    assert extraction["summaries_created"] == 1
    assert extraction["claims_rejected_untraceable"] == 1
    assert document is not None
    assert document["claims"][0]["review_status"] == "pending_review"
    assert claims[0]["evidence_excerpt"] == "Sequences were sampled at temperature 0.1."


def test_reingest_preserves_reviewed_claims_and_existing_full_text(monkeypatch):
    connection = _connection()
    monkeypatch.setattr(literature_ingestion, "search_literature", lambda query, limit=5: _search_result())
    monkeypatch.setattr(literature_ingestion, "get_europe_pmc_full_text", lambda pmcid: FULL_TEXT_XML)
    settings = literature_ingestion.get_settings()
    original_key = settings.llm_api_key
    settings.llm_api_key = "test-key"

    class FakeResponse:
        content = ""

    class FakeProvider:
        def chat(self, messages, tools=None, response_format=None):
            chunk_id = next(
                line.split(" |", 1)[0].removeprefix("[CHUNK ")
                for line in messages[-1]["content"].splitlines()
                if line.startswith("[CHUNK ")
            )
            response = FakeResponse()
            response.content = (
                '{"claims":[{"statement":"ProteinMPNN designed sequences.",'
                '"claim_type":"finding",'
                '"evidence_excerpt":"ProteinMPNN designed sequences for fixed backbones.",'
                f'"chunk_id":"{chunk_id}","context":{{}},"confidence":0.9}}]}}'
            )
            return response

    monkeypatch.setattr(literature_ingestion, "get_llm_provider", lambda: FakeProvider())
    try:
        first = literature_ingestion.ingest_europe_pmc_query(connection, "ProteinMPNN", limit=1)
        document_id = first["documents"][0]["document_id"]
        claim_id = connection.execute(
            "SELECT claim_id FROM scientific_claims WHERE document_id = ?",
            (document_id,),
        ).fetchone()["claim_id"]
        literature.review_claim(
            connection,
            claim_id,
            review_status="accepted",
            reviewed_by="reviewer",
        )

        monkeypatch.setattr(
            literature_ingestion,
            "get_europe_pmc_full_text",
            lambda pmcid: (_ for _ in ()).throw(RuntimeError("temporary network failure")),
        )
        second = literature_ingestion.ingest_europe_pmc_query(connection, "ProteinMPNN", limit=1)
        document = literature.get_document(connection, document_id)
    finally:
        settings.llm_api_key = original_key
        connection.close()

    assert second["documents"][0]["content_changed"] is False
    assert second["documents"][0]["extraction"]["status"] == "skipped_unchanged"
    assert document is not None
    assert document["content_kind"] == "full_text"
    assert document["claims"][0]["review_status"] == "accepted"


def test_detect_claim_relations_marks_result_pending_review(monkeypatch):
    connection = _connection()
    connection.execute(
        """
        INSERT INTO research_sources (source_id, source_type, title, uri)
        VALUES ('source_a', 'test', 'A', 'test://a'), ('source_b', 'test', 'B', 'test://b')
        """
    )
    connection.execute(
        """
        INSERT INTO literature_documents (
            document_id, source_id, external_source, external_id, title
        ) VALUES
            ('doc_a', 'source_a', 'TEST', 'A', 'Study A'),
            ('doc_b', 'source_b', 'TEST', 'B', 'Study B')
        """
    )
    connection.execute(
        """
        INSERT INTO scientific_claims (
            claim_id, document_id, statement, extraction_method
        ) VALUES
            ('claim_a', 'doc_a', 'Higher temperature increased diversity.', 'test'),
            ('claim_b', 'doc_b', 'Higher temperature reduced recovery.', 'test')
        """
    )
    settings = literature_ingestion.get_settings()
    original_key = settings.llm_api_key
    settings.llm_api_key = "test-key"

    class FakeResponse:
        content = (
            '{"relations":[{"source_claim_id":"claim_a","target_claim_id":"claim_b",'
            '"relation_type":"qualifies","rationale":"The outcomes measure different properties.",'
            '"confidence":0.8}]}'
        )

    class FakeProvider:
        def chat(self, messages, tools=None, response_format=None):
            return FakeResponse()

    monkeypatch.setattr(literature_ingestion, "get_llm_provider", lambda: FakeProvider())
    try:
        result = literature_ingestion.detect_claim_relations_with_llm(connection)
        relations = literature.list_relations(connection)
    finally:
        settings.llm_api_key = original_key
        connection.close()

    assert result["relations_created"] == 1
    assert relations[0]["relation_type"] == "qualifies"
    assert relations[0]["review_status"] == "pending_review"


def test_due_literature_subscription_runs_and_reschedules(monkeypatch):
    connection = _connection()
    connection.execute(
        """
        INSERT INTO literature_subscriptions (
            subscription_id, name, query, interval_hours, result_limit,
            fetch_full_text, extract_claims, next_run_at
        ) VALUES ('sub_test', 'Protein design', 'ProteinMPNN', 12, 1, 0, 0, '2000-01-01')
        """
    )
    monkeypatch.setattr(
        "backend.app.services.literature_subscription_service.ingest_europe_pmc_query",
        lambda connection, query, **kwargs: {"query": query, "documents_ingested": 1},
    )
    result = run_due_subscriptions(connection)
    item = connection.execute(
        "SELECT * FROM literature_subscriptions WHERE subscription_id='sub_test'"
    ).fetchone()
    connection.close()

    assert result["subscriptions_run"] == 1
    assert item["last_status"] == "completed"
    assert item["last_run_at"] is not None
    assert item["next_run_at"] > item["last_run_at"]


def test_subscription_failure_rolls_back_partial_ingestion(monkeypatch):
    connection = _connection()
    connection.execute(
        """
        INSERT INTO literature_subscriptions (
            subscription_id, name, query, interval_hours, result_limit,
            fetch_full_text, extract_claims, next_run_at
        ) VALUES ('sub_fail', 'Failing import', 'broken', 12, 1, 0, 0, CURRENT_TIMESTAMP)
        """
    )

    def partial_failure(connection, query, **kwargs):
        connection.execute(
            """
            INSERT INTO research_sources (source_id, source_type, title, uri)
            VALUES ('partial_source', 'test', 'Partial', 'test://partial')
            """
        )
        raise RuntimeError("provider failed")

    monkeypatch.setattr(
        "backend.app.services.literature_subscription_service.ingest_europe_pmc_query",
        partial_failure,
    )
    item = dict(connection.execute(
        "SELECT * FROM literature_subscriptions WHERE subscription_id='sub_fail'"
    ).fetchone())
    result = run_subscription(connection, item)
    partial = connection.execute(
        "SELECT 1 FROM research_sources WHERE source_id='partial_source'"
    ).fetchone()
    status = connection.execute(
        "SELECT last_status FROM literature_subscriptions WHERE subscription_id='sub_fail'"
    ).fetchone()["last_status"]
    connection.close()

    assert result["status"] == "failed"
    assert partial is None
    assert status == "failed"


def test_due_subscription_can_only_be_claimed_once():
    connection = _connection()
    connection.execute(
        """
        INSERT INTO literature_subscriptions (
            subscription_id, name, query, interval_hours, result_limit,
            fetch_full_text, extract_claims, next_run_at
        ) VALUES ('sub_claim', 'Claim once', 'protein', 12, 1, 0, 0, '2000-01-01')
        """
    )
    first = literature_subscriptions.claim_due_subscription(connection, "sub_claim")
    second = literature_subscriptions.claim_due_subscription(connection, "sub_claim")
    connection.close()

    assert first is not None
    assert first["last_status"] == "running"
    assert second is None
