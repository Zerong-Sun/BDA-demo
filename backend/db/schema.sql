PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
  project_id TEXT PRIMARY KEY,
  project_name TEXT NOT NULL,
  project_type TEXT NOT NULL,
  status TEXT NOT NULL,
  owner_id TEXT,
  summary TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS targets (
  target_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
  target_name TEXT NOT NULL,
  target_type TEXT NOT NULL,
  pdb_id TEXT,
  chain_ids TEXT,
  sequence TEXT,
  structure_file_path TEXT,
  cleaned_structure_file_path TEXT,
  epitope_residues TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS design_tasks (
  task_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
  task_type TEXT NOT NULL,
  objective TEXT NOT NULL,
  constraints_json TEXT NOT NULL DEFAULT '{}',
  model_route_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL,
  created_by TEXT
);

CREATE TABLE IF NOT EXISTS workflow_runs (
  workflow_run_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES design_tasks(task_id) ON DELETE CASCADE,
  status TEXT NOT NULL,
  start_time TEXT,
  end_time TEXT,
  compute_resource TEXT,
  summary_metrics_json TEXT NOT NULL DEFAULT '{}',
  layout_json TEXT NOT NULL DEFAULT '{"nodes":[],"edges":[]}',
  output_directory TEXT
);

CREATE TABLE IF NOT EXISTS workflow_node_runs (
  node_run_id TEXT PRIMARY KEY,
  workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(workflow_run_id) ON DELETE CASCADE,
  node_type TEXT NOT NULL,
  node_name TEXT NOT NULL,
  status TEXT NOT NULL,
  model_name TEXT,
  model_version TEXT,
  input_files_json TEXT NOT NULL DEFAULT '[]',
  output_files_json TEXT NOT NULL DEFAULT '[]',
  parameters_json TEXT NOT NULL DEFAULT '{}',
  metrics_json TEXT NOT NULL DEFAULT '{}',
  logs TEXT,
  error_message TEXT,
  position_json TEXT NOT NULL DEFAULT '{"x":0,"y":0}'
);

CREATE TABLE IF NOT EXISTS workflow_edges (
  edge_id TEXT PRIMARY KEY,
  workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(workflow_run_id) ON DELETE CASCADE,
  source_node_run_id TEXT NOT NULL REFERENCES workflow_node_runs(node_run_id) ON DELETE CASCADE,
  source_port TEXT NOT NULL DEFAULT 'output',
  target_node_run_id TEXT NOT NULL REFERENCES workflow_node_runs(node_run_id) ON DELETE CASCADE,
  target_port TEXT NOT NULL DEFAULT 'input',
  edge_type TEXT NOT NULL DEFAULT 'data',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(workflow_run_id, source_node_run_id, source_port, target_node_run_id, target_port, edge_type)
);

CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(project_id) ON DELETE CASCADE,
  workflow_run_id TEXT REFERENCES workflow_runs(workflow_run_id) ON DELETE SET NULL,
  node_run_id TEXT REFERENCES workflow_node_runs(node_run_id) ON DELETE SET NULL,
  artifact_type TEXT NOT NULL,
  format TEXT NOT NULL,
  storage_uri TEXT NOT NULL,
  display_name TEXT NOT NULL,
  size_bytes INTEGER NOT NULL DEFAULT 0,
  checksum TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidates (
  candidate_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
  task_id TEXT NOT NULL REFERENCES design_tasks(task_id) ON DELETE CASCADE,
  workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(workflow_run_id) ON DELETE CASCADE,
  family TEXT,
  sequence TEXT,
  structure_file_path TEXT,
  complex_file_path TEXT,
  interface_score REAL,
  pred_kd TEXT,
  plddt REAL,
  interface_pae REAL,
  rosetta_score REAL,
  interface_energy REAL,
  clash_count INTEGER,
  buried_sasa REAL,
  solubility_score REAL,
  aggregation_risk TEXT,
  expression_risk TEXT,
  status TEXT NOT NULL,
  decision TEXT,
  next_action TEXT
);

CREATE TABLE IF NOT EXISTS experiment_results (
  result_id TEXT PRIMARY KEY,
  experiment_batch_id TEXT NOT NULL,
  candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
  experiment_type TEXT NOT NULL,
  pass_status TEXT NOT NULL,
  value TEXT,
  unit TEXT,
  raw_file TEXT,
  processed_file TEXT,
  conclusion TEXT,
  failure_reason TEXT
);

CREATE TABLE IF NOT EXISTS delivery_packages (
  package_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
  candidate_ids TEXT NOT NULL DEFAULT '[]',
  report_file TEXT,
  fasta_file TEXT,
  structure_bundle TEXT,
  score_table TEXT,
  experiment_summary TEXT,
  redesign_constraints TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS server_connections (
  server_id TEXT PRIMARY KEY,
  server_name TEXT NOT NULL,
  server_type TEXT NOT NULL,
  base_url TEXT,
  auth_type TEXT NOT NULL,
  credential_ref TEXT,
  network_status TEXT NOT NULL,
  health_check_endpoint TEXT,
  last_health_check_at TEXT,
  capabilities_json TEXT NOT NULL DEFAULT '{}',
  owner_id TEXT,
  enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS compute_nodes (
  compute_node_id TEXT PRIMARY KEY,
  server_id TEXT REFERENCES server_connections(server_id) ON DELETE SET NULL,
  node_name TEXT NOT NULL,
  node_type TEXT NOT NULL,
  scheduler_type TEXT NOT NULL,
  queue_name TEXT,
  gpu_type TEXT,
  gpu_count INTEGER NOT NULL DEFAULT 0,
  cpu_count INTEGER NOT NULL DEFAULT 0,
  memory_gb INTEGER NOT NULL DEFAULT 0,
  storage_path TEXT,
  container_runtime TEXT,
  status TEXT NOT NULL,
  current_jobs_json TEXT NOT NULL DEFAULT '[]',
  resource_limits_json TEXT NOT NULL DEFAULT '{}',
  last_seen_at TEXT
);

CREATE TABLE IF NOT EXISTS model_plugins (
  model_plugin_id TEXT PRIMARY KEY,
  model_name TEXT NOT NULL,
  model_type TEXT NOT NULL,
  provider TEXT NOT NULL,
  version TEXT NOT NULL,
  description TEXT,
  input_schema_json TEXT NOT NULL DEFAULT '{}',
  output_schema_json TEXT NOT NULL DEFAULT '{}',
  parameter_schema_json TEXT NOT NULL DEFAULT '{}',
  artifact_schema_json TEXT NOT NULL DEFAULT '{}',
  supported_task_types TEXT NOT NULL DEFAULT '[]',
  supported_file_types TEXT NOT NULL DEFAULT '[]',
  resource_requirement_json TEXT NOT NULL DEFAULT '{}',
  default_compute_node_id TEXT REFERENCES compute_nodes(compute_node_id) ON DELETE SET NULL,
  container_image TEXT,
  command_template TEXT,
  api_endpoint TEXT,
  license TEXT,
  citation TEXT,
  status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS method_plugins (
  method_plugin_id TEXT PRIMARY KEY,
  method_name TEXT NOT NULL,
  method_type TEXT NOT NULL,
  description TEXT,
  input_schema_json TEXT NOT NULL DEFAULT '{}',
  output_schema_json TEXT NOT NULL DEFAULT '{}',
  parameter_schema_json TEXT NOT NULL DEFAULT '{}',
  compatible_model_types TEXT NOT NULL DEFAULT '[]',
  compatible_workflow_nodes TEXT NOT NULL DEFAULT '[]',
  default_parameters_json TEXT NOT NULL DEFAULT '{}',
  version TEXT NOT NULL,
  owner_id TEXT,
  status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_providers (
  llm_provider_id TEXT PRIMARY KEY,
  provider_name TEXT NOT NULL,
  provider_type TEXT NOT NULL,
  base_url TEXT,
  model_names TEXT NOT NULL DEFAULT '[]',
  auth_type TEXT NOT NULL,
  credential_ref TEXT,
  tool_calling_supported INTEGER NOT NULL DEFAULT 0,
  json_schema_supported INTEGER NOT NULL DEFAULT 0,
  max_context_tokens INTEGER,
  default_temperature REAL,
  allowed_scopes TEXT NOT NULL DEFAULT '[]',
  data_policy TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_entries (
  knowledge_entry_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  subcategory TEXT,
  summary TEXT NOT NULL,
  content TEXT NOT NULL,
  tags_json TEXT NOT NULL DEFAULT '[]',
  related_model_plugins TEXT NOT NULL DEFAULT '[]',
  related_method_plugins TEXT NOT NULL DEFAULT '[]',
  source_type TEXT NOT NULL DEFAULT 'curated',
  citation TEXT,
  confidence TEXT NOT NULL DEFAULT 'curated',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id TEXT PRIMARY KEY,
  actor_id TEXT,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT,
  project_id TEXT,
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_targets_project_id ON targets(project_id);
CREATE INDEX IF NOT EXISTS idx_design_tasks_project_id ON design_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_task_id ON workflow_runs(task_id);
CREATE INDEX IF NOT EXISTS idx_workflow_node_runs_workflow_run_id ON workflow_node_runs(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_workflow_edges_workflow_run_id ON workflow_edges(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_workflow_edges_source ON workflow_edges(source_node_run_id);
CREATE INDEX IF NOT EXISTS idx_workflow_edges_target ON workflow_edges(target_node_run_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_project_id ON artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_workflow_run_id ON artifacts(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_node_run_id ON artifacts(node_run_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_category ON knowledge_entries(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_status ON knowledge_entries(status);
CREATE INDEX IF NOT EXISTS idx_candidates_project_id ON candidates(project_id);
CREATE INDEX IF NOT EXISTS idx_candidates_workflow_run_id ON candidates(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
CREATE INDEX IF NOT EXISTS idx_experiment_results_candidate_id ON experiment_results(candidate_id);
