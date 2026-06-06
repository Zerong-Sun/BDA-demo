import { z } from 'zod'

export const CandidateSchema = z.object({
  candidate_id: z.string(),
  project_id: z.string(),
  task_id: z.string().nullable().optional(),
  workflow_run_id: z.string().nullable().optional(),
  family: z.string().nullable(),
  sequence: z.string().nullable().optional(),
  structure_file_path: z.string().nullable().optional(),
  complex_file_path: z.string().nullable().optional(),
  interface_score: z.number(),
  pred_kd: z.string(),
  plddt: z.number(),
  interface_pae: z.number().nullable().optional(),
  rosetta_score: z.number().nullable().optional(),
  interface_energy: z.number().nullable().optional(),
  clash_count: z.number().nullable().optional(),
  buried_sasa: z.number().nullable().optional(),
  solubility_score: z.number().nullable().optional(),
  aggregation_risk: z.string().nullable().optional(),
  expression_risk: z.string().nullable().optional(),
  status: z.string(),
  decision: z.string().nullable(),
  next_action: z.string().nullable().optional(),
})

export type Candidate = z.infer<typeof CandidateSchema>

export const ProjectSchema = z.object({
  project_id: z.string(),
  project_name: z.string(),
  project_type: z.string(),
  status: z.string(),
  owner_id: z.string().nullable().optional(),
  summary: z.string().nullable().optional(),
})

export type Project = z.infer<typeof ProjectSchema>

export const ExperimentResultSchema = z.object({
  result_id: z.string(),
  experiment_batch_id: z.string().nullable().optional(),
  candidate_id: z.string(),
  experiment_type: z.string(),
  pass_status: z.string(),
  value: z.string().nullable().optional(),
  unit: z.string().nullable().optional(),
  conclusion: z.string().nullable().optional(),
  failure_reason: z.string().nullable().optional(),
})

export type ExperimentResult = z.infer<typeof ExperimentResultSchema>

export const WorkflowNodeSchema = z.object({
  node_run_id: z.string(),
  workflow_run_id: z.string(),
  node_type: z.string(),
  node_name: z.string(),
  status: z.string(),
  model_name: z.string().nullable().optional(),
  model_version: z.string().nullable().optional(),
  parameters_json: z.string().nullable().optional(),
  metrics_json: z.union([z.string(), z.record(z.string(), z.unknown())]).nullable().optional(),
  logs: z.string().nullable().optional(),
})

export type WorkflowNode = z.infer<typeof WorkflowNodeSchema>
