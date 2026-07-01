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
    {
        "knowledge_entry_id": "kb_route_planning",
        "title": "Knowledge-guided workflow route planning",
        "category": "workflow",
        "subcategory": "route_selection",
        "summary": "Choose workflow routes by design objective, evidence quality, available target context, and validation needs.",
        "content": (
            "A route planner should first summarize the project target, objective, constraints, and available evidence. "
            "It should then compare candidate routes, explain why each route fits, list required model modules, and keep "
            "route selection separate from script generation. Users should be able to choose one route and optionally "
            "disable modules before the system creates workflow nodes or scripts."
        ),
        "tags": ["workflow", "route", "planner", "modules", "knowledge"],
    },
    {
        "knowledge_entry_id": "kb_insecticidal_protein_design",
        "title": "Insecticidal protein design route boundaries",
        "category": "application",
        "subcategory": "insecticidal_protein",
        "summary": "Insecticidal protein projects need explicit pest species, target biology, specificity, safety, and assay plans.",
        "content": (
            "For an insecticidal or anti-pest protein project, distinguish computational protein generation from claims "
            "about biological activity. The project should name the pest species, intended exposure route, putative target "
            "or gut receptor, specificity requirements, crop or formulation context, environmental safety assumptions, "
            "and planned in vitro or in vivo assays. De novo generation can propose structures and sequences, but activity, "
            "toxicity spectrum, off-target effects, and durability require controlled experimental validation."
        ),
        "tags": ["insect", "antipest", "抗虫", "specificity", "assay", "safety"],
    },
    {
        "knowledge_entry_id": "kb_model_module_chain",
        "title": "Protein design model module chain",
        "category": "workflow",
        "subcategory": "model_modules",
        "summary": "Common protein routes chain generation, sequence design, folding, scoring, filtering, and validation modules.",
        "content": (
            "A typical de novo protein design route uses a structure generator such as RFdiffusion, a sequence designer "
            "such as ProteinMPNN, a fold or complex predictor such as AlphaFold2, AlphaFold3, Boltz, or Chai-1, and an "
            "energy or interface scoring step such as Rosetta. Route plans should record module plugin IDs, expected inputs "
            "and outputs, parameter assumptions, and downstream script-preview readiness so the workflow graph remains auditable."
        ),
        "tags": ["RFdiffusion", "ProteinMPNN", "AlphaFold", "Rosetta", "modules", "script"],
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
