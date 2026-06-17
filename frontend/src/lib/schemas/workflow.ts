import { z } from 'zod'
import { ArtifactSchema } from './artifact'

export const WorkflowNodeSchema = z.object({
  node_run_id: z.string(),
  workflow_run_id: z.string(),
  node_type: z.string(),
  node_name: z.string(),
  status: z.string(),
  model_name: z.string().nullable().optional(),
  model_version: z.string().nullable().optional(),
  input_files_json: z.union([z.string(), z.array(z.unknown()), z.record(z.string(), z.unknown())]).nullable().optional(),
  output_files_json: z.union([z.string(), z.array(z.unknown()), z.record(z.string(), z.unknown())]).nullable().optional(),
  parameters_json: z.union([z.string(), z.record(z.string(), z.unknown())]).nullable().optional(),
  metrics_json: z.union([z.string(), z.record(z.string(), z.unknown())]).nullable().optional(),
  logs: z.string().nullable().optional(),
  position_json: z.string().nullable().optional(),
})

export type WorkflowNode = z.infer<typeof WorkflowNodeSchema>

export const WorkflowEdgeSchema = z.object({
  edge_id: z.string(),
  workflow_run_id: z.string(),
  source_node_run_id: z.string(),
  source_port: z.string(),
  target_node_run_id: z.string(),
  target_port: z.string(),
  edge_type: z.string(),
  metadata_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  created_at: z.string().optional(),
})

export type WorkflowEdge = z.infer<typeof WorkflowEdgeSchema>

export const WorkflowRunSchema = z.object({
  workflow_run_id: z.string(),
  task_id: z.string(),
  status: z.string(),
  summary_metrics_json: z.union([z.record(z.string(), z.unknown()), z.string()]).optional(),
  layout_json: z.string().nullable().optional(),
})

export type WorkflowRun = z.infer<typeof WorkflowRunSchema>

const JobLikeSchema = z.object({
  job_id: z.string(),
}).passthrough()

export const WorkflowGraphSchema = z.object({
  workflow_run: WorkflowRunSchema,
  nodes: z.array(WorkflowNodeSchema),
  edges: z.array(WorkflowEdgeSchema),
  artifacts: z.array(ArtifactSchema),
  jobs: z.array(JobLikeSchema),
})

export type WorkflowGraph = z.infer<typeof WorkflowGraphSchema>

export const WorkflowLayoutSchema = z.object({
  nodes: z.array(
    z.object({
      node_run_id: z.string(),
      position: z.object({ x: z.number(), y: z.number() }),
    }),
  ),
  edges: z.array(
    z.object({
      id: z.string().optional(),
      edge_id: z.string().optional(),
      source: z.string().optional(),
      target: z.string().optional(),
      source_node_run_id: z.string().optional(),
      target_node_run_id: z.string().optional(),
      source_port: z.string().optional(),
      target_port: z.string().optional(),
      edge_type: z.string().optional(),
    }),
  ),
})

export type WorkflowLayout = z.infer<typeof WorkflowLayoutSchema>
