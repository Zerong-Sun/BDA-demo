from __future__ import annotations

import json
import shlex
import sqlite3
import uuid
from typing import Any

from ..repositories import catalog, research_planner, registry
from ..settings import get_settings

REFERENCE_SEED = {
    "title": "AI甜味蛋白_天然骨架_受体机制_计算设计与实验验证_2026-06-20",
    "version": "2026-06-20",
    "reference_count": 35,
    "verification_policy": (
        "Treat as a research seed. Verify recent papers, preprints, company claims, "
        "and regulatory status against primary or official sources."
    ),
}

SCAFFOLDS = [
    {
        "id": "single_chain_monellin",
        "name": "Single-chain monellin",
        "priority": 1,
        "route": "monellin_redesign",
        "length_aa": 97,
        "modeled_residues": 96,
        "chain_architecture": "engineered single chain",
        "uniprot": ["P02881", "P02882"],
        "pdb": ["2O9U"],
        "strengths": ["commercial/regulatory precedents", "single-chain engineering precedent", "high sweetness"],
        "risks": ["thermal/process stability", "aftertaste", "patent landscape"],
        "design_focus": ["fold stability", "linker", "secretion", "sensory profile"],
    },
    {
        "id": "brazzein_53",
        "name": "Brazzein-53/54",
        "priority": 2,
        "route": "brazzein_redesign",
        "length_aa": 54,
        "modeled_residues": 53,
        "chain_architecture": "single chain, four disulfide bonds",
        "uniprot": ["P56552"],
        "pdb": ["4HE7"],
        "strengths": ["small", "heat/acid tolerant", "receptor mutagenesis literature"],
        "risks": ["four disulfide pairs", "patent crowding", "correct oxidative folding"],
        "design_focus": ["surface residues", "disulfide preservation", "host compatibility"],
    },
    {
        "id": "thaumatin",
        "name": "Thaumatin",
        "priority": 3,
        "route": "thaumatin_benchmark",
        "strengths": ["mature industrial comparator", "flavor enhancement"],
        "risks": ["large protein", "long sweetness tail", "multiple disulfides"],
        "design_focus": ["benchmarking", "flavor modulation", "surface charge"],
    },
    {
        "id": "mabinlin_2",
        "name": "Mabinlin-2",
        "priority": 4,
        "route": "observation_only",
        "length_aa": [33, 72],
        "chain_architecture": "two mature chains",
        "uniprot": ["P30233"],
        "pdb": ["2DS2"],
        "strengths": ["heat-stability reference", "small individual chains"],
        "risks": ["two-chain architecture", "interchain disulfides"],
        "design_focus": ["stability mechanism reference"],
    },
    {
        "id": "curculin",
        "name": "Curculin-1/2",
        "priority": 5,
        "route": "ph_responsive_research",
        "length_aa": [114, 113],
        "chain_architecture": "dimeric mature proteins",
        "uniprot": ["P19667", "Q6F495"],
        "pdb": ["2DPF"],
        "strengths": ["taste-modifying activity", "pH-responsive research value"],
        "risks": ["exceeds 100 aa", "dimerization", "not a simple single-chain scaffold"],
        "design_focus": ["mechanism reference, not first-generation scaffold"],
    },
    {
        "id": "pentadin",
        "name": "Pentadin",
        "priority": 6,
        "route": "observation_only",
        "length_aa": None,
        "chain_architecture": "unresolved in current official database package",
        "uniprot": [],
        "pdb": [],
        "strengths": ["historical natural sweet-protein report"],
        "risks": ["no independently verified UniProt sequence or RCSB structure in current search"],
        "design_focus": ["primary-source sequence verification"],
    },
    {
        "id": "de_novo_receptor_binder",
        "name": "De novo TAS1R2/TAS1R3 binder",
        "priority": 5,
        "route": "de_novo_binder",
        "strengths": ["novel sequence space", "mechanism-led exploration"],
        "risks": ["binding does not prove activation", "no first-generation product evidence"],
        "design_focus": ["defined receptor epitope", "functional activation gate", "specificity"],
    },
]

ROUTES = [
    {
        "route_id": "monellin_redesign",
        "name": "Single-chain monellin 定向改造",
        "recommendation": "recommended",
        "generation": "first_generation",
        "rationale": "兼顾天然甜味、工程先例、生产路线与可改造空间。",
        "key_risks": ["热/加工稳定性", "后甜与异味", "FTO"],
    },
    {
        "route_id": "brazzein_redesign",
        "name": "Brazzein-53/54 定向改造",
        "recommendation": "recommended_parallel",
        "generation": "first_generation",
        "rationale": "小型、耐热耐酸，适合作为饮料应用的并行骨架。",
        "key_risks": ["二硫键正确形成", "专利拥挤", "表达宿主适配"],
    },
    {
        "route_id": "ph_responsive_research",
        "name": "pH-responsive 味觉修饰蛋白",
        "recommendation": "research_track",
        "generation": "second_generation",
        "rationale": "适合酸饮料等差异化场景，但生产和法规复杂度更高。",
        "key_risks": ["糖基化/多亚基", "酸依赖机制", "法规先例有限"],
    },
    {
        "route_id": "de_novo_binder",
        "name": "De novo 受体 binder",
        "recommendation": "high_risk",
        "generation": "second_generation",
        "rationale": "仅在受体区域、阳性对照和功能 assay 已定义时进入正式设计。",
        "key_risks": ["预测结合不等于受体激活", "表达与感官未验证", "高筛选成本"],
    },
]


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def create_brief(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    title: str,
    objective: str,
    product_context: str,
    constraints: dict[str, Any],
    source_material: list[dict[str, Any]],
    created_by: str,
) -> dict[str, Any]:
    assumptions = [
        {"key": "receptor_species", "value": "human", "status": "needs_confirmation"},
        {"key": "receptor", "value": "TAS1R2/TAS1R3", "status": "working_assumption"},
        {"key": "first_application", "value": "beverage", "status": "recommended_default"},
        {"key": "automation", "value": "confirm_each_compute_node", "status": "safe_default"},
    ]
    materials = []
    seen_materials: set[tuple[str, str]] = set()
    for material in [REFERENCE_SEED, *source_material]:
        identity = (str(material.get("title") or ""), str(material.get("kind") or "seed"))
        if identity in seen_materials:
            continue
        seen_materials.add(identity)
        materials.append(material)
    return research_planner.create_brief(
        connection,
        research_brief_id=_id("brief"),
        project_id=project_id,
        title=title,
        objective=objective,
        product_context=product_context,
        constraints=constraints,
        source_material=materials,
        assumptions=assumptions,
        created_by=created_by,
    )


def _findings(source_refs: list[str] | None = None) -> list[dict[str, Any]]:
    rows = [
        (
            "regulatory",
            "Regulatory precedents require official verification",
            "Modified monellin and brazzein have reported US GRAS precedents, but notice status, intended use, production organism, and conditions of use must be read from FDA records.",
            "Do not equate self-GRAS, submitted notices, and FDA no-questions letters.",
        ),
        (
            "natural_scaffolds",
            "First-generation scaffold priority",
            "Single-chain monellin and brazzein-53/54 are the default first-generation comparison; thaumatin is a benchmark, while pH-responsive proteins remain a research track.",
            "Final choice depends on product matrix, expression host, sensory target, and FTO.",
        ),
        (
            "receptor_mechanism",
            "Human receptor functional gate",
            "The working target is human TAS1R2/TAS1R3. Candidate binding or docking alone does not demonstrate receptor activation or perceived sweetness.",
            "Protein-specific contact regions and activation mechanisms require primary-evidence review.",
        ),
        (
            "design",
            "Prefer constrained redesign before de novo",
            "Preserve validated folds, disulfides, and functional residues during partial diffusion or sequence redesign. Treat de novo receptor binders as a high-risk second-generation route.",
            "Positive controls and a functional receptor assay must be defined before de novo execution.",
        ),
        (
            "experiments",
            "Evidence ladder",
            "Expression and folding, human receptor activation, sensory confirmation, food-matrix performance, process economics, safety, and regulatory evidence are separate gates.",
            "Animal taste behavior cannot substitute for human sensory evidence because of species differences.",
        ),
        (
            "manufacturing",
            "Design and fermentation must be co-optimized",
            "Rank candidates using effective sweetness titer: protein titer × correctly folded fraction × relative sweetness, rather than expression or docking score alone.",
            "The metric requires measured inputs and cannot be inferred from sequence alone.",
        ),
    ]
    return [
        {
            "research_finding_id": _id("finding"),
            "track": track,
            "title": title,
            "statement": statement,
            "evidence_level": "research_seed",
            "source_refs": source_refs or [REFERENCE_SEED["title"]],
            "uncertainty": uncertainty,
        }
        for track, title, statement, uncertainty in rows
    ]


def _rf_parameters(route_id: str) -> dict[str, Any]:
    de_novo = route_id == "de_novo_binder"
    scaffold = {
        "monellin_redesign": "single_chain_monellin",
        "brazzein_redesign": "brazzein_53",
        "ph_responsive_research": "ph_responsive",
    }.get(route_id)
    # For monellin, the input is prepared as natural chain B (A1-50) and
    # natural chain A (B1-44). Omitting a /0 chain break tells RFdiffusion to
    # emit one continuous chain, with a sampled 2-4 residue linker between the
    # two experimentally established motifs. The canonical MNEI linker is GF.
    contigs = {
        "single_chain_monellin": "[A1-50/2-4/B1-44]",
        # RCSB 4HE7 contains 53 modeled residues; the curated sequence is 54 aa.
        "brazzein_53": "[A1-53]",
        "ph_responsive": "",
    }.get(scaffold, "")
    partial_t = {
        # Variable-length linker motif scaffolding is not compatible with
        # partial diffusion's exact input/output length requirement.
        "single_chain_monellin": 0,
        # Keep the compact four-disulfide brazzein fold close to 4HE7.
        "brazzein_53": 5,
    }.get(scaffold, 0 if de_novo else 10)
    return {
        "design_mode": (
            "receptor_binder_de_novo"
            if de_novo
            else (
                "motif_scaffolding_with_linker"
                if scaffold == "single_chain_monellin"
                else "scaffold_partial_diffusion"
            )
        ),
        "scaffold": None if de_novo else scaffold,
        "inference.input_pdb": "",
        "contigmap.contigs": "[70-100]" if de_novo else contigs,
        "ppi.hotspot_res": "",
        "inference.num_designs": 1000 if de_novo else 100,
        "diffuser.partial_T": partial_t,
        "diffuser.T": 50,
        "denoiser.noise_scale_ca": 0.5 if not de_novo else 1.0,
        "denoiser.noise_scale_frame": 0.5 if not de_novo else 1.0,
        "contigmap.provide_seq": (
            # Zero-indexed modeled cysteine positions in 4HE7.
            "[2,14,20,24,35,45,47,50]"
            if scaffold == "brazzein_53"
            else ""
        ),
        "preserve_disulfides": scaffold == "brazzein_53",
        "linker_design": (
            {
                "input_chain_order": "natural chain B then natural chain A",
                "linker_length_range": [2, 4],
                "validated_reference_linker": "GF",
                "output_chain_count": 1,
            }
            if scaffold == "single_chain_monellin"
            else None
        ),
        "charge_design_guidance": {
            "stage": "ProteinMPNN_and_downstream_selection",
            "goal": "retain or enrich solvent-exposed positive patches without globally overcharging the protein",
            "warning": "RFdiffusion generates backbone geometry and does not optimize side-chain charge.",
        },
        "copilot_basis": "research_seed_pending_primary_source_verification",
        "requires_user_review": True,
    }


def build_workflow(route_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if route_id not in {item["route_id"] for item in ROUTES}:
        raise ValueError("unsupported_sweet_protein_route")
    if route_id == "ph_responsive_research":
        design_name = "pH-responsive scaffold redesign"
    elif route_id == "de_novo_binder":
        design_name = "De novo receptor binder generation"
    elif route_id == "monellin_redesign":
        design_name = "Monellin single-chain linker scaffolding"
    elif route_id == "brazzein_redesign":
        design_name = "Brazzein disulfide-preserving partial diffusion"
    else:
        design_name = "Constrained scaffold redesign"
    nodes = [
        {"key": "evidence", "node_type": "research_review", "name": "Evidence and assumption review", "resource": "manual", "initial_status": "requires_review", "parameters": {"review_gate": True}},
        {"key": "prepare", "node_type": "structure_preparation", "name": "Receptor and scaffold preparation", "resource": "manual", "initial_status": "requires_review", "parameters": {"receptor": "human TAS1R2/TAS1R3", "verify_structure_version": True}},
        {"key": "rf", "node_type": "backbone_generation", "name": design_name, "resource": "gpu", "model_name": "RFdiffusion", "parameters": _rf_parameters(route_id)},
        {"key": "mpnn", "node_type": "sequence_generation", "name": "ProteinMPNN sequence design", "resource": "gpu", "model_name": "ProteinMPNN", "parameters": {"num_seq_per_target": 8, "sampling_temp": "0.1 0.2", "omit_AAs": "CX", "preserve_functional_positions": True, "requires_user_review": True}},
        {"key": "fold", "node_type": "fold_prediction", "name": "Monomer and receptor-complex prediction", "resource": "gpu", "model_name": "AlphaFold2", "parameters": {"model_preset": "multimer", "models_to_relax": "none", "cross_validate_complex": True, "requires_user_review": True}},
        {"key": "rosetta", "node_type": "scoring", "name": "Rosetta stability and interface analysis", "resource": "cpu", "model_name": "Rosetta", "parameters": {"application": "rosetta_scripts", "nstruct": 3, "score:weights": "ref2015", "interface": "A_B", "requires_user_review": True}},
        {"key": "filter", "node_type": "selection", "name": "Developability, safety and diversity filters", "resource": "cpu", "parameters": {"check_disulfides": True, "allergenicity_screen": True, "aggregation_screen": True}},
        {"key": "review", "node_type": "review_gate", "name": "Design review gate", "resource": "manual", "parameters": {"binding_is_not_activation": True, "requires_human_receptor_assay_plan": True}},
        {"key": "experiment", "node_type": "experiment", "name": "Expandable experiment plan", "resource": "manual", "initial_status": "waiting_external_result", "parameters": {"stages": ["expression_and_folding", "receptor_function", "sensory", "food_matrix", "process", "safety_regulatory"]}},
    ]
    edges = [
        {"source": nodes[index]["key"], "target": nodes[index + 1]["key"], "edge_type": "review_gate" if index in {0, 6, 7} else "data"}
        for index in range(len(nodes) - 1)
    ]
    return nodes, edges


def generate_plan(
    connection: sqlite3.Connection,
    *,
    research_brief_id: str,
    selected_route: str | None,
    created_by: str,
) -> dict[str, Any]:
    brief = research_planner.get_brief(connection, research_brief_id)
    if brief is None:
        raise ValueError("research_brief_not_found")
    provisional_route = selected_route or "monellin_redesign"
    nodes, edges = build_workflow(provisional_route)
    llm_synthesis = None
    llm_error = None
    try:
        from .llm_planning_service import synthesize_sweet_protein_plan

        llm_synthesis = synthesize_sweet_protein_plan(
            connection,
            brief=brief,
            canonical_routes=ROUTES,
            canonical_scaffolds=SCAFFOLDS,
            canonical_nodes=nodes,
        )
    except Exception as exc:
        llm_error = str(exc)[:500]
    route_id = selected_route or (llm_synthesis or {}).get("selected_route") or provisional_route
    nodes, edges = build_workflow(route_id)
    if llm_synthesis:
        allowed_by_node = {
            node["key"]: set((node.get("parameters") or {}).keys())
            for node in nodes
        }
        for node in nodes:
            overrides = (
                (llm_synthesis.get("parameter_overrides") or {}).get(node["key"])
                if isinstance(llm_synthesis.get("parameter_overrides"), dict)
                else None
            )
            if not isinstance(overrides, dict):
                continue
            sanitized = {
                key: value
                for key, value in overrides.items()
                if key in allowed_by_node[node["key"]]
                and key.lower() not in {"command", "shell", "script"}
            }
            candidate = {**(node.get("parameters") or {}), **sanitized}
            if node["key"] == "rf" and not validate_rfdiffusion_parameters(candidate)["valid"]:
                continue
            node["parameters"] = candidate
    source_material = brief.get("source_material_json") or []
    source_refs = list(dict.fromkeys(
        str(item.get("title"))
        for item in source_material
        if item.get("title")
    ))
    findings = _findings(source_refs)
    research_planner.replace_findings(connection, research_brief_id, findings)
    route_options = [dict(item) for item in ROUTES]
    if llm_synthesis:
        assessments = {
            item.get("route_id"): item
            for item in (llm_synthesis.get("route_assessments") or [])
            if isinstance(item, dict)
        }
        for route in route_options:
            assessment = assessments.get(route["route_id"])
            if not assessment:
                continue
            for key in ("recommendation", "rationale", "key_risks"):
                if assessment.get(key):
                    route[key] = assessment[key]
            route["required_evidence"] = assessment.get("required_evidence") or []
            route["expected_benefits"] = assessment.get("expected_benefits") or []
    dossier = {
        "seed": REFERENCE_SEED,
        "scaffolds": SCAFFOLDS,
        "receptor": {
            "name": "human TAS1R2/TAS1R3",
            "regions": ["TAS1R2 VFD", "TAS1R2 CRD", "TAS1R3 CRD", "dimer interface"],
            "warning": "Predicted binding does not establish activation or sweetness.",
        },
        "verification_queue": [
            "FDA GRAS notice status and intended use",
            "2025 full-length human sweet receptor structures",
            "2026 allosteric-binding paper and de novo preprint",
            "UniProt sequences and PDB chain/construct mapping",
            "patent/FTO landscape",
        ],
        "source_reference_queue": [
            reference
            for item in source_material
            for reference in (item.get("references") or [])
        ],
        "experiment_gates": [
            "expression_and_correct_folding",
            "human_receptor_activation",
            "human_sensory_after_approval",
            "food_matrix_performance",
            "manufacturing_economics",
            "safety_and_regulatory",
        ],
        "assumptions": (llm_synthesis or {}).get("assumptions") or brief.get("assumptions_json") or [],
        "risks": (llm_synthesis or {}).get("risks") or [],
        "success_criteria": (llm_synthesis or {}).get("success_criteria") or [],
        "planning_summary": (llm_synthesis or {}).get("planning_summary"),
        "planning_provenance": {
            "mode": "llm_validated" if llm_synthesis else "deterministic_fallback",
            "model": get_settings().llm_model if llm_synthesis else None,
            "fallback_reason": llm_error,
            "guardrails": [
                "canonical_route_ids_only",
                "registered_models_only",
                "existing_parameter_keys_only",
                "trusted_script_renderer_only",
            ],
        },
    }
    if llm_synthesis and isinstance(llm_synthesis.get("receptor_synthesis"), dict):
        dossier["receptor"] = {
            **dossier["receptor"],
            **llm_synthesis["receptor_synthesis"],
            "warning": dossier["receptor"]["warning"],
        }
    if llm_synthesis and llm_synthesis.get("verification_queue"):
        dossier["verification_queue"] = llm_synthesis["verification_queue"]
    plan = research_planner.create_plan(
        connection,
        workflow_plan_id=_id("plan"),
        research_brief_id=research_brief_id,
        project_id=brief["project_id"],
        name=f"{brief['title']} · sweet protein workflow",
        selected_route=route_id,
        route_options=route_options,
        dossier=dossier,
        nodes=nodes,
        edges=edges,
        created_by=created_by,
    )
    _replace_parameter_recommendations(
        connection,
        plan["workflow_plan_id"],
        nodes,
        source_refs,
    )
    return plan


def materialize_plan(
    connection: sqlite3.Connection,
    *,
    workflow_plan_id: str,
    selected_route: str,
) -> dict[str, Any]:
    plan = research_planner.get_plan(connection, workflow_plan_id)
    if plan is None:
        raise ValueError("workflow_plan_not_found")
    if plan.get("materialized_workflow_run_id"):
        raise ValueError("workflow_plan_already_materialized")
    nodes, edges = build_workflow(selected_route)
    run = catalog.create_draft_workflow_run(connection, plan["project_id"])
    plugins = {item["model_name"]: item for item in registry.list_model_plugins(connection)}
    created: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        plugin = plugins.get(node.get("model_name"))
        created_node = catalog.add_workflow_node(
            connection,
            run["workflow_run_id"],
            node_type=node["node_type"],
            node_name=node["name"],
            model_name=node.get("model_name"),
            model_version=(plugin or {}).get("version"),
            parameters_json=json.dumps(node["parameters"], ensure_ascii=False),
            position_json=json.dumps({"x": 80 + (index % 3) * 300, "y": 100 + (index // 3) * 210}),
        )
        if node.get("initial_status"):
            created_node = catalog.update_workflow_node(
                connection,
                created_node["node_run_id"],
                status=node["initial_status"],
            ) or created_node
        created[node["key"]] = created_node
    materialized_edges = [
        {
            "source_node_run_id": created[edge["source"]]["node_run_id"],
            "target_node_run_id": created[edge["target"]]["node_run_id"],
            "source_port": "output",
            "target_port": "input",
            "edge_type": edge["edge_type"],
        }
        for edge in edges
    ]
    saved_edges = catalog.replace_workflow_edges(connection, run["workflow_run_id"], materialized_edges)
    research_planner.set_materialized(connection, workflow_plan_id, run["workflow_run_id"], selected_route)
    connection.execute(
        """
        INSERT OR IGNORE INTO run_automation_policies (
            automation_policy_id, workflow_run_id, mode, auto_submit_ready,
            notify_on_ready, notify_on_terminal, max_auto_retries,
            retry_backoff_seconds, created_by
        ) VALUES (?, ?, 'confirm_each_node', 0, 1, 1, 0, 60, ?)
        """,
        (_id("policy"), run["workflow_run_id"], plan.get("created_by")),
    )
    gate_nodes = [
        (key, node)
        for key, node in created.items()
        if node.get("node_type") in {"research_review", "review_gate"}
    ]
    for key, node in gate_nodes:
        connection.execute(
            """
            INSERT INTO decision_gates (
                decision_gate_id, workflow_plan_id, workflow_run_id, node_run_id,
                gate_type, name, criteria_json, status
            ) VALUES (?, ?, ?, ?, 'manual_review', ?, ?, 'pending')
            """,
            (
                _id("gate"),
                workflow_plan_id,
                run["workflow_run_id"],
                node["node_run_id"],
                node["node_name"],
                json.dumps([
                    {"criterion": "inputs reviewed", "required": True},
                    {"criterion": "assumptions and evidence boundaries accepted", "required": True},
                ]),
            ),
        )
    experiment_node = created.get("experiment")
    experiment_plan = None
    if experiment_node:
        from .experiment_planner_service import build_experiment_plan

        experiment_plan = build_experiment_plan(
            connection,
            workflow_plan_id=workflow_plan_id,
            workflow_run_id=run["workflow_run_id"],
            node_run_id=experiment_node["node_run_id"],
            created_by=plan.get("created_by") or "system",
        )
    return {
        "workflow_plan_id": workflow_plan_id,
        "workflow_run_id": run["workflow_run_id"],
        "selected_route": selected_route,
        "nodes": list(created.values()),
        "edges": saved_edges,
        "experiment_plan_id": (experiment_plan or {}).get("experiment_plan_id"),
    }


RF_ALLOWED_PARAMETERS = {
    "contigmap.contigs",
    "ppi.hotspot_res",
    "inference.num_designs",
    "diffuser.partial_T",
    "diffuser.T",
    "denoiser.noise_scale_ca",
    "denoiser.noise_scale_frame",
    "contigmap.inpaint_seq",
    "contigmap.inpaint_str",
    "contigmap.provide_seq",
    "inference.ckpt_override_path",
    "inference.symmetry",
    "potentials.guiding_potentials",
    "potentials.guide_scale",
}

RF_PARAMETER_RULES: dict[str, dict[str, Any]] = {
    "contigmap.contigs": {"type": "string", "required": True},
    "ppi.hotspot_res": {"type": "string"},
    "inference.num_designs": {"type": "integer", "min": 1, "max": 100000},
    "diffuser.partial_T": {"type": "integer", "min": 0, "max": 50},
    "diffuser.T": {"type": "integer", "min": 1, "max": 200},
    "denoiser.noise_scale_ca": {"type": "number", "min": 0, "max": 5},
    "denoiser.noise_scale_frame": {"type": "number", "min": 0, "max": 5},
    "contigmap.inpaint_seq": {"type": "string"},
    "contigmap.inpaint_str": {"type": "string"},
    "contigmap.provide_seq": {"type": "string"},
    "inference.ckpt_override_path": {"type": "string"},
    "inference.symmetry": {"type": "string"},
    "potentials.guiding_potentials": {"type": "json"},
    "potentials.guide_scale": {"type": "number", "min": 0, "max": 20},
}


def validate_rfdiffusion_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    for key, rule in RF_PARAMETER_RULES.items():
        value = parameters.get(key)
        if rule.get("required") and (value is None or value == ""):
            errors.append({"parameter": key, "message": "Required parameter is missing."})
            continue
        if value is None or value == "":
            continue
        expected_type = rule["type"]
        valid_type = (
            expected_type == "string" and isinstance(value, str)
        ) or (
            expected_type == "integer"
            and isinstance(value, int)
            and not isinstance(value, bool)
        ) or (
            expected_type == "number"
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        ) or (
            expected_type == "json"
            and isinstance(value, (str, list, dict))
        )
        if not valid_type:
            errors.append({
                "parameter": key,
                "message": f"Expected {expected_type}.",
            })
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "min" in rule and value < rule["min"]:
                errors.append({"parameter": key, "message": f"Must be >= {rule['min']}."})
            if "max" in rule and value > rule["max"]:
                errors.append({"parameter": key, "message": f"Must be <= {rule['max']}."})
    ignored = sorted(
        key for key in parameters
        if key not in RF_ALLOWED_PARAMETERS
        and key not in {
            "design_mode",
            "scaffold",
            "preserve_disulfides",
            "linker_design",
            "charge_design_guidance",
            "copilot_basis",
            "requires_user_review",
            "inference.input_pdb",
            "inference.output_prefix",
        }
    )
    for key in ("inference.input_pdb", "inference.output_prefix"):
        if parameters.get(key):
            warnings.append({
                "parameter": key,
                "message": "Value is platform-managed from staged artifacts/output workspace.",
            })
    for key in ignored:
        warnings.append({
            "parameter": key,
            "message": "Parameter is not part of the trusted RFdiffusion command allowlist.",
        })
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def render_rfdiffusion_command(parameters: dict[str, Any]) -> str:
    validation = validate_rfdiffusion_parameters(parameters)
    if not validation["valid"]:
        detail = ";".join(
            f"{item['parameter']}:{item['message']}"
            for item in validation["errors"]
        )
        raise ValueError(f"invalid_rfdiffusion_parameters:{detail}")
    command = ["python", "/opt/RFdiffusion/scripts/run_inference.py"]
    command.append("inference.input_pdb=/input/<staged-target-structure>")
    for key in sorted(RF_ALLOWED_PARAMETERS):
        value = parameters.get(key)
        if value is None or value == "":
            continue
        if isinstance(value, (list, dict)):
            rendered = json.dumps(value, separators=(",", ":"))
        elif isinstance(value, bool):
            rendered = "true" if value else "false"
        else:
            rendered = str(value)
        command.append(f"{key}={rendered}")
    command.append("inference.output_prefix=output/design")
    return " ".join(shlex.quote(token) for token in command)


def _replace_parameter_recommendations(
    connection: sqlite3.Connection,
    workflow_plan_id: str,
    nodes: list[dict[str, Any]],
    source_refs: list[str],
) -> None:
    connection.execute(
        "DELETE FROM parameter_recommendations WHERE workflow_plan_id = ?",
        (workflow_plan_id,),
    )
    plugin_by_name = {
        item["model_name"]: item
        for item in registry.list_model_plugins(connection)
    }
    for node in nodes:
        model_name = node.get("model_name")
        if not model_name:
            continue
        plugin = plugin_by_name.get(model_name) or {}
        fields = (plugin.get("parameter_schema_json") or {}).get("fields", [])
        fields_by_key = {field.get("key"): field for field in fields}
        for key, value in (node.get("parameters") or {}).items():
            field = fields_by_key.get(key) or {}
            if key in {
                "copilot_basis",
                "requires_user_review",
                "design_mode",
                "scaffold",
                "linker_design",
                "charge_design_guidance",
                "preserve_disulfides",
            }:
                continue
            recommended_range = {
                k: field[k] for k in ("min", "max", "options") if k in field
            }
            connection.execute(
                """
                INSERT INTO parameter_recommendations (
                    parameter_recommendation_id, workflow_plan_id, node_key,
                    model_name, parameter_key, recommended_value_json,
                    default_value_json, recommended_range_json, source_refs_json,
                    rationale, confidence, validation_rules_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _id("paramrec"),
                    workflow_plan_id,
                    node["key"],
                    model_name,
                    key,
                    json.dumps(value, ensure_ascii=False),
                    json.dumps(field.get("default"), ensure_ascii=False),
                    json.dumps(recommended_range, ensure_ascii=False),
                    json.dumps(source_refs, ensure_ascii=False),
                    field.get("help") or "Copilot workflow-template recommendation.",
                    "template_inferred",
                    json.dumps(recommended_range, ensure_ascii=False),
                ),
            )
