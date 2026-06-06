-- Extended schema for BDA platform (Phase 2/3)

CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  workflow_run_id TEXT REFERENCES workflow_runs(workflow_run_id) ON DELETE SET NULL,
  node_run_id TEXT REFERENCES workflow_node_runs(node_run_id) ON DELETE SET NULL,
  compute_node_id TEXT REFERENCES compute_nodes(compute_node_id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  plugin_id TEXT,
  input_artifacts TEXT NOT NULL DEFAULT '{}',
  output_artifacts TEXT NOT NULL DEFAULT '{}',
  logs TEXT,
  error_message TEXT,
  external_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TEXT,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS job_events (
  event_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'researcher',
  display_name TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organizations (
  organization_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organization_members (
  organization_id TEXT NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member',
  PRIMARY KEY (organization_id, user_id)
);

CREATE TABLE IF NOT EXISTS project_members (
  project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'researcher',
  PRIMARY KEY (project_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_workflow_run_id ON jobs(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_node_run_id ON jobs(node_run_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_project_id ON audit_logs(project_id);

-- Add organization_id to projects if missing
-- Applied via migration script
