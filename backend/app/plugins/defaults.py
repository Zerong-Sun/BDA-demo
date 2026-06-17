from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from typing import Any


def _port(name: str, artifact_types: list[str], *, required: bool = True, many: bool = False, help: str = "") -> dict:
    return {
        "name": name,
        "artifact_types": artifact_types,
        "required": required,
        "many": many,
        "help": help,
    }


def _field(
    key: str,
    label: str,
    field_type: str,
    default: Any,
    help: str,
    *,
    advanced: bool = False,
    minimum: int | float | None = None,
    maximum: int | float | None = None,
    options: list[str] | None = None,
) -> dict:
    field = {
        "key": key,
        "label": label,
        "type": field_type,
        "default": default,
        "help": help,
        "advanced": advanced,
    }
    if minimum is not None:
        field["min"] = minimum
    if maximum is not None:
        field["max"] = maximum
    if options is not None:
        field["options"] = options
    return field


DEFAULT_MODEL_PLUGINS: list[dict[str, Any]] = [
    {
        "model_plugin_id": "plugin_rfdiffusion",
        "model_name": "RFdiffusion",
        "model_type": "backbone_generation",
        "provider": "open_source",
        "version": "1.1.0",
        "description": "Backbone generation for binder geometry with contig, hotspot, length, symmetry, and sampling controls.",
        "input_schema_json": {
            "ports": [
                _port("target_structure", ["target_structure", "cleaned_structure"], help="Target PDB/mmCIF artifact."),
                _port("contig_map", ["contig_map", "constraints"], required=False, help="RFdiffusion contig mapping constraints."),
                _port("hotspot_residues", ["constraints"], required=False, help="Residue hotspot constraints."),
            ]
        },
        "output_schema_json": {
            "ports": [
                _port("backbone_set", ["backbone_set"], many=True, help="Generated backbone structures."),
                _port("score_table", ["score_table"], required=False, help="Sampling scores and metadata."),
                _port("run_manifest", ["manifest"], help="Machine-readable output manifest."),
            ]
        },
        "parameter_schema_json": {
            "fields": [
                _field("num_designs", "Number of designs", "integer", 100, "Number of backbones to sample.", minimum=1, maximum=100000),
                _field("contig_map", "Contig map", "string", "", "RFdiffusion contig string, for example [A1-120/0 80-120]."),
                _field("hotspot_residues", "Hotspot residues", "string", "", "Comma-separated target residues to bias interface contacts."),
                _field("binder_length_min", "Binder length min", "integer", 60, "Minimum binder length.", minimum=1, maximum=2000),
                _field("binder_length_max", "Binder length max", "integer", 120, "Maximum binder length.", minimum=1, maximum=2000),
                _field("diffusion_steps", "Diffusion steps", "integer", 50, "Number of denoising steps.", advanced=True, minimum=1, maximum=500),
                _field("noise_scale_ca", "CA noise scale", "number", 1.0, "Coordinate noise scale for CA atoms.", advanced=True, minimum=0, maximum=5),
                _field("noise_scale_frame", "Frame noise scale", "number", 1.0, "Frame noise scale.", advanced=True, minimum=0, maximum=5),
                _field("symmetry", "Symmetry", "enum", "none", "Optional symmetry mode.", advanced=True, options=["none", "cyclic", "dihedral", "tetrahedral"]),
                _field("random_seed", "Random seed", "integer", 0, "Zero means auto-generate seed.", advanced=True, minimum=0),
            ]
        },
        "artifact_schema_json": {"outputs": [{"type": "backbone_set", "formats": ["pdb", "mmcif", "zip"]}, {"type": "score_table", "formats": ["csv", "json"]}]},
        "supported_task_types": ["binder_design", "scaffold_generation", "nanocage_design"],
        "supported_file_types": ["pdb", "mmcif", "json", "txt"],
        "resource_requirement_json": {"gpu_count": 1, "min_vram_gb": 24, "cpu_count": 8, "memory_gb": 32, "runtime_env": {"BDA_GPU": "1"}},
        "default_compute_node_id": "compute_gpu_local",
        "container_image": "bda/rfdiffusion:1.1.0",
        "command_template": "python run.py",
        "api_endpoint": None,
        "license": "BSD-style / upstream dependent",
        "citation": "RFdiffusion upstream citation TBD",
        "status": "active",
    },
    {
        "model_plugin_id": "plugin_proteinmpnn",
        "model_name": "ProteinMPNN",
        "model_type": "sequence_generation",
        "provider": "open_source",
        "version": "1.0.0",
        "description": "Sequence design for fixed or generated backbones with chain, residue, amino-acid omission, and sampling controls.",
        "input_schema_json": {
            "ports": [
                _port("backbone_set", ["backbone_set", "structure", "cleaned_structure"], help="Backbone structures to sequence-design."),
                _port("fixed_positions", ["constraints"], required=False, help="Residues that must not mutate."),
                _port("bias_json", ["constraints"], required=False, help="Optional amino-acid bias configuration."),
            ]
        },
        "output_schema_json": {
            "ports": [
                _port("sequence_set", ["sequence_set"], many=True, help="Designed sequences in FASTA/CSV form."),
                _port("score_table", ["score_table"], help="Sequence design scores."),
                _port("run_manifest", ["manifest"], help="Machine-readable output manifest."),
            ]
        },
        "parameter_schema_json": {
            "fields": [
                _field("num_seq_per_target", "Sequences per target", "integer", 8, "Number of sequences sampled per backbone.", minimum=1, maximum=10000),
                _field("sampling_temperature", "Sampling temperature", "number", 0.1, "Higher values increase diversity and risk.", minimum=0, maximum=2),
                _field("designed_chains", "Designed chains", "string", "", "Comma-separated chains to design. Empty means infer from input."),
                _field("fixed_positions", "Fixed positions", "string", "", "Residues to keep fixed, for example A:10,A:11."),
                _field("omit_aas", "Omit amino acids", "string", "X", "Amino acids excluded from sampling."),
                _field("backbone_noise", "Backbone noise", "number", 0.0, "Optional backbone perturbation.", advanced=True, minimum=0, maximum=1),
                _field("random_seed", "Random seed", "integer", 0, "Zero means auto-generate seed.", advanced=True, minimum=0),
            ]
        },
        "artifact_schema_json": {"outputs": [{"type": "sequence_set", "formats": ["fasta", "csv"]}, {"type": "score_table", "formats": ["csv", "json"]}]},
        "supported_task_types": ["binder_design", "scaffold_redesign", "enzyme_repair"],
        "supported_file_types": ["pdb", "mmcif", "fasta", "json"],
        "resource_requirement_json": {"gpu_count": 1, "cpu_fallback": True, "cpu_count": 8, "memory_gb": 16, "runtime_env": {"BDA_GPU": "1"}},
        "default_compute_node_id": "compute_gpu_local",
        "container_image": "bda/proteinmpnn:1.0.0",
        "command_template": "python run.py",
        "api_endpoint": None,
        "license": "MIT / upstream dependent",
        "citation": "ProteinMPNN upstream citation TBD",
        "status": "active",
    },
    {
        "model_plugin_id": "plugin_alphafold2",
        "model_name": "AlphaFold2",
        "model_type": "fold_prediction",
        "provider": "open_source",
        "version": "2.3.0",
        "description": "Structure and complex prediction with confidence metrics such as pLDDT, pTM, ipTM, and interface PAE.",
        "input_schema_json": {
            "ports": [
                _port("sequence_set", ["sequence_set"], help="FASTA/sequence set for prediction."),
                _port("target_structure", ["target_structure", "cleaned_structure"], required=False, help="Optional target structure for complex workflows."),
                _port("pairing_config", ["constraints"], required=False, help="Optional chain pairing configuration."),
            ]
        },
        "output_schema_json": {
            "ports": [
                _port("predicted_structure", ["predicted_structure"], many=True, help="Predicted model structures."),
                _port("complex_structure", ["complex_structure"], required=False, many=True, help="Predicted complexes."),
                _port("score_table", ["score_table"], help="Confidence metrics."),
                _port("pae_matrix", ["pae_matrix"], required=False, help="PAE matrix artifact."),
            ]
        },
        "parameter_schema_json": {
            "fields": [
                _field("model_preset", "Model preset", "enum", "multimer", "AlphaFold model preset.", options=["monomer", "monomer_ptm", "multimer"]),
                _field("num_recycles", "Recycle count", "integer", 3, "Number of recycling iterations.", minimum=1, maximum=48),
                _field("msa_mode", "MSA mode", "enum", "reduced_dbs", "Database/MSA strategy.", options=["full_dbs", "reduced_dbs", "single_sequence"]),
                _field("template_mode", "Template mode", "enum", "none", "Template usage mode.", advanced=True, options=["none", "pdb70", "custom"]),
                _field("pairing_strategy", "Pairing strategy", "enum", "paired", "Multimer sequence pairing strategy.", advanced=True, options=["paired", "unpaired", "paired_plus_unpaired"]),
                _field("max_template_date", "Max template date", "string", "2026-01-01", "Template cutoff date.", advanced=True),
                _field("random_seed", "Random seed", "integer", 0, "Zero means auto-generate seed.", advanced=True, minimum=0),
            ]
        },
        "artifact_schema_json": {"outputs": [{"type": "predicted_structure", "formats": ["pdb", "mmcif"]}, {"type": "score_table", "formats": ["csv", "json"]}, {"type": "pae_matrix", "formats": ["json"]}]},
        "supported_task_types": ["binder_design", "scaffold_redesign", "nanocage_design", "enzyme_repair"],
        "supported_file_types": ["fasta", "pdb", "mmcif", "json"],
        "resource_requirement_json": {"gpu_count": 1, "min_vram_gb": 32, "cpu_count": 8, "memory_gb": 64, "database_ssd": True, "runtime_env": {"BDA_GPU": "1"}},
        "default_compute_node_id": "compute_gpu_local",
        "container_image": "bda/alphafold2:2.3.0",
        "command_template": "python run.py",
        "api_endpoint": None,
        "license": "Apache-2.0 / database terms apply",
        "citation": "AlphaFold upstream citation TBD",
        "status": "active",
    },
    {
        "model_plugin_id": "plugin_rosetta",
        "model_name": "Rosetta",
        "model_type": "scoring",
        "provider": "open_source",
        "version": "2024.09",
        "description": "Relax, interface scoring, ddG estimation, clash checks, buried SASA, and developability-adjacent metrics.",
        "input_schema_json": {
            "ports": [
                _port("complex_structure", ["complex_structure", "predicted_structure", "structure"], help="Complex or structure to score."),
                _port("score_config", ["constraints"], required=False, help="Optional scoring protocol configuration."),
            ]
        },
        "output_schema_json": {
            "ports": [
                _port("relaxed_structure", ["relaxed_structure"], required=False, many=True, help="Relaxed output models."),
                _port("score_table", ["score_table"], help="Rosetta and interface metrics."),
                _port("interface_metrics", ["interface_metrics"], required=False, help="Structured interface metric JSON."),
            ]
        },
        "parameter_schema_json": {
            "fields": [
                _field("protocol", "Protocol", "enum", "interface_score", "Rosetta protocol to run.", options=["interface_score", "relax", "ddg", "cartesian_ddg"]),
                _field("nstruct", "N structures", "integer", 1, "Number of Rosetta trajectories.", minimum=1, maximum=10000),
                _field("relax_rounds", "Relax rounds", "integer", 3, "FastRelax repeat count.", minimum=0, maximum=100),
                _field("score_function", "Score function", "enum", "ref2015", "Rosetta score function.", advanced=True, options=["ref2015", "beta_nov16", "beta_cart"]),
                _field("interface_chains", "Interface chains", "string", "A_B", "Rosetta interface chain definition."),
                _field("ddg_repeats", "ddG repeats", "integer", 3, "Repeat count for ddG protocols.", advanced=True, minimum=1, maximum=100),
                _field("constraint_weight", "Constraint weight", "number", 1.0, "Constraint score weight.", advanced=True, minimum=0, maximum=100),
            ]
        },
        "artifact_schema_json": {"outputs": [{"type": "relaxed_structure", "formats": ["pdb", "mmcif"]}, {"type": "score_table", "formats": ["csv", "json"]}, {"type": "interface_metrics", "formats": ["json"]}]},
        "supported_task_types": ["binder_design", "scaffold_redesign", "enzyme_repair"],
        "supported_file_types": ["pdb", "mmcif", "json"],
        "resource_requirement_json": {"gpu_count": 0, "cpu_count": 16, "memory_gb": 32, "runtime_env": {}},
        "default_compute_node_id": "compute_cpu_local",
        "container_image": "bda/rosetta:2024.09",
        "command_template": "python run.py",
        "api_endpoint": None,
        "license": "Rosetta academic/commercial terms",
        "citation": "Rosetta upstream citation TBD",
        "status": "active",
    },
    {
        "model_plugin_id": "plugin_maskrgn",
        "model_name": "Mask RGN",
        "model_type": "sequence_generation",
        "provider": "internal",
        "version": "experimental-0.1",
        "description": "Internal experimental masked graph sequence model for structure-conditioned redesign.",
        "input_schema_json": {
            "ports": [
                _port("structure", ["structure", "backbone_set", "cleaned_structure"], help="Structure or backbone artifact for graph-conditioned sampling."),
                _port("mask_positions", ["constraints"], required=False, help="Residue mask specification."),
                _port("task_config", ["constraints"], required=False, help="Optional task-level configuration JSON."),
            ]
        },
        "output_schema_json": {
            "ports": [
                _port("sequence_set", ["sequence_set"], many=True, help="Sampled sequences."),
                _port("score_table", ["score_table"], required=False, help="Model scores and sampling metadata."),
                _port("embedding", ["embedding"], required=False, help="Optional model embeddings or latent features."),
            ]
        },
        "parameter_schema_json": {
            "fields": [
                _field("checkpoint_key", "Checkpoint", "enum", "maskrgnn_demo", "Server-side checkpoint reference.", options=["maskrgnn_demo"]),
                _field("num_samples", "Number of samples", "integer", 64, "Number of sequences to sample.", minimum=1, maximum=100000),
                _field("mask_ratio", "Mask ratio", "number", 0.3, "Fraction of residues sampled when mask positions are not explicit.", minimum=0, maximum=1),
                _field("temperature", "Temperature", "number", 1.0, "Sampling temperature.", minimum=0, maximum=5),
                _field("fixed_positions", "Fixed positions", "string", "", "Residues to keep fixed, for example A:10,A:11."),
                _field("random_seed", "Random seed", "integer", 0, "Zero means auto-generate seed.", advanced=True, minimum=0),
            ]
        },
        "artifact_schema_json": {"outputs": [{"type": "sequence_set", "formats": ["fasta", "csv"]}, {"type": "score_table", "formats": ["csv", "json"]}, {"type": "embedding", "formats": ["json"]}]},
        "supported_task_types": ["binder_design", "scaffold_redesign", "enzyme_repair"],
        "supported_file_types": ["pdb", "mmcif", "json"],
        "resource_requirement_json": {"gpu_count": 1, "min_vram_gb": 16, "cpu_count": 8, "memory_gb": 24, "runtime_env": {"BDA_GPU": "1", "BDA_MASKRGN_CHECKPOINT": "maskrgnn_demo"}},
        "default_compute_node_id": "compute_gpu_local",
        "container_image": "bda/maskrgn:experimental-0.1",
        "command_template": "python -m maskrgnn_clean.inference",
        "api_endpoint": None,
        "license": "Internal",
        "citation": "Internal BDA Mask RGN experimental model",
        "status": "experimental",
    },
]


MODEL_PLUGIN_COLUMNS = [
    "model_plugin_id",
    "model_name",
    "model_type",
    "provider",
    "version",
    "description",
    "input_schema_json",
    "output_schema_json",
    "parameter_schema_json",
    "artifact_schema_json",
    "supported_task_types",
    "supported_file_types",
    "resource_requirement_json",
    "default_compute_node_id",
    "container_image",
    "command_template",
    "api_endpoint",
    "license",
    "citation",
    "status",
]


def default_model_plugins() -> list[dict[str, Any]]:
    return deepcopy(DEFAULT_MODEL_PLUGINS)


def _db_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value


def register_default_model_plugins(connection: sqlite3.Connection) -> None:
    placeholders = ", ".join(["?"] * len(MODEL_PLUGIN_COLUMNS))
    updates = ", ".join([f"{column} = excluded.{column}" for column in MODEL_PLUGIN_COLUMNS if column != "model_plugin_id"])
    sql = f"""
        INSERT INTO model_plugins ({", ".join(MODEL_PLUGIN_COLUMNS)})
        VALUES ({placeholders})
        ON CONFLICT(model_plugin_id) DO UPDATE SET {updates}
    """
    for plugin in DEFAULT_MODEL_PLUGINS:
        connection.execute(sql, tuple(_db_value(plugin.get(column)) for column in MODEL_PLUGIN_COLUMNS))
