from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from typing import Any

from ..repositories import research_planner

URL_RE = re.compile(r"https?://[^\s)>\]]+")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"


def split_markdown(content: str) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    section_path: list[str] = []
    current_title = "Document"
    current_level = 1
    buffer: list[str] = []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if not text:
            return
        chunks.append({
            "section_title": current_title,
            "section_path": " / ".join(section_path) or current_title,
            "content": text,
        })

    for line in content.splitlines():
        match = HEADING_RE.match(line)
        if match:
            flush()
            buffer = []
            current_level = len(match.group(1))
            current_title = match.group(2).strip()
            section_path = section_path[: current_level - 1]
            section_path.append(current_title)
        else:
            buffer.append(line)
    flush()
    return chunks or [{
        "section_title": "Document",
        "section_path": "Document",
        "content": content.strip(),
    }]


def ingest_markdown_source(
    connection: sqlite3.Connection,
    *,
    research_brief_id: str,
    title: str,
    content: str,
    source_uri: str | None,
) -> dict[str, Any]:
    brief = research_planner.get_brief(connection, research_brief_id)
    if brief is None:
        raise ValueError("research_brief_not_found")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    uri = source_uri or f"upload://markdown/{digest}"
    # Scope uploaded sources to a brief. The same file may be attached to
    # multiple projects without overwriting source ownership metadata.
    source_id = _stable_id("source", f"{research_brief_id}:user_markdown:{uri}")
    document_id = _stable_id("doc", f"{source_id}:document")
    external_id = source_id
    connection.execute(
        """
        INSERT INTO research_sources (
            source_id, source_type, title, uri, content_hash,
            metadata_json, last_ingested_at
        ) VALUES (?, 'user_markdown', ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(source_type, uri) DO UPDATE SET
            title = excluded.title,
            content_hash = excluded.content_hash,
            metadata_json = excluded.metadata_json,
            last_ingested_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            source_id,
            title,
            uri,
            digest,
            json.dumps({"research_brief_id": research_brief_id}, ensure_ascii=False),
        ),
    )
    connection.execute(
        """
        INSERT INTO literature_documents (
            document_id, source_id, external_source, external_id, title,
            content_kind, full_text_status, metadata_json
        ) VALUES (?, ?, 'user_markdown', ?, ?, 'full_text', 'available', ?)
        ON CONFLICT(external_source, external_id) DO UPDATE SET
            source_id = excluded.source_id,
            title = excluded.title,
            content_kind = 'full_text',
            full_text_status = 'available',
            metadata_json = excluded.metadata_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            document_id,
            source_id,
            external_id,
            title,
            json.dumps({"research_brief_id": research_brief_id, "content_hash": digest}),
        ),
    )
    connection.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
    chunks = split_markdown(content)
    for index, chunk in enumerate(chunks):
        chunk_content = chunk["content"]
        connection.execute(
            """
            INSERT INTO document_chunks (
                chunk_id, document_id, section_title, section_path, chunk_index,
                content, content_hash, token_estimate, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _stable_id("chunk", f"{document_id}:{index}:{chunk_content}"),
                document_id,
                chunk["section_title"],
                chunk["section_path"],
                index,
                chunk_content,
                hashlib.sha256(chunk_content.encode("utf-8")).hexdigest(),
                max(1, len(chunk_content) // 4),
                json.dumps({"source_type": "user_markdown"}),
            ),
        )
    references = list(dict.fromkeys(
        raw.rstrip(".,;:")
        for raw in URL_RE.findall(content)
    ))
    source_record = {
        "source_id": source_id,
        "document_id": document_id,
        "title": title,
        "kind": "user_markdown",
        "content_hash": digest,
        "chunk_count": len(chunks),
        "reference_count": len(references),
        "references": references[:200],
        "source_uri": uri,
        "status": "ingested",
    }
    research_planner.append_source_material(connection, research_brief_id, source_record)
    return {
        **source_record,
        "sections": [
            {"title": chunk["section_title"], "path": chunk["section_path"]}
            for chunk in chunks
        ],
    }
