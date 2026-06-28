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

CREATE TABLE IF NOT EXISTS research_sources (
  source_id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  title TEXT NOT NULL,
  uri TEXT NOT NULL,
  content_hash TEXT,
  version_ref TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'active',
  last_ingested_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(source_type, uri)
);

CREATE TABLE IF NOT EXISTS script_assets (
  script_asset_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  model_plugin_id TEXT,
  relative_path TEXT NOT NULL,
  language TEXT NOT NULL,
  scheduler TEXT,
  content_hash TEXT NOT NULL,
  resource_config_json TEXT NOT NULL DEFAULT '{}',
  environment_json TEXT NOT NULL DEFAULT '{}',
  input_hints_json TEXT NOT NULL DEFAULT '[]',
  output_hints_json TEXT NOT NULL DEFAULT '[]',
  parse_warnings_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (source_id) REFERENCES research_sources(source_id),
  FOREIGN KEY (model_plugin_id) REFERENCES model_plugins(model_plugin_id),
  UNIQUE(relative_path)
);

CREATE TABLE IF NOT EXISTS model_parameter_catalog (
  parameter_catalog_id TEXT PRIMARY KEY,
  model_plugin_id TEXT NOT NULL,
  parameter_key TEXT NOT NULL,
  label TEXT,
  parameter_type TEXT NOT NULL,
  default_value_json TEXT,
  constraints_json TEXT NOT NULL DEFAULT '{}',
  description TEXT,
  advanced INTEGER NOT NULL DEFAULT 0,
  provenance TEXT NOT NULL DEFAULT 'plugin_schema',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (model_plugin_id) REFERENCES model_plugins(model_plugin_id),
  UNIQUE(model_plugin_id, parameter_key)
);

CREATE TABLE IF NOT EXISTS script_parameter_observations (
  observation_id TEXT PRIMARY KEY,
  script_asset_id TEXT NOT NULL,
  model_plugin_id TEXT,
  parameter_key TEXT NOT NULL,
  raw_value TEXT,
  normalized_value_json TEXT,
  source_line INTEGER,
  source_kind TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (script_asset_id) REFERENCES script_assets(script_asset_id),
  FOREIGN KEY (model_plugin_id) REFERENCES model_plugins(model_plugin_id),
  UNIQUE(script_asset_id, parameter_key, source_line, source_kind)
);

CREATE TABLE IF NOT EXISTS literature_documents (
  document_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  external_source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  title TEXT NOT NULL,
  authors TEXT,
  journal TEXT,
  publication_year INTEGER,
  doi TEXT,
  pmid TEXT,
  pmcid TEXT,
  abstract_text TEXT,
  content_kind TEXT NOT NULL DEFAULT 'metadata',
  full_text_status TEXT NOT NULL DEFAULT 'not_requested',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (source_id) REFERENCES research_sources(source_id),
  UNIQUE(external_source, external_id)
);

CREATE TABLE IF NOT EXISTS document_chunks (
  chunk_id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  section_title TEXT,
  section_path TEXT,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  token_estimate INTEGER NOT NULL DEFAULT 0,
  summary_text TEXT,
  summary_method TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (document_id) REFERENCES literature_documents(document_id),
  UNIQUE(document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS scientific_claims (
  claim_id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  statement TEXT NOT NULL,
  claim_type TEXT NOT NULL DEFAULT 'finding',
  context_json TEXT NOT NULL DEFAULT '{}',
  confidence REAL,
  extraction_method TEXT NOT NULL,
  review_status TEXT NOT NULL DEFAULT 'pending_review',
  reviewed_by TEXT,
  reviewed_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (document_id) REFERENCES literature_documents(document_id)
);

CREATE TABLE IF NOT EXISTS claim_evidence (
  evidence_id TEXT PRIMARY KEY,
  claim_id TEXT NOT NULL,
  chunk_id TEXT NOT NULL,
  evidence_excerpt TEXT NOT NULL,
  start_offset INTEGER,
  end_offset INTEGER,
  evidence_role TEXT NOT NULL DEFAULT 'supports',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (claim_id) REFERENCES scientific_claims(claim_id),
  FOREIGN KEY (chunk_id) REFERENCES document_chunks(chunk_id)
);

CREATE TABLE IF NOT EXISTS claim_relations (
  relation_id TEXT PRIMARY KEY,
  source_claim_id TEXT NOT NULL,
  target_claim_id TEXT NOT NULL,
  relation_type TEXT NOT NULL,
  rationale TEXT,
  confidence REAL,
  review_status TEXT NOT NULL DEFAULT 'pending_review',
  reviewed_by TEXT,
  reviewed_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (source_claim_id) REFERENCES scientific_claims(claim_id),
  FOREIGN KEY (target_claim_id) REFERENCES scientific_claims(claim_id),
  UNIQUE(source_claim_id, target_claim_id, relation_type)
);

CREATE TABLE IF NOT EXISTS research_campaigns (
  campaign_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  name TEXT NOT NULL,
  objective TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  max_rounds INTEGER NOT NULL DEFAULT 3,
  current_round INTEGER NOT NULL DEFAULT 1,
  budget_json TEXT NOT NULL DEFAULT '{}',
  stop_conditions_json TEXT NOT NULL DEFAULT '[]',
  strategy_json TEXT NOT NULL DEFAULT '{}',
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS campaign_rounds (
  campaign_round_id TEXT PRIMARY KEY,
  campaign_id TEXT NOT NULL,
  round_number INTEGER NOT NULL,
  workflow_run_id TEXT NOT NULL,
  parent_round_id TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  parameter_patch_json TEXT NOT NULL DEFAULT '{}',
  approval_status TEXT NOT NULL DEFAULT 'not_required',
  approved_by TEXT,
  approved_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TEXT,
  FOREIGN KEY (campaign_id) REFERENCES research_campaigns(campaign_id) ON DELETE CASCADE,
  FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id) ON DELETE CASCADE,
  FOREIGN KEY (parent_round_id) REFERENCES campaign_rounds(campaign_round_id) ON DELETE SET NULL,
  UNIQUE(campaign_id, round_number),
  UNIQUE(workflow_run_id)
);

CREATE TABLE IF NOT EXISTS campaign_evaluations (
  evaluation_id TEXT PRIMARY KEY,
  campaign_round_id TEXT NOT NULL,
  metrics_json TEXT NOT NULL DEFAULT '{}',
  criteria_results_json TEXT NOT NULL DEFAULT '[]',
  recommendation TEXT NOT NULL,
  rationale TEXT,
  evaluator TEXT NOT NULL DEFAULT 'rule_based',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (campaign_round_id) REFERENCES campaign_rounds(campaign_round_id) ON DELETE CASCADE,
  UNIQUE(campaign_round_id)
);

CREATE TABLE IF NOT EXISTS campaign_decisions (
  decision_id TEXT PRIMARY KEY,
  campaign_round_id TEXT NOT NULL,
  decision_type TEXT NOT NULL,
  parameter_patch_json TEXT NOT NULL DEFAULT '{}',
  rationale TEXT,
  status TEXT NOT NULL DEFAULT 'proposed',
  proposed_by TEXT NOT NULL DEFAULT 'system',
  reviewed_by TEXT,
  reviewed_at TEXT,
  next_campaign_round_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (campaign_round_id) REFERENCES campaign_rounds(campaign_round_id) ON DELETE CASCADE,
  FOREIGN KEY (next_campaign_round_id) REFERENCES campaign_rounds(campaign_round_id) ON DELETE SET NULL,
  UNIQUE(campaign_round_id)
);

CREATE TABLE IF NOT EXISTS literature_subscriptions (
  subscription_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  query TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  interval_hours INTEGER NOT NULL DEFAULT 24,
  result_limit INTEGER NOT NULL DEFAULT 5,
  fetch_full_text INTEGER NOT NULL DEFAULT 1,
  extract_claims INTEGER NOT NULL DEFAULT 1,
  last_run_at TEXT,
  next_run_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_status TEXT,
  last_result_json TEXT NOT NULL DEFAULT '{}',
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_briefs (
  research_brief_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  title TEXT NOT NULL,
  objective TEXT NOT NULL,
  product_context TEXT NOT NULL DEFAULT 'food_ingredient',
  constraints_json TEXT NOT NULL DEFAULT '{}',
  source_material_json TEXT NOT NULL DEFAULT '[]',
  assumptions_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'draft',
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS research_findings (
  research_finding_id TEXT PRIMARY KEY,
  research_brief_id TEXT NOT NULL,
  track TEXT NOT NULL,
  title TEXT NOT NULL,
  statement TEXT NOT NULL,
  evidence_level TEXT NOT NULL DEFAULT 'research_seed',
  source_refs_json TEXT NOT NULL DEFAULT '[]',
  uncertainty TEXT,
  review_status TEXT NOT NULL DEFAULT 'pending_review',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (research_brief_id) REFERENCES research_briefs(research_brief_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS workflow_plans (
  workflow_plan_id TEXT PRIMARY KEY,
  research_brief_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  name TEXT NOT NULL,
  selected_route TEXT,
  route_options_json TEXT NOT NULL DEFAULT '[]',
  dossier_json TEXT NOT NULL DEFAULT '{}',
  nodes_json TEXT NOT NULL DEFAULT '[]',
  edges_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'draft',
  materialized_workflow_run_id TEXT,
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  version INTEGER DEFAULT '1' NOT NULL,
  supersedes_workflow_plan_id TEXT,
  FOREIGN KEY (research_brief_id) REFERENCES research_briefs(research_brief_id) ON DELETE CASCADE,
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
  FOREIGN KEY (materialized_workflow_run_id) REFERENCES workflow_runs(workflow_run_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS research_questions (
  research_question_id TEXT PRIMARY KEY,
  research_brief_id TEXT NOT NULL,
  track TEXT NOT NULL,
  question TEXT NOT NULL,
  query_json TEXT NOT NULL DEFAULT '{}',
  priority INTEGER NOT NULL DEFAULT 100,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (research_brief_id) REFERENCES research_briefs(research_brief_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS research_runs (
  research_run_id TEXT PRIMARY KEY,
  research_brief_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  progress_json TEXT NOT NULL DEFAULT '{}',
  result_summary_json TEXT NOT NULL DEFAULT '{}',
  error_message TEXT,
  started_at TEXT,
  completed_at TEXT,
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (research_brief_id) REFERENCES research_briefs(research_brief_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evidence_links (
  evidence_link_id TEXT PRIMARY KEY,
  research_run_id TEXT NOT NULL,
  research_question_id TEXT,
  research_finding_id TEXT,
  source_type TEXT NOT NULL,
  source_identifier TEXT,
  title TEXT NOT NULL,
  uri TEXT,
  evidence_excerpt TEXT,
  evidence_level TEXT NOT NULL DEFAULT 'metadata',
  applicability_json TEXT NOT NULL DEFAULT '{}',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  review_status TEXT NOT NULL DEFAULT 'pending_review',
  reviewed_by TEXT,
  reviewed_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (research_run_id) REFERENCES research_runs(research_run_id) ON DELETE CASCADE,
  FOREIGN KEY (research_question_id) REFERENCES research_questions(research_question_id) ON DELETE SET NULL,
  FOREIGN KEY (research_finding_id) REFERENCES research_findings(research_finding_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS design_hypotheses (
  design_hypothesis_id TEXT PRIMARY KEY,
  research_brief_id TEXT NOT NULL,
  hypothesis TEXT NOT NULL,
  rationale TEXT,
  falsification_test TEXT,
  evidence_link_ids_json TEXT NOT NULL DEFAULT '[]',
  confidence TEXT NOT NULL DEFAULT 'low',
  status TEXT NOT NULL DEFAULT 'proposed',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (research_brief_id) REFERENCES research_briefs(research_brief_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS parameter_recommendations (
  parameter_recommendation_id TEXT PRIMARY KEY,
  workflow_plan_id TEXT NOT NULL,
  node_key TEXT NOT NULL,
  model_name TEXT,
  parameter_key TEXT NOT NULL,
  recommended_value_json TEXT,
  default_value_json TEXT,
  recommended_range_json TEXT NOT NULL DEFAULT '{}',
  source_refs_json TEXT NOT NULL DEFAULT '[]',
  rationale TEXT,
  confidence TEXT NOT NULL DEFAULT 'inferred',
  validation_rules_json TEXT NOT NULL DEFAULT '{}',
  user_modified INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (workflow_plan_id) REFERENCES workflow_plans(workflow_plan_id) ON DELETE CASCADE,
  UNIQUE(workflow_plan_id, node_key, parameter_key)
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
CREATE INDEX IF NOT EXISTS idx_research_sources_type ON research_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_script_assets_model ON script_assets(model_plugin_id);
CREATE INDEX IF NOT EXISTS idx_parameter_catalog_model ON model_parameter_catalog(model_plugin_id);
CREATE INDEX IF NOT EXISTS idx_script_parameter_model ON script_parameter_observations(model_plugin_id);
CREATE INDEX IF NOT EXISTS idx_literature_documents_doi ON literature_documents(doi);
CREATE INDEX IF NOT EXISTS idx_literature_documents_pmid ON literature_documents(pmid);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_scientific_claims_document ON scientific_claims(document_id);
CREATE INDEX IF NOT EXISTS idx_scientific_claims_review ON scientific_claims(review_status);
CREATE INDEX IF NOT EXISTS idx_claim_evidence_claim ON claim_evidence(claim_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_project ON research_campaigns(project_id);
CREATE INDEX IF NOT EXISTS idx_campaign_rounds_campaign ON campaign_rounds(campaign_id, round_number);
CREATE INDEX IF NOT EXISTS idx_campaign_evaluations_round ON campaign_evaluations(campaign_round_id);
CREATE INDEX IF NOT EXISTS idx_campaign_decisions_round ON campaign_decisions(campaign_round_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_campaign_evaluation_round ON campaign_evaluations(campaign_round_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_campaign_decision_round ON campaign_decisions(campaign_round_id);
CREATE INDEX IF NOT EXISTS idx_literature_subscriptions_due ON literature_subscriptions(enabled, next_run_at);
CREATE INDEX IF NOT EXISTS idx_research_briefs_project ON research_briefs(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_research_findings_brief ON research_findings(research_brief_id, track);
CREATE INDEX IF NOT EXISTS idx_workflow_plans_brief ON workflow_plans(research_brief_id, created_at);
CREATE INDEX IF NOT EXISTS idx_research_questions_brief ON research_questions(research_brief_id, priority);
CREATE INDEX IF NOT EXISTS idx_research_runs_brief ON research_runs(research_brief_id, created_at);
CREATE INDEX IF NOT EXISTS idx_evidence_links_run ON evidence_links(research_run_id, review_status);
CREATE INDEX IF NOT EXISTS idx_candidates_project_id ON candidates(project_id);
CREATE INDEX IF NOT EXISTS idx_candidates_workflow_run_id ON candidates(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
CREATE INDEX IF NOT EXISTS idx_experiment_results_candidate_id ON experiment_results(candidate_id);
