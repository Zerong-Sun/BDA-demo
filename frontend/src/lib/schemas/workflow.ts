import { z } from 'zod'

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
  position_json: z.string().nullable().optional(),
})

export type WorkflowNode = z.infer<typeof WorkflowNodeSchema>

export const WorkflowRunSchema = z.object({
  workflow_run_id: z.string(),
  task_id: z.string(),
  status: z.string(),
  summary_metrics_json: z.union([z.record(z.string(), z.unknown()), z.string()]).optional(),
  layout_json: z.string().nullable().optional(),
})

export type WorkflowRun = z.infer<typeof WorkflowRunSchema>

export const WorkflowLayoutSchema = z.object({
  nodes: z.array(
    z.object({
      node_run_id: z.string(),
      position: z.object({ x: z.number(), y: z.number() }),
    }),
  ),
  edges: z.array(
    z.object({
      id: z.string(),
      source: z.string(),
      target: z.string(),
    }),
  ),
})

export type WorkflowLayout = z.infer<typeof WorkflowLayoutSchema>
