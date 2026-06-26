from __future__ import annotations

import json
import sqlite3

ENTRIES = [
    {
        "knowledge_entry_id": "kb_evidence_hierarchy",
        "title": "Evidence hierarchy for protein design decisions",
        "category": "methodology",
        "subcategory": "evidence",
        "summary": "Separate experimental evidence, curated database records, computational predictions, and design hypotheses.",
        "content": (
            "For protein design decisions, report evidence provenance. Experimental structures and measured "
            "binding or biophysical data should be identified separately from AlphaFold confidence, docking, "
            "Rosetta energies, language-model scores, and sequence heuristics. A predicted interaction or pathway "
            "effect is a hypothesis until supported by suitable biochemical, cellular, or in vivo evidence."
        ),
        "tags": ["evidence", "experimental", "prediction", "validation", "uncertainty"],
    },
    {
        "knowledge_entry_id": "kb_pdb_selection",
        "title": "Selecting PDB structures for protein design",
        "category": "methodology",
        "subcategory": "structure_selection",
        "summary": "Select PDB templates by biological state, construct, ligand, resolution, chain completeness, and experimental context.",
        "content": (
            "Do not select a PDB template by resolution alone. Check organism and construct, mutations, missing "
            "regions, oligomeric state, ligand or partner state, pH and experimental method, biological assembly, "
            "interface relevance, and whether the structure captures the intended active, inactive, open, or closed state."
        ),
        "tags": ["PDB", "template", "resolution", "assembly", "conformation"],
    },
    {
        "knowledge_entry_id": "kb_literature_synthesis",
        "title": "Literature synthesis for programmable biomaterials",
        "category": "methodology",
        "subcategory": "literature",
        "summary": "Build literature answers from traceable sources and separate reported findings from synthesis.",
        "content": (
            "A literature response should give identifiers and links, summarize the model system and methods, "
            "state the reported result, identify limitations, and then explain how it may affect the BDA design "
            "route. Abstract-only evidence must be labeled as such. Full text should only be used when openly available."
        ),
        "tags": ["literature", "citation", "DOI", "PMID", "review"],
    },
    {
        "knowledge_entry_id": "kb_pathway_reasoning",
        "title": "Pathway and protein-function reasoning",
        "category": "methodology",
        "subcategory": "pathway",
        "summary": "Pathway claims depend on organism, cell type, molecular state, directionality, and evidence type.",
        "content": (
            "When describing pathways, name the protein species or isoform, organism, cellular compartment, "
            "upstream and downstream relationships, activation or inhibition direction, and the evidence supporting "
            "each edge. Binding does not automatically imply pathway activation, and overexpression phenotypes may "
            "not represent physiological function."
        ),
        "tags": ["pathway", "signaling", "function", "mechanism", "context"],
    },
    {
        "knowledge_entry_id": "kb_sequence_properties",
        "title": "Sequence-only protein property screening",
        "category": "biomaterial_property",
        "subcategory": "sequence",
        "summary": "Sequence descriptors are useful filters but cannot replace structural prediction or experiments.",
        "content": (
            "Length, molecular weight, charge proxies, hydrophobic fraction, aromatic content, cysteine count, "
            "and extinction estimates can flag obvious liabilities. They do not directly establish solubility, "
            "fold stability, expression yield, aggregation, affinity, immunogenicity, or biological activity."
        ),
        "tags": ["sequence", "molecular_weight", "charge", "hydrophobicity", "screening"],
    },
]


def register_default_knowledge(connection: sqlite3.Connection) -> None:
    for entry in ENTRIES:
        connection.execute(
            """
            INSERT INTO knowledge_entries (
                knowledge_entry_id, title, category, subcategory, summary, content,
                tags_json, related_model_plugins, related_method_plugins, source_type,
                citation, confidence, metadata_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, '[]', '[]', 'curated', ?, 'curated', '{}', 'active')
            ON CONFLICT(knowledge_entry_id) DO UPDATE SET
                title=excluded.title,
                category=excluded.category,
                subcategory=excluded.subcategory,
                summary=excluded.summary,
                content=excluded.content,
                tags_json=excluded.tags_json,
                citation=excluded.citation,
                status='active',
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                entry["knowledge_entry_id"],
                entry["title"],
                entry["category"],
                entry["subcategory"],
                entry["summary"],
                entry["content"],
                json.dumps(entry["tags"]),
                "BDA curated operating guidance.",
            ),
        )
