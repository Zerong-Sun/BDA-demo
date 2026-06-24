from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

from ..copilot.provider import get_llm_provider
from ..copilot.research import get_europe_pmc_full_text, search_literature
from ..settings import get_settings

MAX_CHUNK_CHARS = 3500
MAX_EXTRACTION_CHUNKS = 8
MAX_FULL_TEXT_BYTES = 10 * 1024 * 1024


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


@dataclass
class Section:
    title: str
    path: str
    paragraphs: list[str]


def parse_full_text_xml(xml_text: str) -> list[Section]:
    if len(xml_text.encode("utf-8")) > MAX_FULL_TEXT_BYTES:
        raise ValueError("full_text_too_large")
    lowered_prefix = xml_text[:2000].lower()
    if "<!doctype" in lowered_prefix or "<!entity" in lowered_prefix:
        raise ValueError("unsafe_xml_declaration")
    root = ET.fromstring(xml_text)
    sections: list[Section] = []

    abstract_paragraphs: list[str] = []
    for element in root.iter():
        if _local_name(element.tag) == "abstract":
            abstract_paragraphs.extend(
                text for child in element.iter()
                if _local_name(child.tag) == "p" and (text := _text(child))
            )
            break
    if abstract_paragraphs:
        sections.append(Section("Abstract", "Abstract", abstract_paragraphs))

    body = next((element for element in root.iter() if _local_name(element.tag) == "body"), None)
    if body is None:
        return sections

    def walk(section: ET.Element, parents: list[str]) -> None:
        title_element = next(
            (child for child in section if _local_name(child.tag) == "title"),
            None,
        )
        title = _text(title_element) or "Untitled section"
        path = " > ".join([*parents, title])
        paragraphs = [
            _text(child)
            for child in section
            if _local_name(child.tag) == "p" and _text(child)
        ]
        if paragraphs:
            sections.append(Section(title, path, paragraphs))
        for child in section:
            if _local_name(child.tag) == "sec":
                walk(child, [*parents, title])

    for child in body:
        if _local_name(child.tag) == "sec":
            walk(child, [])
        elif _local_name(child.tag) == "p" and (paragraph := _text(child)):
            sections.append(Section("Body", "Body", [paragraph]))
    return sections


def chunk_sections(sections: list[Section]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for section in sections:
        buffer = ""
        for paragraph in section.paragraphs:
            candidates = [paragraph]
            if len(paragraph) > MAX_CHUNK_CHARS:
                candidates = [
                    paragraph[i:i + MAX_CHUNK_CHARS]
                    for i in range(0, len(paragraph), MAX_CHUNK_CHARS)
                ]
            for candidate in candidates:
                combined = f"{buffer}\n\n{candidate}".strip() if buffer else candidate
                if buffer and len(combined) > MAX_CHUNK_CHARS:
                    chunks.append({
                        "section_title": section.title,
                        "section_path": section.path,
                        "content": buffer,
                    })
                    buffer = candidate
                else:
                    buffer = combined
        if buffer:
            chunks.append({
                "section_title": section.title,
                "section_path": section.path,
                "content": buffer,
            })
    return chunks


def _clear_document_content(connection: sqlite3.Connection, document_id: str) -> None:
    claim_rows = connection.execute(
        "SELECT claim_id FROM scientific_claims WHERE document_id = ?",
        (document_id,),
    ).fetchall()
    claim_ids = [row["claim_id"] for row in claim_rows]
    for claim_id in claim_ids:
        connection.execute(
            "DELETE FROM claim_relations WHERE source_claim_id = ? OR target_claim_id = ?",
            (claim_id, claim_id),
        )
    connection.execute(
        "DELETE FROM claim_evidence WHERE claim_id IN (SELECT claim_id FROM scientific_claims WHERE document_id = ?)",
        (document_id,),
    )
    connection.execute(
        "DELETE FROM scientific_claims WHERE document_id = ?",
        (document_id,),
    )
    connection.execute(
        "DELETE FROM document_chunks WHERE document_id = ?",
        (document_id,),
    )


def _upsert_document(
    connection: sqlite3.Connection,
    item: dict[str, Any],
    *,
    full_text_xml: str | None,
) -> tuple[str, list[dict[str, Any]], bool]:
    external_source = str(item.get("source") or "MED")
    external_id = str(item.get("identifier") or item.get("pmid") or item.get("pmcid") or item.get("doi"))
    uri = item.get("url") or f"https://europepmc.org/article/{external_source}/{external_id}"
    source_id = _stable_id("source", f"europe_pmc:{external_source}:{external_id}")
    document_id = _stable_id("doc", f"europe_pmc:{external_source}:{external_id}")
    existing = connection.execute(
        """
        SELECT d.document_id, d.content_kind, d.full_text_status, s.content_hash
        FROM literature_documents d
        JOIN research_sources s ON s.source_id = d.source_id
        WHERE d.external_source = ? AND d.external_id = ?
        """,
        (external_source, external_id),
    ).fetchone()
    preserve_existing_full_text = (
        existing is not None
        and existing["content_kind"] == "full_text"
        and full_text_xml is None
    )
    raw_for_hash = full_text_xml or item.get("abstract") or json.dumps(item, sort_keys=True)
    content_hash = hashlib.sha256(raw_for_hash.encode()).hexdigest()
    if preserve_existing_full_text:
        content_hash = existing["content_hash"]
    content_changed = existing is None or existing["content_hash"] != content_hash
    connection.execute(
        """
        INSERT INTO research_sources (
            source_id, source_type, title, uri, content_hash, version_ref,
            metadata_json, status, last_ingested_at
        ) VALUES (?, 'europe_pmc', ?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
        ON CONFLICT(source_type, uri) DO UPDATE SET
            title=excluded.title,
            content_hash=excluded.content_hash,
            version_ref=excluded.version_ref,
            metadata_json=excluded.metadata_json,
            status='active',
            last_ingested_at=CURRENT_TIMESTAMP,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            source_id,
            item.get("title") or external_id,
            uri,
            content_hash,
            item.get("year"),
            json.dumps({
                "doi": item.get("doi"),
                "pmid": item.get("pmid"),
                "pmcid": item.get("pmcid"),
                "is_open_access": item.get("is_open_access"),
            }),
        ),
    )
    source_row = connection.execute(
        "SELECT source_id FROM research_sources WHERE source_type='europe_pmc' AND uri=?",
        (uri,),
    ).fetchone()
    source_id = source_row["source_id"]
    if preserve_existing_full_text:
        content_kind = existing["content_kind"]
        full_text_status = existing["full_text_status"]
    else:
        content_kind = "full_text" if full_text_xml else ("abstract" if item.get("abstract") else "metadata")
        full_text_status = "available" if full_text_xml else (
            "not_open_access" if not item.get("is_open_access") else "unavailable"
        )
    connection.execute(
        """
        INSERT INTO literature_documents (
            document_id, source_id, external_source, external_id, title,
            authors, journal, publication_year, doi, pmid, pmcid,
            abstract_text, content_kind, full_text_status, metadata_json, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
        ON CONFLICT(external_source, external_id) DO UPDATE SET
            source_id=excluded.source_id,
            title=excluded.title,
            authors=excluded.authors,
            journal=excluded.journal,
            publication_year=excluded.publication_year,
            doi=excluded.doi,
            pmid=excluded.pmid,
            pmcid=excluded.pmcid,
            abstract_text=excluded.abstract_text,
            content_kind=excluded.content_kind,
            full_text_status=excluded.full_text_status,
            metadata_json=excluded.metadata_json,
            status='active',
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            document_id,
            source_id,
            external_source,
            external_id,
            item.get("title") or external_id,
            item.get("authors"),
            item.get("journal"),
            int(item["year"]) if str(item.get("year") or "").isdigit() else None,
            item.get("doi"),
            item.get("pmid"),
            item.get("pmcid"),
            item.get("abstract"),
            content_kind,
            full_text_status,
            json.dumps({
                "url": uri,
                "cited_by_count": item.get("cited_by_count"),
                "is_open_access": item.get("is_open_access"),
            }),
        ),
    )
    document_row = connection.execute(
        "SELECT document_id FROM literature_documents WHERE external_source=? AND external_id=?",
        (external_source, external_id),
    ).fetchone()
    document_id = document_row["document_id"]
    if not content_changed:
        rows = connection.execute(
            """
            SELECT chunk_id, section_title, section_path, content
            FROM document_chunks
            WHERE document_id = ?
            ORDER BY chunk_index
            """,
            (document_id,),
        ).fetchall()
        return document_id, [dict(row) for row in rows], False

    _clear_document_content(connection, document_id)

    if full_text_xml:
        sections = parse_full_text_xml(full_text_xml)
    elif item.get("abstract"):
        sections = [Section("Abstract", "Abstract", [item["abstract"]])]
    else:
        sections = []
    chunks = chunk_sections(sections)
    stored_chunks: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        content = chunk["content"]
        chunk_id = _stable_id("chunk", f"{document_id}:{index}:{content}")
        connection.execute(
            """
            INSERT INTO document_chunks (
                chunk_id, document_id, section_title, section_path,
                chunk_index, content, content_hash, token_estimate,
                metadata_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', 'active')
            """,
            (
                chunk_id,
                document_id,
                chunk.get("section_title"),
                chunk.get("section_path"),
                index,
                content,
                hashlib.sha256(content.encode()).hexdigest(),
                max(1, len(content) // 4),
            ),
        )
        stored_chunks.append({"chunk_id": chunk_id, **chunk})
    return document_id, stored_chunks, True


def _parse_json_response(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("claim_extraction_not_object")
    return value


def _extract_claim_batch(
    connection: sqlite3.Connection,
    document_id: str,
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.llm_api_key:
        return {"status": "skipped_no_api_key", "claims_created": 0}
    selected = chunks[:MAX_EXTRACTION_CHUNKS]
    if not selected:
        return {"status": "skipped_no_content", "claims_created": 0}
    source_text = "\n\n".join(
        f"[CHUNK {chunk['chunk_id']} | {chunk.get('section_path')}]\n{chunk['content']}"
        for chunk in selected
    )
    prompt = f"""
Extract traceable scientific claims from this life-science paper.
Return one JSON object with "chunk_summaries" and "claims" arrays.
Each chunk summary must contain chunk_id and a concise summary grounded only in that chunk.
Each claim must contain:
- statement: a cautious standalone statement
- claim_type: one of method, finding, limitation, parameter, experiment, hypothesis
- evidence_excerpt: an exact verbatim substring copied from one chunk, maximum 300 characters
- chunk_id: the exact CHUNK identifier
- context: object with organism, protein, model, assay, conditions, limitations when present
- confidence: number from 0 to 1

Do not infer beyond the supplied text. Skip claims without an exact supporting excerpt.

{source_text}
""".strip()
    response = get_llm_provider().chat(
        [
            {"role": "system", "content": "You extract evidence-grounded scientific claims as strict JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    payload = _parse_json_response(response.content)
    chunks_by_id = {chunk["chunk_id"]: chunk for chunk in selected}
    summaries_created = 0
    for item in payload.get("chunk_summaries") or []:
        if not isinstance(item, dict):
            continue
        chunk_id = str(item.get("chunk_id") or "")
        summary = str(item.get("summary") or "").strip()
        if chunk_id not in chunks_by_id or not summary:
            continue
        connection.execute(
            """
            UPDATE document_chunks
            SET summary_text = ?, summary_method = 'llm_chunk_summary'
            WHERE chunk_id = ?
            """,
            (summary[:2000], chunk_id),
        )
        summaries_created += 1
    created = 0
    rejected = 0
    allowed_types = {"method", "finding", "limitation", "parameter", "experiment", "hypothesis"}
    for item in payload.get("claims") or []:
        if not isinstance(item, dict):
            rejected += 1
            continue
        statement = str(item.get("statement") or "").strip()
        excerpt = str(item.get("evidence_excerpt") or "").strip()
        chunk_id = str(item.get("chunk_id") or "")
        chunk = chunks_by_id.get(chunk_id)
        if (
            not statement
            or len(statement) > 2000
            or not excerpt
            or len(excerpt) > 300
            or chunk is None
            or excerpt not in chunk["content"]
        ):
            rejected += 1
            continue
        claim_id = f"claim_{uuid.uuid4().hex[:16]}"
        claim_type = str(item.get("claim_type") or "finding")
        if claim_type not in allowed_types:
            claim_type = "finding"
        confidence = item.get("confidence")
        confidence = (
            max(0.0, min(1.0, float(confidence)))
            if isinstance(confidence, (int, float)) else None
        )
        connection.execute(
            """
            INSERT INTO scientific_claims (
                claim_id, document_id, statement, claim_type, context_json,
                confidence, extraction_method, review_status
            ) VALUES (?, ?, ?, ?, ?, ?, 'llm_evidence_extraction', 'pending_review')
            """,
            (
                claim_id,
                document_id,
                statement,
                claim_type,
                json.dumps(item.get("context") if isinstance(item.get("context"), dict) else {}),
                confidence,
            ),
        )
        start = chunk["content"].index(excerpt)
        connection.execute(
            """
            INSERT INTO claim_evidence (
                evidence_id, claim_id, chunk_id, evidence_excerpt,
                start_offset, end_offset, evidence_role
            ) VALUES (?, ?, ?, ?, ?, ?, 'supports')
            """,
            (
                f"evidence_{uuid.uuid4().hex[:16]}",
                claim_id,
                chunk_id,
                excerpt,
                start,
                start + len(excerpt),
            ),
        )
        created += 1
    return {
        "status": "completed",
        "summaries_created": summaries_created,
        "claims_created": created,
        "claims_rejected_untraceable": rejected,
    }


def extract_claims_with_llm(
    connection: sqlite3.Connection,
    document_id: str,
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    if not get_settings().llm_api_key:
        return {"status": "skipped_no_api_key", "claims_created": 0}
    if not chunks:
        return {"status": "skipped_no_content", "claims_created": 0}
    totals = {
        "status": "completed",
        "batches": 0,
        "summaries_created": 0,
        "claims_created": 0,
        "claims_rejected_untraceable": 0,
    }
    for start in range(0, len(chunks), MAX_EXTRACTION_CHUNKS):
        result = _extract_claim_batch(
            connection,
            document_id,
            chunks[start:start + MAX_EXTRACTION_CHUNKS],
        )
        totals["batches"] += 1
        for key in ("summaries_created", "claims_created", "claims_rejected_untraceable"):
            totals[key] += int(result.get(key) or 0)
    return totals


def detect_claim_relations_with_llm(
    connection: sqlite3.Connection,
    *,
    limit: int = 30,
    accepted_only: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.llm_api_key:
        return {"status": "skipped_no_api_key", "relations_created": 0}
    where = "WHERE c.review_status = 'accepted'" if accepted_only else ""
    rows = connection.execute(
        f"""
        SELECT c.claim_id, c.statement, c.claim_type, c.context_json,
               d.title, d.doi, d.pmid, d.publication_year
        FROM scientific_claims c
        JOIN literature_documents d ON d.document_id = c.document_id
        {where}
        ORDER BY c.created_at DESC
        LIMIT ?
        """,
        (max(2, min(limit, 100)),),
    ).fetchall()
    claims = [dict(row) for row in rows]
    if len(claims) < 2:
        return {"status": "skipped_insufficient_claims", "relations_created": 0}
    claim_text = "\n".join(
        f"[{item['claim_id']}] {item['statement']} | source={item['title']}"
        for item in claims
    )
    prompt = f"""
Compare the evidence-grounded claims below. Return strict JSON with a "relations" array.
Only include meaningful scientific relationships. Each item must contain:
- source_claim_id
- target_claim_id
- relation_type: supports, qualifies, or contradicts
- rationale: concise explanation of the relationship and contextual difference
- confidence: number from 0 to 1

Do not infer a contradiction merely because experiments use different systems or conditions.
Prefer "qualifies" when context, organism, assay, construct, or model assumptions differ.

{claim_text}
""".strip()
    response = get_llm_provider().chat(
        [
            {"role": "system", "content": "You compare scientific claims conservatively as strict JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    payload = _parse_json_response(response.content)
    valid_ids = {item["claim_id"] for item in claims}
    created = 0
    rejected = 0
    for item in payload.get("relations") or []:
        if not isinstance(item, dict):
            rejected += 1
            continue
        source_id = str(item.get("source_claim_id") or "")
        target_id = str(item.get("target_claim_id") or "")
        relation_type = str(item.get("relation_type") or "")
        if (
            source_id not in valid_ids
            or target_id not in valid_ids
            or source_id == target_id
            or relation_type not in {"supports", "qualifies", "contradicts"}
        ):
            rejected += 1
            continue
        confidence = item.get("confidence")
        confidence = (
            max(0.0, min(1.0, float(confidence)))
            if isinstance(confidence, (int, float)) else None
        )
        connection.execute(
            """
            INSERT INTO claim_relations (
                relation_id, source_claim_id, target_claim_id, relation_type,
                rationale, confidence, review_status
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending_review')
            ON CONFLICT(source_claim_id, target_claim_id, relation_type) DO UPDATE SET
                rationale=excluded.rationale,
                confidence=excluded.confidence,
                review_status='pending_review'
            """,
            (
                f"relation_{uuid.uuid4().hex[:16]}",
                source_id,
                target_id,
                relation_type,
                str(item.get("rationale") or "")[:2000],
                confidence,
            ),
        )
        created += 1
    return {
        "status": "completed",
        "relations_created": created,
        "relations_rejected": rejected,
    }


def ingest_europe_pmc_query(
    connection: sqlite3.Connection,
    query: str,
    *,
    limit: int = 5,
    fetch_full_text: bool = True,
    extract_claims: bool = True,
) -> dict[str, Any]:
    search = search_literature(query, limit=limit)
    documents = []
    for item in search["results"]:
        full_text_xml = None
        full_text_error = None
        if fetch_full_text and item.get("pmcid") and item.get("is_open_access"):
            try:
                full_text_xml = get_europe_pmc_full_text(item["pmcid"])
            except Exception as exc:  # network/provider errors are recorded per document
                full_text_error = str(exc)[:300]
        document_id, chunks, content_changed = _upsert_document(
            connection,
            item,
            full_text_xml=full_text_xml,
        )
        existing_claim_count = connection.execute(
            "SELECT COUNT(*) AS total FROM scientific_claims WHERE document_id = ?",
            (document_id,),
        ).fetchone()["total"]
        if not extract_claims:
            extraction = {"status": "disabled", "claims_created": 0}
        elif not content_changed and existing_claim_count:
            extraction = {
                "status": "skipped_unchanged",
                "claims_created": 0,
                "existing_claims": int(existing_claim_count),
            }
        else:
            extraction = extract_claims_with_llm(connection, document_id, chunks)
        documents.append({
            "document_id": document_id,
            "title": item.get("title"),
            "content_kind": "full_text" if full_text_xml else (
                "abstract" if item.get("abstract") else "metadata"
            ),
            "chunk_count": len(chunks),
            "content_changed": content_changed,
            "full_text_error": full_text_error,
            "extraction": extraction,
        })
    return {
        "query": query,
        "documents_ingested": len(documents),
        "documents": documents,
    }
