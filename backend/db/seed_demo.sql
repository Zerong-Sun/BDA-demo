DELETE FROM audit_logs;
DELETE FROM llm_providers;
DELETE FROM method_plugins;
DELETE FROM model_plugins;
DELETE FROM compute_nodes;
DELETE FROM server_connections;
DELETE FROM delivery_packages;
DELETE FROM experiment_results;
DELETE FROM candidates;
DELETE FROM workflow_edges;
DELETE FROM workflow_node_runs;
DELETE FROM workflow_runs;
DELETE FROM design_tasks;
DELETE FROM targets;
DELETE FROM projects;

INSERT INTO projects (project_id, project_name, project_type, status, owner_id, summary)
VALUES
  ('proj_pd1_0423', 'PD1Binder_validation_0423', 'binder_design', 'running', 'demo-user', 'PD-1 binder closed-loop demo with BLI validation and redesign constraints.'),
  ('proj_nanocage_0518', 'Nanocage_delivery_0518', 'multimer_design', 'draft', 'demo-user', 'Programmable protein cage cargo display route planning.'),
  ('proj_enzyme_0507', 'Enzyme_repair_0507', 'scaffold_redesign', 'queued', 'demo-user', 'Enzyme scaffold repair constrained by expression and thermal-shift data.');

INSERT INTO targets (target_id, project_id, target_name, target_type, pdb_id, chain_ids, epitope_residues, metadata_json)
VALUES
  ('target_pd1', 'proj_pd1_0423', 'PD-1 extracellular domain', 'protein', NULL, 'A', 'interface patch from assay brief', '{"assay_constraints":["BLI","SEC"],"species":"human"}');

INSERT INTO design_tasks (task_id, project_id, task_type, objective, constraints_json, model_route_json, status, created_by)
VALUES
  ('task_pd1_binder', 'proj_pd1_0423', 'binder_design', 'Design PD-1 binders with expression and developability constraints.', '{"preserve_epitope":true,"max_family_ordered":6,"penalize_hydrophobic_patch":true}', '["target_intake","rfdiffusion","proteinmpnn","alphafold2","rosetta","bda_filters","wet_lab_validation"]', 'completed', 'demo-user');

INSERT INTO workflow_runs (workflow_run_id, task_id, status, start_time, end_time, compute_resource, summary_metrics_json, output_directory)
VALUES
  ('run_pd1_round1', 'task_pd1_binder', 'completed', '2026-05-20T09:00:00Z', '2026-05-22T18:30:00Z', 'demo_precomputed', '{"generated":18000,"designed":1248,"folded":312,"scored":120,"ordered":48,"bli_positive":9,"best_kd":"0.6 nM"}', 'artifacts/proj_pd1_0423/run_pd1_round1');

INSERT INTO workflow_node_runs (node_run_id, workflow_run_id, node_type, node_name, status, model_name, model_version, parameters_json, metrics_json, logs)
VALUES
  ('node_target', 'run_pd1_round1', 'target_intake', 'Target protein', 'completed', NULL, NULL, '{"target":"PD-1","assays":["BLI","SEC"]}', '{"inputs_confirmed":3}', 'PD-1 target and constraints parsed.'),
  ('node_rf', 'run_pd1_round1', 'backbone_generation', 'RFdiffusion backbone generation', 'completed', 'RFdiffusion', 'demo-1.0', '{"backbones_requested":18000}', '{"generated":18000}', 'Generated 18,000 candidate backbones.'),
  ('node_mpnn', 'run_pd1_round1', 'sequence_generation', 'ProteinMPNN sequence design', 'completed', 'ProteinMPNN', 'demo-1.0', '{"diversity_cap":true}', '{"designed":1248}', 'Designed 1,248 sequences.'),
  ('node_af2', 'run_pd1_round1', 'fold_prediction', 'AlphaFold2 complex prediction', 'completed', 'AlphaFold2', 'demo-2.3', '{"recycles":3,"database_preset":"reduced_dbs"}', '{"folded":312}', 'Folded 312 complexes.'),
  ('node_rosetta', 'run_pd1_round1', 'scoring', 'Rosetta relax / interface scoring', 'completed', 'Rosetta', 'demo-2026.06', '{"relax_repeats":3}', '{"scored":120}', 'Completed Rosetta relax and interface scoring.'),
  ('node_filter', 'run_pd1_round1', 'selection', 'BDA filters', 'completed', 'BDA filters', 'demo-1.0', '{"max_family_ordered":6}', '{"ordered":48}', 'Selected 48 designs for wet-lab validation.'),
  ('node_lab', 'run_pd1_round1', 'experiment', 'Wet-lab validation', 'completed', NULL, NULL, '{"assays":["expression","purification","BLI","SEC","thermal_shift"]}', '{"bli_positive":9,"best_kd":"0.6 nM"}', 'BLI confirmed 9 positive candidates.');

INSERT INTO candidates (candidate_id, project_id, task_id, workflow_run_id, family, sequence, structure_file_path, complex_file_path, interface_score, pred_kd, plddt, interface_pae, rosetta_score, interface_energy, clash_count, buried_sasa, solubility_score, aggregation_risk, expression_risk, status, decision, next_action)
VALUES
  ('PD1Binder_c4361', 'proj_pd1_0423', 'task_pd1_binder', 'run_pd1_round1', 'F2', NULL, 'structures/PD1Binder_c4361.pdb', 'complexes/PD1Binder_c4361_complex.pdb', 94, '0.6 nM', 92, 1.8, -28.4, -42.6, 0, 1280.5, 88, 'Low', 'High', 'Validated', 'Anchor', 'Preserve motif and generate scaffold-diverse round-two variants.'),
  ('PD1Binder_a0172', 'proj_pd1_0423', 'task_pd1_binder', 'run_pd1_round1', 'F2', NULL, 'structures/PD1Binder_a0172.pdb', 'complexes/PD1Binder_a0172_complex.pdb', 91, '1.1 nM', 89, 2.1, -25.7, -39.1, 1, 1195.0, 84, 'Low', 'High', 'Validated', 'Order', 'Keep as exploitation candidate.'),
  ('PD1Binder_b1923', 'proj_pd1_0423', 'task_pd1_binder', 'run_pd1_round1', 'F5', NULL, 'structures/PD1Binder_b1923.pdb', 'complexes/PD1Binder_b1923_complex.pdb', 87, '2.4 nM', 84, 2.6, -22.9, -36.4, 2, 1102.3, 81, 'Medium', 'Medium', 'Validated', 'Order', 'Keep for family diversity.'),
  ('PD1Binder_c7239', 'proj_pd1_0423', 'task_pd1_binder', 'run_pd1_round1', 'F1', NULL, NULL, NULL, 82, '4.8 nM', 76, 3.8, -18.1, NULL, NULL, NULL, 68, 'High', 'Low', 'QC risk', 'Hold', 'Improve developability before ordering.'),
  ('PD1Binder_a6562', 'proj_pd1_0423', 'task_pd1_binder', 'run_pd1_round1', 'F3', NULL, NULL, NULL, 80, '5.2 nM', 83, 2.9, -19.3, NULL, NULL, NULL, 76, 'Medium', 'Medium', 'Retest', 'Retest', 'Retest with stricter SEC gate.'),
  ('PD1Binder_d4410', 'proj_pd1_0423', 'task_pd1_binder', 'run_pd1_round1', 'F6', NULL, NULL, NULL, 77, '7.5 nM', 80, 2.7, -17.6, NULL, NULL, NULL, 79, 'Low', 'High', 'Reserve', 'Reserve', 'Reserve for exploration batch.'),
  ('PD1Binder_e2014', 'proj_pd1_0423', 'task_pd1_binder', 'run_pd1_round1', 'F4', NULL, NULL, NULL, 74, '9.8 nM', 72, 3.1, -15.8, NULL, NULL, NULL, 71, 'Medium', 'Medium', 'Reserve', 'Reserve', 'Reserve only if diversity is needed.'),
  ('PD1Binder_f1021', 'proj_pd1_0423', 'task_pd1_binder', 'run_pd1_round1', 'F7', NULL, NULL, NULL, 71, '12 nM', 79, 2.5, -14.9, NULL, NULL, NULL, 75, 'Low', 'High', 'Reserve', 'Reserve', 'Reserve for scaffold exploration.');

INSERT INTO experiment_results (result_id, experiment_batch_id, candidate_id, experiment_type, pass_status, value, unit, conclusion, failure_reason)
VALUES
  ('result_bli_c4361', 'batch_pd1_48', 'PD1Binder_c4361', 'BLI', 'pass', '0.6', 'nM', 'Best measured BLI Kd; use as round-two motif anchor.', NULL),
  ('result_sec_c4361', 'batch_pd1_48', 'PD1Binder_c4361', 'SEC', 'pass', 'monomeric', NULL, 'Acceptable SEC profile.', NULL),
  ('result_bli_a0172', 'batch_pd1_48', 'PD1Binder_a0172', 'BLI', 'pass', '1.1', 'nM', 'Strong binder from F2 family.', NULL),
  ('result_bli_b1923', 'batch_pd1_48', 'PD1Binder_b1923', 'BLI', 'pass', '2.4', 'nM', 'Strong binder from F5 family.', NULL),
  ('result_bli_c7239', 'batch_pd1_48', 'PD1Binder_c7239', 'BLI', 'pass', '4.8', 'nM', 'Moderate binder from F1 family.', NULL),
  ('result_sec_c7239', 'batch_pd1_48', 'PD1Binder_c7239', 'SEC', 'fail', 'aggregation', NULL, 'Aggregation risk confirmed.', 'hydrophobic_patch'),
  ('result_bli_a6562', 'batch_pd1_48', 'PD1Binder_a6562', 'BLI', 'pass', '5.2', 'nM', 'Moderate binder from F3 family.', NULL),
  ('result_bli_d4410', 'batch_pd1_48', 'PD1Binder_d4410', 'BLI', 'pass', '7.5', 'nM', 'Usable binder from F6 family.', NULL),
  ('result_bli_e2014', 'batch_pd1_48', 'PD1Binder_e2014', 'BLI', 'pass', '9.8', 'nM', 'Usable binder from F4 family.', NULL),
  ('result_bli_f1021', 'batch_pd1_48', 'PD1Binder_f1021', 'BLI', 'pass', '12', 'nM', 'Usable binder from F7 family.', NULL);

INSERT INTO delivery_packages (package_id, project_id, candidate_ids, report_file, fasta_file, structure_bundle, score_table, experiment_summary, redesign_constraints)
VALUES
  ('pkg_pd1_round1', 'proj_pd1_0423', '["PD1Binder_c4361","PD1Binder_a0172","PD1Binder_b1923"]', 'artifacts/reports/pd1_round1_summary.pdf', 'artifacts/fasta/pd1_round1_ordered.fasta', 'artifacts/structures/pd1_round1_top.zip', 'artifacts/tables/pd1_round1_scores.csv', '9/48 BLI-positive candidates; best BLI Kd 0.6 nM.', '{"preserve_candidate":"PD1Binder_c4361","increase_scaffold_diversity":true,"penalize_exposed_hydrophobic_area":true}');

INSERT INTO server_connections (server_id, server_name, server_type, base_url, auth_type, credential_ref, network_status, health_check_endpoint, capabilities_json, owner_id, enabled)
VALUES
  ('server_local_api', 'BDA local API gateway', 'local_server', 'http://localhost:8100', 'none', NULL, 'available', '/health', '{"roles":["api_gateway"]}', 'demo-user', 1),
  ('server_cpu_worker', 'BDA CPU worker', 'local_server', 'http://localhost:8110', 'none', NULL, 'unavailable', '/health', '{"roles":["structure_preparation","rosetta","score_merge","report_generation"]}', 'demo-user', 1),
  ('server_gpu_worker', 'BDA GPU worker', 'local_server', 'http://localhost:8120', 'none', NULL, 'unavailable', '/health', '{"roles":["rfdiffusion","proteinmpnn","alphafold2"]}', 'demo-user', 1);

INSERT INTO compute_nodes (compute_node_id, server_id, node_name, node_type, scheduler_type, gpu_type, gpu_count, cpu_count, memory_gb, storage_path, container_runtime, status, current_jobs_json, resource_limits_json, last_seen_at)
VALUES
  ('compute_cpu_local', 'server_cpu_worker', 'local-cpu-worker', 'CPU', 'local', NULL, 0, 16, 64, 'artifacts/scratch/cpu', 'Docker', 'unavailable', '[]', '{"max_jobs":2}', NULL),
  ('compute_gpu_local', 'server_gpu_worker', 'local-gpu-worker', 'GPU', 'local', 'NVIDIA RTX/A-series', 1, 24, 128, 'artifacts/scratch/gpu', 'Docker', 'unavailable', '[]', '{"max_jobs":1,"min_vram_gb":24}', NULL);

INSERT INTO model_plugins (model_plugin_id, model_name, model_type, provider, version, description, input_schema_json, output_schema_json, parameter_schema_json, artifact_schema_json, supported_task_types, supported_file_types, resource_requirement_json, default_compute_node_id, container_image, command_template, api_endpoint, license, citation, status)
VALUES
  ('plugin_rfdiffusion', 'RFdiffusion', 'backbone_generation', 'open_source', 'demo-1.0', 'Backbone generation for binder geometry.', '{"target_pdb":"string","contig_map":"string"}', '{"backbone_dir":"path","manifest":"json"}', '{"num_designs":"integer"}', '{"artifacts":["pdb","manifest.json"]}', '["binder_design"]', '["pdb","mmcif"]', '{"gpu":true,"min_vram_gb":24}', 'compute_gpu_local', NULL, 'rfdiffusion --config {parameters}', NULL, 'BSD-style / upstream dependent', 'RFdiffusion upstream citation TBD', 'active'),
  ('plugin_proteinmpnn', 'ProteinMPNN', 'sequence_generation', 'open_source', 'demo-1.0', 'Sequence design with diversity controls.', '{"backbone_dir":"path"}', '{"fasta":"path","score_table":"csv"}', '{"temperature":"number","diversity_cap":"boolean"}', '{"artifacts":["fasta","csv","manifest.json"]}', '["binder_design","scaffold_redesign"]', '["pdb"]', '{"gpu_preferred":true,"cpu_fallback":true}', 'compute_gpu_local', NULL, 'protein_mpnn_run.py --jsonl_path {input}', NULL, 'MIT / upstream dependent', 'ProteinMPNN upstream citation TBD', 'active'),
  ('plugin_alphafold2', 'AlphaFold2', 'fold_prediction', 'open_source', 'demo-2.3', 'Complex prediction and confidence scoring.', '{"fasta":"path","target_pdb":"path"}', '{"complex_models":"path","confidence_json":"json"}', '{"recycles":"integer","database_preset":"string"}', '{"artifacts":["pdb","json","manifest.json"]}', '["binder_design"]', '["fasta","pdb"]', '{"gpu":true,"database_ssd":true}', 'compute_gpu_local', NULL, 'run_alphafold.py --fasta_paths {fasta}', NULL, 'Apache-2.0 / database terms apply', 'AlphaFold upstream citation TBD', 'active'),
  ('plugin_rosetta', 'Rosetta', 'scoring', 'open_source', 'demo-2026.06', 'Relax and interface scoring.', '{"complex_pdb":"path"}', '{"score_table":"csv","relaxed_pdb":"path"}', '{"relax_repeats":"integer"}', '{"artifacts":["pdb","csv","manifest.json"]}', '["binder_design","scaffold_redesign"]', '["pdb"]', '{"cpu":true}', 'compute_cpu_local', NULL, 'rosetta_scripts.default.linuxgccrelease @flags', NULL, 'Rosetta academic/commercial terms', 'Rosetta upstream citation TBD', 'active');

INSERT INTO method_plugins (method_plugin_id, method_name, method_type, description, compatible_model_types, compatible_workflow_nodes, default_parameters_json, version, owner_id, status)
VALUES
  ('method_affinity_score', 'Affinity score', 'metric_calculation', 'Normalize interface and predicted binding metrics.', '["fold_prediction","scoring"]', '["BDA filters"]', '{"weight":0.35}', 'demo-1.0', 'demo-user', 'active'),
  ('method_diversity_cap', 'Diversity cap', 'filter', 'Limit ordered candidates from a single scaffold family.', '["sequence_generation","scoring"]', '["BDA filters"]', '{"max_per_family":6}', 'demo-1.0', 'demo-user', 'active'),
  ('method_expression_risk', 'Expression risk', 'ranking', 'Penalize candidates with low expression likelihood.', '["sequence_generation","scoring"]', '["BDA filters"]', '{"penalty":0.2}', 'demo-1.0', 'demo-user', 'active'),
  ('method_hydrophobic_patch', 'Hydrophobic patch penalty', 'ranking', 'Penalize exposed hydrophobic surface associated with SEC loss.', '["scoring"]', '["Rosetta scoring","BDA filters"]', '{"penalty":0.25}', 'demo-1.0', 'demo-user', 'active');

INSERT INTO llm_providers (llm_provider_id, provider_name, provider_type, base_url, model_names, auth_type, credential_ref, tool_calling_supported, json_schema_supported, max_context_tokens, default_temperature, allowed_scopes, data_policy, status)
VALUES
  ('llm_demo_rules', 'Demo rule-based Copilot', 'local_model', NULL, '["bda-demo-rules"]', 'none', NULL, 0, 1, 8000, 0.2, '["route_planning","candidate_explanation","result_interpretation","report_generation"]', '{"send_sequences":false,"send_structure_files":false,"send_internal_paths":false}', 'active');
