import { z } from 'zod'

export const JobSchema = z.object({
  job_id: z.string(),
  workflow_run_id: z.string().nullable().optional(),
  node_run_id: z.string().nullable().optional(),
  compute_node_id: z.string().nullable().optional(),
  status: z.string(),
  plugin_id: z.string().nullable().optional(),
  input_artifacts: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  output_artifacts: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  logs: z.string().nullable().optional(),
  error_message: z.string().nullable().optional(),
  created_at: z.string().optional(),
  started_at: z.string().nullable().optional(),
  finished_at: z.string().nullable().optional(),
})

export type Job = z.infer<typeof JobSchema>
