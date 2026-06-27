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
  interface_score: z.number().nullable(),
  pred_kd: z.string().nullable(),
  plddt: z.number().nullable(),
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

export const CandidateListSchema = z.object({
  items: z.array(CandidateSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
})

export type CandidateListResponse = z.infer<typeof CandidateListSchema>

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

export type { Project } from './project'
export { ProjectSchema } from './project'
export type { WorkflowNode } from './workflow'
export { WorkflowNodeSchema } from './workflow'
