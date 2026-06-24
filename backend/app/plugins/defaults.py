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
                _field("inference.input_pdb", "Input PDB", "artifact_ref", "", "Target or motif PDB passed as inference.input_pdb."),
                _field("contigmap.contigs", "Contigs", "string", "[A1-150/0 70-100]", "Hydra contig list, e.g. target residues plus a chain break and binder length range."),
                _field("ppi.hotspot_res", "Hotspot residues", "string", "[A59,A83,A91]", "Target residues used to bias binder contacts."),
                _field("inference.num_designs", "Number of designs", "integer", 100, "RFdiffusion trajectories/backbones to sample.", minimum=1, maximum=100000),
                _field("inference.output_prefix", "Output prefix", "string", "outputs/rfdiffusion/design", "Prefix for generated PDB and trajectory outputs.", advanced=True),
                _field("diffuser.partial_T", "Partial diffusion steps", "integer", 0, "Use >0 to noise/denoise from a starting structure; requires length-compatible contigs.", advanced=True, minimum=0, maximum=50),
                _field("diffuser.T", "Diffusion steps", "integer", 50, "Total denoising steps; RFdiffusion defaults are checkpoint-aware.", advanced=True, minimum=1, maximum=200),
                _field("denoiser.noise_scale_ca", "CA noise scale", "number", 1.0, "Translation noise scale; lower values can improve constrained PPI designs at lower diversity.", advanced=True, minimum=0, maximum=5),
                _field("denoiser.noise_scale_frame", "Frame noise scale", "number", 1.0, "Frame/rotation noise scale; usually tied to CA noise scale.", advanced=True, minimum=0, maximum=5),
                _field("contigmap.inpaint_seq", "Inpaint sequence", "string", "", "Residue ranges whose sequence identity is hidden, e.g. [A1/A30-40].", advanced=True),
                _field("contigmap.inpaint_str", "Inpaint structure", "string", "", "Residue ranges whose structure is masked, useful for flexible peptide design.", advanced=True),
                _field("contigmap.provide_seq", "Provide sequence", "string", "", "Zero-indexed sequence ranges kept visible in partial diffusion, e.g. [100-119].", advanced=True),
                _field("inference.ckpt_override_path", "Checkpoint override", "enum", "", "Optional specialized RFdiffusion checkpoint.", advanced=True, options=["", "models/ActiveSite_ckpt.pt", "models/Complex_beta_ckpt.pt"]),
                _field("inference.symmetry", "Symmetry", "string", "", "Symmetry mode such as c4, d2, or tetrahedral when using symmetry config.", advanced=True),
                _field("potentials.guiding_potentials", "Guiding potentials", "json", "[]", "Optional RFdiffusion potentials list; tune carefully.", advanced=True),
                _field("potentials.guide_scale", "Potential guide scale", "number", 1.0, "Global strength for guiding potentials.", advanced=True, minimum=0, maximum=20),
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
                _field("pdb_path", "Single PDB path", "artifact_ref", "", "Use for a single backbone; alternatively provide jsonl_path."),
                _field("jsonl_path", "Parsed PDB JSONL", "artifact_ref", "", "Folder/file containing parsed ProteinMPNN JSONL inputs."),
                _field("out_folder", "Output folder", "string", "outputs/proteinmpnn", "Folder for FASTA, score, probability outputs."),
                _field("num_seq_per_target", "Sequences per target", "integer", 8, "Number of sequences sampled per backbone.", minimum=1, maximum=10000),
                _field("batch_size", "Batch size", "integer", 1, "Batch size; increase only if GPU memory allows.", minimum=1, maximum=1024),
                _field("sampling_temp", "Sampling temperatures", "string", "0.1", "Space-separated temperatures, e.g. 0.1 0.15 0.2; higher increases diversity."),
                _field("model_name", "Model name", "enum", "v_48_020", "ProteinMPNN model weights.", options=["v_48_002", "v_48_010", "v_48_020", "v_48_030"]),
                _field("pdb_path_chains", "Designed chains", "string", "", "Chains to design for a single PDB."),
                _field("chain_id_jsonl", "Chain design JSONL", "artifact_ref", "", "Dictionary specifying designed vs fixed chains.", advanced=True),
                _field("fixed_positions_jsonl", "Fixed positions JSONL", "artifact_ref", "", "Dictionary of fixed residue positions.", advanced=True),
                _field("omit_AAs", "Omit amino acids", "string", "X", "Amino acids excluded from sampling, e.g. CX.", advanced=True),
                _field("bias_AA_jsonl", "AA bias JSONL", "artifact_ref", "", "Global amino-acid composition bias.", advanced=True),
                _field("bias_by_res_jsonl", "Per-residue bias JSONL", "artifact_ref", "", "Per-position amino-acid bias.", advanced=True),
                _field("omit_AA_jsonl", "Per-residue omit JSONL", "artifact_ref", "", "Per-position omitted amino acids.", advanced=True),
                _field("pssm_jsonl", "PSSM JSONL", "artifact_ref", "", "PSSM constraints for sequence sampling.", advanced=True),
                _field("pssm_multi", "PSSM blend", "number", 0.0, "0 ignores PSSM, 1 ignores MPNN probabilities.", advanced=True, minimum=0, maximum=1),
                _field("pssm_threshold", "PSSM threshold", "number", 0.0, "Log-odds threshold restricting allowed amino acids.", advanced=True),
                _field("tied_positions_jsonl", "Tied positions JSONL", "artifact_ref", "", "Groups positions that should share sampled amino acids.", advanced=True),
                _field("backbone_noise", "Backbone noise", "number", 0.0, "Gaussian noise added to backbone atoms.", advanced=True, minimum=0, maximum=1),
                _field("use_soluble_model", "Use soluble model", "boolean", False, "Load weights trained on soluble proteins.", advanced=True),
                _field("ca_only", "CA-only model", "boolean", False, "Parse CA-only structures and use CA-only weights.", advanced=True),
                _field("seed", "Random seed", "integer", 0, "0 means randomly pick a seed.", advanced=True, minimum=0),
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
                _field("fasta_paths", "FASTA paths", "artifact_ref", "", "Comma-separated FASTA files; multisequence FASTA is folded as multimer."),
                _field("output_dir", "Output directory", "string", "outputs/alphafold", "Directory where AlphaFold writes ranked models and metrics."),
                _field("data_dir", "Data directory", "string", "/data/alphafold", "Directory containing AlphaFold databases and parameters."),
                _field("model_preset", "Model preset", "enum", "multimer", "AlphaFold preset.", options=["monomer", "monomer_casp14", "monomer_ptm", "multimer"]),
                _field("db_preset", "Database preset", "enum", "reduced_dbs", "Database search preset.", options=["full_dbs", "reduced_dbs"]),
                _field("max_template_date", "Max template date", "string", "2026-01-01", "Maximum template release date considered."),
                _field("num_multimer_predictions_per_model", "Multimer predictions/model", "integer", 5, "Predictions per multimer model; only applies to model_preset=multimer.", minimum=1, maximum=20),
                _field("models_to_relax", "Models to relax", "enum", "best", "Amber relaxation scope.", options=["all", "best", "none"]),
                _field("use_gpu_relax", "GPU relax", "boolean", True, "Run Amber relaxation on GPU."),
                _field("use_precomputed_msas", "Use precomputed MSAs", "boolean", False, "Reuse MSAs from output directory when available.", advanced=True),
                _field("benchmark", "Benchmark mode", "boolean", False, "Run JAX model twice to exclude compilation time.", advanced=True),
                _field("random_seed", "Random seed", "integer", 0, "0 means auto-generate seed.", advanced=True, minimum=0),
                _field("jackhmmer_n_cpu", "JackHMMER CPUs", "integer", 8, "CPU count for JackHMMER searches.", advanced=True, minimum=1, maximum=256),
                _field("hmmsearch_n_cpu", "HMMSearch CPUs", "integer", 8, "CPU count for HMMSearch in multimer pipeline.", advanced=True, minimum=1, maximum=256),
                _field("hhsearch_n_cpu", "HHSearch CPUs", "integer", 8, "CPU count for HHSearch template search.", advanced=True, minimum=1, maximum=256),
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
                _field("application", "Application", "enum", "rosetta_scripts", "Rosetta executable/application.", options=["rosetta_scripts", "relax", "InterfaceAnalyzer", "cartesian_ddg"]),
                _field("s", "Input structure", "artifact_ref", "", "Input PDB/mmCIF structure passed with -s."),
                _field("parser:protocol", "RosettaScripts XML", "artifact_ref", "", "XML protocol for rosetta_scripts; omit for standalone relax/interface tools."),
                _field("nstruct", "N structures", "integer", 1, "Number of output trajectories/decoys.", minimum=1, maximum=10000),
                _field("score:weights", "Score weights", "enum", "ref2015", "Score function weights file.", options=["ref2015", "beta_nov16", "beta_cart", "talaris2014"]),
                _field("interface", "Interface chains", "string", "A_B", "Interface definition used by interface scoring/analyzer protocols."),
                _field("ex1", "Extra chi 1 rotamers", "boolean", True, "Enable extra chi1 rotamers during packing."),
                _field("ex2", "Extra chi 2 rotamers", "boolean", True, "Enable extra chi2 rotamers during packing."),
                _field("relax:constrain_relax_to_start_coords", "Constrain to start coords", "boolean", True, "Coordinate constraints for FastRelax/local refinement.", advanced=True),
                _field("relax:ramp_constraints", "Ramp constraints", "boolean", False, "Whether to ramp constraint weights during relax.", advanced=True),
                _field("relax:script", "Relax script", "enum", "default", "Relax script/control file.", advanced=True, options=["default", "MonomerRelax2019", "InterfaceRelax2019", "always_constrained_relax_script"]),
                _field("parser:script_vars", "Script variables", "string", "", "RosettaScripts variable substitutions, e.g. resfile=design.resfile.", advanced=True),
                _field("resfile", "Resfile", "artifact_ref", "", "Residue-level design/repacking directives.", advanced=True),
                _field("constraints:cst_fa_file", "Constraint file", "artifact_ref", "", "Full-atom constraint file.", advanced=True),
                _field("out:suffix", "Output suffix", "string", "", "Suffix appended to Rosetta output structures.", advanced=True),
                _field("out:file:scorefile", "Scorefile", "string", "score.sc", "Rosetta scorefile path/name.", advanced=True),
                _field("constant_seed", "Constant seed", "boolean", False, "Use deterministic seed behavior.", advanced=True),
                _field("jran", "Random seed", "integer", 1111111, "Rosetta random seed when constant_seed is enabled.", advanced=True, minimum=1),
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
        "model_plugin_id": "plugin_alphafold3",
        "model_name": "AlphaFold 3",
        "model_type": "fold_prediction",
        "provider": "google_deepmind",
        "version": "3.0",
        "description": "All-atom biomolecular complex prediction for proteins, nucleic acids, ligands, ions, and covalent modifications; non-commercial model-parameter terms apply.",
        "input_schema_json": {
            "ports": [
                _port("fold_input_json", ["constraints", "sequence_set"], help="AlphaFold 3 JSON input with sequences, ligands, bonds, and model seeds."),
                _port("database_bundle", ["database"], required=False, help="Optional local AF3 public databases."),
            ]
        },
        "output_schema_json": {
            "ports": [
                _port("predicted_complex", ["complex_structure", "predicted_structure"], many=True, help="All-atom predicted structures."),
                _port("confidence_json", ["score_table"], help="Ranking/confidence outputs."),
                _port("run_manifest", ["manifest"], help="Machine-readable output manifest."),
            ]
        },
        "parameter_schema_json": {
            "workflow_note": "Prediction-stage alternative to AlphaFold2, Boltz, and Chai-1. Use after sequence/design generation; do not chain AF2 -> AF3 -> Boltz as if they were transformations unless doing explicit model comparison.",
            "exclusive_with": ["plugin_alphafold2", "plugin_boltz", "plugin_chai1"],
            "recommended_after": ["plugin_proteinmpnn", "plugin_rfdiffusion", "plugin_bindcraft"],
            "fields": [
                _field("json_path", "Input JSON", "artifact_ref", "", "Path to AlphaFold 3 fold_input.json."),
                _field("model_dir", "Model directory", "string", "/root/models", "Directory containing AlphaFold 3 model parameters obtained from Google."),
                _field("output_dir", "Output directory", "string", "outputs/alphafold3", "Directory for structures and confidence outputs."),
                _field("db_dir", "Database directory", "string", "/root/public_databases", "Directory containing AlphaFold 3 public databases."),
                _field("run_data_pipeline", "Run data pipeline", "boolean", True, "Run genetic/template search; CPU-only and time consuming."),
                _field("run_inference", "Run inference", "boolean", True, "Run GPU inference from prepared features."),
                _field("model_seeds", "Model seeds", "string", "1", "Comma-separated seeds written into AlphaFold 3 JSON input."),
                _field("num_recycles", "Recycles", "integer", 10, "Optional inference recycle count if exposed by local wrapper.", advanced=True, minimum=1, maximum=48),
                _field("non_commercial_ack", "Non-commercial use confirmed", "boolean", False, "Required before running with Google-provided AF3 parameters.", advanced=True),
            ],
        },
        "artifact_schema_json": {"outputs": [{"type": "complex_structure", "formats": ["cif", "pdb"]}, {"type": "score_table", "formats": ["json"]}]},
        "supported_task_types": ["binder_design", "complex_prediction", "ligand_complex_prediction", "nanocage_design"],
        "supported_file_types": ["json", "fasta", "cif", "pdb"],
        "resource_requirement_json": {"gpu_count": 1, "min_vram_gb": 40, "cpu_count": 16, "memory_gb": 64, "database_ssd": True, "runtime_env": {"BDA_GPU": "1"}},
        "default_compute_node_id": "compute_gpu_local",
        "container_image": "bda/alphafold3:3.0",
        "command_template": "python run_alphafold.py --json_path {json_path} --model_dir {model_dir} --output_dir {output_dir}",
        "api_endpoint": None,
        "license": "Apache-2.0 source; model parameters/output non-commercial terms",
        "citation": "Abramson et al. Nature 2024, AlphaFold 3",
        "status": "restricted",
    },
    {
        "model_plugin_id": "plugin_boltz",
        "model_name": "Boltz",
        "model_type": "fold_prediction",
        "provider": "open_source",
        "version": "2.x",
        "description": "Open-source biomolecular interaction prediction; Boltz-2 also reports binding-affinity-oriented outputs.",
        "input_schema_json": {
            "ports": [
                _port("input_yaml", ["constraints", "sequence_set"], help="Boltz YAML input or directory of YAML inputs."),
                _port("msa", ["msa"], required=False, help="Optional MSA artifacts or server-generated MSA."),
            ]
        },
        "output_schema_json": {
            "ports": [
                _port("predicted_complex", ["complex_structure", "predicted_structure"], many=True, help="Predicted complex structures."),
                _port("affinity_metrics", ["score_table"], required=False, help="Boltz affinity and binder-probability outputs."),
            ]
        },
        "parameter_schema_json": {
            "workflow_note": "Prediction-stage alternative to AlphaFold2/3 and Chai-1. Prefer Boltz when license/commercial availability or affinity-style ranking matters.",
            "exclusive_with": ["plugin_alphafold2", "plugin_alphafold3", "plugin_chai1"],
            "recommended_after": ["plugin_proteinmpnn", "plugin_rfdiffusion", "plugin_bindcraft"],
            "fields": [
                _field("input_path", "Input YAML/path", "artifact_ref", "", "Boltz YAML file or directory."),
                _field("model", "Model", "enum", "boltz2", "Boltz model family/version.", options=["boltz2", "boltz1"]),
                _field("use_msa_server", "Use MSA server", "boolean", True, "Generate MSAs through configured server."),
                _field("msa_server_url", "MSA server URL", "string", "", "Optional custom MSA server URL.", advanced=True),
                _field("predict_affinity", "Predict affinity", "boolean", True, "Return affinity prediction outputs when supported."),
                _field("num_samples", "Samples", "integer", 5, "Number of structure samples to generate.", minimum=1, maximum=100),
                _field("recycling_steps", "Recycling steps", "integer", 3, "Inference recycle count in local wrapper.", advanced=True, minimum=1, maximum=20),
                _field("diffusion_samples", "Diffusion samples", "integer", 1, "Diffusion samples per input if supported.", advanced=True, minimum=1, maximum=100),
            ],
        },
        "artifact_schema_json": {"outputs": [{"type": "complex_structure", "formats": ["cif", "pdb"]}, {"type": "score_table", "formats": ["json", "csv"]}]},
        "supported_task_types": ["binder_design", "complex_prediction", "ligand_complex_prediction", "affinity_ranking"],
        "supported_file_types": ["yaml", "yml", "fasta", "cif", "pdb"],
        "resource_requirement_json": {"gpu_count": 1, "min_vram_gb": 24, "cpu_count": 8, "memory_gb": 32, "runtime_env": {"BDA_GPU": "1"}},
        "default_compute_node_id": "compute_gpu_local",
        "container_image": "bda/boltz:2",
        "command_template": "boltz predict {input_path} --use_msa_server",
        "api_endpoint": None,
        "license": "MIT",
        "citation": "Boltz-1 / Boltz-2 technical reports",
        "status": "experimental",
    },
    {
        "model_plugin_id": "plugin_chai1",
        "model_name": "Chai-1",
        "model_type": "fold_prediction",
        "provider": "open_source",
        "version": "0.6.1",
        "description": "Multimodal biomolecular structure prediction for proteins, small molecules, DNA, RNA, glycosylations, restraints, and covalent bonds.",
        "input_schema_json": {
            "ports": [
                _port("input_fasta", ["sequence_set"], help="FASTA containing all complex components."),
                _port("restraints", ["constraints"], required=False, help="Optional restraints/covalent bond context."),
                _port("msa", ["msa"], required=False, help="Optional aligned.pqt MSA inputs."),
            ]
        },
        "output_schema_json": {
            "ports": [
                _port("predicted_complex", ["complex_structure", "predicted_structure"], many=True, help="Predicted structures."),
                _port("confidence_json", ["score_table"], help="Confidence outputs."),
            ]
        },
        "parameter_schema_json": {
            "workflow_note": "Prediction-stage alternative to AlphaFold2/3 and Boltz. Use when restraints, covalent bonds, modified residues, or ligand-like complex context are important.",
            "exclusive_with": ["plugin_alphafold2", "plugin_alphafold3", "plugin_boltz"],
            "recommended_after": ["plugin_proteinmpnn", "plugin_rfdiffusion", "plugin_bindcraft"],
            "fields": [
                _field("input_fasta", "Input FASTA", "artifact_ref", "", "FASTA containing proteins, nucleotides, ligands/SMILES, and modified residues."),
                _field("output_folder", "Output folder", "string", "outputs/chai1", "Folder for Chai predictions."),
                _field("num_samples", "Samples", "integer", 5, "Chai-1 default sample count.", minimum=1, maximum=100),
                _field("use_msa_server", "Use MSA server", "boolean", True, "Use MMseqs2/ColabFold server for automatic MSA generation."),
                _field("use_templates_server", "Use templates server", "boolean", True, "Use remote template server when available."),
                _field("msa_server_url", "MSA server URL", "string", "", "Optional custom ColabFold-compatible MSA server.", advanced=True),
                _field("template_cif_folder", "Template CIF folder", "string", "", "Folder for custom template CIF files.", advanced=True),
                _field("restraints_json", "Restraints JSON", "artifact_ref", "", "Optional contact/covalent-bond restraints.", advanced=True),
                _field("downloads_dir", "Weights cache", "string", "", "CHAI_DOWNLOADS_DIR override.", advanced=True),
            ],
        },
        "artifact_schema_json": {"outputs": [{"type": "complex_structure", "formats": ["cif", "pdb"]}, {"type": "score_table", "formats": ["json"]}]},
        "supported_task_types": ["binder_design", "complex_prediction", "ligand_complex_prediction", "restraint_guided_prediction"],
        "supported_file_types": ["fasta", "json", "pqt", "cif", "pdb"],
        "resource_requirement_json": {"gpu_count": 1, "min_vram_gb": 24, "recommended_vram_gb": 48, "cpu_count": 8, "memory_gb": 32, "runtime_env": {"BDA_GPU": "1"}},
        "default_compute_node_id": "compute_gpu_local",
        "container_image": "bda/chai1:0.6.1",
        "command_template": "chai-lab fold {input_fasta} {output_folder}",
        "api_endpoint": None,
        "license": "Apache-2.0",
        "citation": "Chai-1 technical report",
        "status": "experimental",
    },
    {
        "model_plugin_id": "plugin_bindcraft",
        "model_name": "BindCraft",
        "model_type": "workflow_pipeline",
        "provider": "open_source",
        "version": "2025.09",
        "description": "Automated de novo binder design pipeline using AlphaFold2 backpropagation, MPNN, and PyRosetta filters.",
        "input_schema_json": {
            "ports": [
                _port("target_settings", ["constraints"], help="BindCraft target JSON settings."),
                _port("target_structure", ["target_structure", "cleaned_structure"], help="Target PDB."),
                _port("filter_settings", ["constraints"], required=False, help="Filter JSON settings."),
                _port("advanced_settings", ["constraints"], required=False, help="Advanced design JSON settings."),
            ]
        },
        "output_schema_json": {
            "ports": [
                _port("binder_designs", ["sequence_set", "complex_structure"], many=True, help="Accepted binder sequences and structures."),
                _port("score_table", ["score_table"], help="BindCraft/AF2/MPNN/PyRosetta metrics."),
                _port("run_manifest", ["manifest"], help="Pipeline manifest."),
            ]
        },
        "parameter_schema_json": {
            "workflow_note": "End-to-end binder-design branch. Do not place RFdiffusion -> ProteinMPNN -> AlphaFold2 upstream of BindCraft on the same branch; use it as an alternative automated route, then merge only at ranking/experimental ordering.",
            "exclusive_with": ["plugin_rfdiffusion", "plugin_proteinmpnn", "plugin_alphafold2"],
            "recommended_before": ["plugin_rosetta", "plugin_boltz", "plugin_chai1", "plugin_alphafold3"],
            "fields": [
                _field("settings", "Target settings JSON", "artifact_ref", "", "BindCraft settings_target JSON."),
                _field("filters", "Filter settings JSON", "artifact_ref", "settings_filters/default_filters.json", "Filter JSON controlling acceptance thresholds."),
                _field("advanced", "Advanced settings JSON", "artifact_ref", "settings_advanced/default_4stage_multimer.json", "Advanced design algorithm/settings JSON."),
                _field("design_path", "Design path", "string", "outputs/bindcraft", "Output folder for designs and statistics."),
                _field("binder_name", "Binder name prefix", "string", "BDA_Binder", "Prefix for designed binder files."),
                _field("chains", "Target chains", "string", "A", "Target chains to keep/use."),
                _field("target_hotspot_residues", "Target hotspots", "string", "", "Hotspot residues or ranges; null/empty allows AF2 to choose binding site."),
                _field("lengths", "Binder lengths", "string", "70-120", "Binder length range."),
                _field("number_of_final_designs", "Final accepted designs", "integer", 100, "Stop after this many accepted designs.", minimum=1, maximum=10000),
                _field("design_algorithm", "Design algorithm", "enum", "4stage", "BindCraft trajectory algorithm.", options=["2stage", "3stage", "4stage", "greedy", "mcmc"]),
                _field("use_multimer_design", "Use AF2 multimer design", "boolean", True, "Use AF2-multimer for design; other model is used for validation."),
                _field("num_recycles_design", "Design recycles", "integer", 3, "AF2 recycles during design.", minimum=1, maximum=48),
                _field("num_recycles_validation", "Validation recycles", "integer", 3, "AF2 recycles during validation.", minimum=1, maximum=48),
                _field("num_seqs", "MPNN sequences", "integer", 8, "MPNN sequences sampled per accepted trajectory.", minimum=1, maximum=1000),
                _field("sampling_temp", "MPNN sampling temp", "number", 0.1, "ProteinMPNN sampling temperature.", advanced=True, minimum=0, maximum=2),
                _field("soft_iterations", "Soft iterations", "integer", 50, "Logits/soft design iterations.", advanced=True, minimum=0, maximum=10000),
                _field("temporary_iterations", "Temporary iterations", "integer", 50, "Softmax temporary design iterations.", advanced=True, minimum=0, maximum=10000),
                _field("hard_iterations", "Hard iterations", "integer", 10, "One-hot design iterations.", advanced=True, minimum=0, maximum=10000),
                _field("weights_iptm", "iPTM design weight", "number", 1.0, "Weight on interface pTM loss.", advanced=True, minimum=0, maximum=100),
                _field("acceptance_rate", "Acceptance-rate floor", "number", 0.01, "Stop/monitor threshold for poor target settings.", advanced=True, minimum=0, maximum=1),
            ],
        },
        "artifact_schema_json": {"outputs": [{"type": "sequence_set", "formats": ["fasta", "csv"]}, {"type": "complex_structure", "formats": ["pdb"]}, {"type": "score_table", "formats": ["csv", "json"]}]},
        "supported_task_types": ["binder_design"],
        "supported_file_types": ["json", "pdb", "csv"],
        "resource_requirement_json": {"gpu_count": 1, "min_vram_gb": 32, "cpu_count": 16, "memory_gb": 64, "runtime_env": {"BDA_GPU": "1"}, "requires_pyrosetta": True},
        "default_compute_node_id": "compute_gpu_local",
        "container_image": "bda/bindcraft:2025.09",
        "command_template": "python -u bindcraft.py --settings {settings} --filters {filters} --advanced {advanced}",
        "api_endpoint": None,
        "license": "Open-source pipeline; PyRosetta license required for commercial use",
        "citation": "BindCraft / Pacesa et al.",
        "status": "experimental",
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
        values = dict(plugin)
        compute_node_id = values.get("default_compute_node_id")
        if compute_node_id:
            exists = connection.execute(
                "SELECT 1 FROM compute_nodes WHERE compute_node_id = ?",
                (compute_node_id,),
            ).fetchone()
            if exists is None:
                values["default_compute_node_id"] = None
        connection.execute(
            sql,
            tuple(_db_value(values.get(column)) for column in MODEL_PLUGIN_COLUMNS),
        )
