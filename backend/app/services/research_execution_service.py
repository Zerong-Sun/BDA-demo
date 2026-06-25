from __future__ import annotations

import sqlite3
import uuid
from typing import Any, Callable

from ..copilot import research
from ..repositories import research_execution, research_planner


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


QUESTION_TEMPLATES = [
    {
        "track": "regulatory",
        "question": "What official regulatory precedents exist for modified monellin and brazzein?",
        "query": {"kind": "regulatory", "identifiers": ["GRN 1142", "GRN 1183", "GRN 1207", "GRN 1269"]},
        "priority": 10,
    },
    {
        "track": "natural_scaffolds",
        "question": "Which natural sweet proteins have reviewed sequence and structure records?",
        "query": {"kind": "uniprot", "terms": ["monellin", "brazzein", "thaumatin", "mabinlin", "miraculin", "neoculin"]},
        "priority": 20,
    },
    {
        "track": "receptor_structure",
        "question": "Which experimental structures and publications describe human TAS1R2/TAS1R3?",
        "query": {"kind": "pdb_and_literature", "term": "human sweet taste receptor TAS1R2 TAS1R3"},
        "priority": 30,
    },
    {
        "track": "mechanism",
        "question": "What evidence supports protein-specific receptor contact regions and activation?",
        "query": {"kind": "literature", "term": "sweet protein TAS1R2 TAS1R3 activation brazzein monellin thaumatin"},
        "priority": 40,
    },
    {
        "track": "design_methods",
        "question": "Which computational design methods and measured parameters were used for sweet proteins?",
        "query": {"kind": "literature", "term": "computational design sweet protein monellin RFdiffusion ProteinMPNN"},
        "priority": 50,
    },
    {
        "track": "experiments",
        "question": "Which experimental gates distinguish binding, receptor activation, sensory sweetness, and safety?",
        "query": {"kind": "literature", "term": "sweet protein receptor assay sensory safety evaluation"},
        "priority": 60,
    },
]

OFFICIAL_GRAS = [
    ("GRN 1142", "Brazzein produced by Komagataella phaffii", "https://www.cfsanappsexternal.fda.gov/scripts/fdcc/?id=1142&set=GRASNotices"),
    ("GRN 1183", "Modified monellin produced by Komagataella phaffii", "https://www.hfpappexternal.fda.gov/scripts/fdcc/index.cfm?id=1183&set=GRASNotices"),
    ("GRN 1207", "Brazzein preparation produced by Aspergillus oryzae", "https://www.hfpappexternal.fda.gov/scripts/fdcc/index.cfm?id=1207&set=grasnotices"),
    ("GRN 1269", "Modified monellin sweet protein", "https://www.hfpappexternal.fda.gov/scripts/fdcc/index.cfm?id=1269&set=GRASNotices"),
]


def ensure_questions(connection: sqlite3.Connection, research_brief_id: str) -> list[dict[str, Any]]:
    existing = research_execution.list_questions(connection, research_brief_id)
    if existing:
        return existing
    templates = QUESTION_TEMPLATES
    brief = research_planner.get_brief(connection, research_brief_id)
    if brief is not None:
        try:
            from .llm_planning_service import decompose_research_questions

            templates = decompose_research_questions(brief) or templates
        except Exception:
            templates = QUESTION_TEMPLATES
    return research_execution.replace_questions(
        connection,
        research_brief_id,
        [
            {"research_question_id": _id("question"), **item}
            for item in templates
        ],
    )


def _evidence(
    question_id: str,
    *,
    source_type: str,
    title: str,
    identifier: str | None = None,
    uri: str | None = None,
    excerpt: str | None = None,
    level: str = "metadata",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "evidence_link_id": _id("evidence"),
        "research_question_id": question_id,
        "source_type": source_type,
        "source_identifier": identifier,
        "title": title,
        "uri": uri,
        "evidence_excerpt": excerpt,
        "evidence_level": level,
        "metadata": metadata or {},
        "applicability": {"requires_human_review": True},
    }


def execute_research_run(
    connection: sqlite3.Connection,
    research_run_id: str,
    *,
    search_literature_fn: Callable[..., dict[str, Any]] | None = None,
    search_pdb_fn: Callable[..., dict[str, Any]] | None = None,
    search_uniprot_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    search_literature_fn = search_literature_fn or research.search_literature
    search_pdb_fn = search_pdb_fn or research.search_pdb
    search_uniprot_fn = search_uniprot_fn or research.search_uniprot
    run = research_execution.get_run(connection, research_run_id)
    if run is None:
        raise ValueError("research_run_not_found")
    questions = ensure_questions(connection, run["research_brief_id"])
    research_execution.update_run(
        connection,
        research_run_id,
        status="running",
        progress={"completed": 0, "total": len(questions), "current_track": None},
    )
    evidence: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for index, question in enumerate(questions):
        query = question.get("query_json") or {}
        kind = query.get("kind")
        try:
            if kind == "regulatory":
                evidence.extend(
                    _evidence(
                        question["research_question_id"],
                        source_type="FDA_GRAS",
                        identifier=identifier,
                        title=title,
                        uri=uri,
                        excerpt="Official FDA GRAS notice record; status and conditions require review of the record.",
                        level="official_record",
                    )
                    for identifier, title, uri in OFFICIAL_GRAS
                )
            elif kind == "uniprot":
                for term in query.get("terms", []):
                    result = search_uniprot_fn(term, limit=3, reviewed_only=True)
                    evidence.extend(
                        _evidence(
                            question["research_question_id"],
                            source_type="UniProtKB",
                            identifier=item.get("accession"),
                            title=item.get("protein_name") or term,
                            uri=item.get("url"),
                            excerpt=(item.get("function_comments") or [None])[0],
                            level="curated_database",
                            metadata=item,
                        )
                        for item in result.get("results", [])
                    )
            elif kind == "pdb_and_literature":
                pdb_result = search_pdb_fn(query["term"], limit=5)
                evidence.extend(
                    _evidence(
                        question["research_question_id"],
                        source_type="RCSB_PDB",
                        identifier=item.get("pdb_id"),
                        title=item.get("title") or item.get("pdb_id") or "PDB structure",
                        uri=item.get("url"),
                        excerpt=item.get("experimental_method"),
                        level="experimental_structure",
                        metadata=item,
                    )
                    for item in pdb_result.get("results", [])
                )
                literature_result = search_literature_fn(query["term"], limit=5)
                evidence.extend(_literature_evidence(question["research_question_id"], literature_result))
            elif kind == "literature":
                evidence.extend(_literature_evidence(
                    question["research_question_id"],
                    search_literature_fn(query["term"], limit=8),
                ))
            connection.execute(
                "UPDATE research_questions SET status='completed', updated_at=CURRENT_TIMESTAMP WHERE research_question_id=?",
                (question["research_question_id"],),
            )
        except Exception as exc:  # partial research runs preserve successful tracks
            failures.append({"track": question["track"], "error": str(exc)[:300]})
            connection.execute(
                "UPDATE research_questions SET status='failed', updated_at=CURRENT_TIMESTAMP WHERE research_question_id=?",
                (question["research_question_id"],),
            )
        research_execution.update_run(
            connection,
            research_run_id,
            status="running",
            progress={
                "completed": index + 1,
                "total": len(questions),
                "current_track": question["track"],
            },
        )
    research_execution.replace_evidence(connection, research_run_id, evidence)
    hypotheses = _hypotheses(run["research_brief_id"], evidence)
    synthesis = None
    brief = research_planner.get_brief(connection, run["research_brief_id"])
    if brief is not None:
        try:
            from .llm_planning_service import synthesize_research_evidence

            synthesis = synthesize_research_evidence(brief=brief, evidence=evidence)
        except Exception as exc:
            failures.append({"track": "evidence_synthesis", "error": str(exc)[:300]})
    if synthesis:
        valid_evidence_ids = {item["evidence_link_id"] for item in evidence}
        synthesized_findings = []
        for item in (synthesis.get("findings") or [])[:30]:
            if not isinstance(item, dict) or not item.get("title") or not item.get("statement"):
                continue
            refs = [
                evidence_id for evidence_id in (item.get("evidence_link_ids") or [])
                if evidence_id in valid_evidence_ids
            ]
            synthesized_findings.append({
                "research_finding_id": _id("finding"),
                "track": str(item.get("track") or "synthesis")[:80],
                "title": str(item["title"])[:240],
                "statement": str(item["statement"])[:4000],
                "evidence_level": str(item.get("evidence_level") or "llm_synthesis")[:80],
                "source_refs": refs,
                "uncertainty": str(item.get("uncertainty") or "")[:1000],
            })
        if synthesized_findings:
            research_planner.replace_findings(
                connection,
                run["research_brief_id"],
                synthesized_findings,
            )
        synthesized_hypotheses = []
        for item in (synthesis.get("hypotheses") or [])[:20]:
            if not isinstance(item, dict) or not item.get("hypothesis"):
                continue
            synthesized_hypotheses.append({
                "design_hypothesis_id": _id("hypothesis"),
                "research_brief_id": run["research_brief_id"],
                "hypothesis": str(item["hypothesis"])[:4000],
                "rationale": str(item.get("rationale") or "")[:4000],
                "falsification_test": str(item.get("falsification_test") or "")[:4000],
                "evidence_link_ids": [
                    evidence_id for evidence_id in (item.get("evidence_link_ids") or [])
                    if evidence_id in valid_evidence_ids
                ],
                "confidence": (
                    item.get("confidence")
                    if item.get("confidence") in {"low", "medium", "high"}
                    else "medium"
                ),
            })
        if synthesized_hypotheses:
            hypotheses = synthesized_hypotheses
    research_execution.replace_hypotheses(connection, run["research_brief_id"], hypotheses)
    terminal_status = "partial" if failures else "completed"
    return research_execution.update_run(
        connection,
        research_run_id,
        status=terminal_status,
        progress={"completed": len(questions), "total": len(questions), "current_track": None},
        result_summary={
            "evidence_count": len(evidence),
            "source_types": sorted({item["source_type"] for item in evidence}),
            "failures": failures,
            "hypothesis_count": len(hypotheses),
            "synthesis_mode": "llm_validated" if synthesis else "deterministic_fallback",
            "conflicts": (synthesis or {}).get("conflicts") or [],
            "unresolved_questions": (synthesis or {}).get("unresolved_questions") or [],
        },
        error_message="; ".join(item["error"] for item in failures) if failures else None,
    ) or {}


def _literature_evidence(question_id: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _evidence(
            question_id,
            source_type="Europe_PMC",
            identifier=item.get("doi") or item.get("pmid") or item.get("identifier"),
            title=item.get("title") or "Literature record",
            uri=item.get("url"),
            excerpt=item.get("abstract"),
            level="abstract" if item.get("abstract") else "metadata",
            metadata={
                "year": item.get("year"),
                "doi": item.get("doi"),
                "pmid": item.get("pmid"),
                "pmcid": item.get("pmcid"),
                "is_open_access": item.get("is_open_access"),
            },
        )
        for item in result.get("results", [])
    ]


def _hypotheses(research_brief_id: str, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence_ids = [item["evidence_link_id"] for item in evidence[:20]]
    return [
        {
            "design_hypothesis_id": _id("hypothesis"),
            "research_brief_id": research_brief_id,
            "hypothesis": "Constrained redesign of a validated sweet-protein fold is more likely to preserve function than unconstrained de novo design.",
            "rationale": "Natural sweetness and fold are known; stability, expression, and surface properties remain design variables.",
            "falsification_test": "Compare matched scaffold-redesign and de novo candidates in expression, folding, and human TAS1R2/TAS1R3 activation assays.",
            "evidence_link_ids": evidence_ids,
            "confidence": "medium",
        },
        {
            "design_hypothesis_id": _id("hypothesis"),
            "research_brief_id": research_brief_id,
            "hypothesis": "Predicted receptor binding is insufficient as a sweetness gate.",
            "rationale": "Binding, receptor activation, and sensory perception are distinct evidence levels.",
            "falsification_test": "Require dose-response receptor activation followed by approved sensory evaluation.",
            "evidence_link_ids": evidence_ids,
            "confidence": "high",
        },
    ]


def create_and_start_run(
    connection: sqlite3.Connection,
    *,
    research_brief_id: str,
    created_by: str,
) -> dict[str, Any]:
    if research_planner.get_brief(connection, research_brief_id) is None:
        raise ValueError("research_brief_not_found")
    ensure_questions(connection, research_brief_id)
    run = research_execution.create_run(
        connection,
        research_run_id=_id("research_run"),
        research_brief_id=research_brief_id,
        created_by=created_by,
    )
    return execute_research_run(connection, run["research_run_id"])
