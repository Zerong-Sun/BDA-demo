import { z } from 'zod'

export const ProjectSchema = z.object({
  project_id: z.string(),
  project_name: z.string(),
  project_type: z.string(),
  status: z.string(),
  owner_id: z.string().nullable().optional(),
  summary: z.string().nullable().optional(),
})

export type Project = z.infer<typeof ProjectSchema>

export const ProjectOverviewSchema = z.object({
  project: ProjectSchema,
  funnel: z.object({
    generated: z.number(),
    designed: z.number(),
    folded: z.number(),
    scored: z.number(),
    ordered: z.number(),
  }),
  results_summary: z
    .object({
      hit_count: z.number(),
      ordered_count: z.number(),
      hit_rate_pct: z.number(),
      hit_rate_label: z.string(),
      best_kd: z.string(),
      best_kd_candidate: z.string().nullable().optional(),
      main_failure: z.string(),
      main_failure_detail: z.string(),
      sec_failure_count: z.number(),
      decision: z.string(),
      decision_detail: z.string(),
      experiment_summary: z.string().nullable().optional(),
    })
    .nullable()
    .optional(),
  compute_status: z.object({
    gpu_available: z.boolean(),
    cpu_available: z.boolean(),
    label: z.string(),
  }),
  next_action: z.string(),
})

export type ProjectOverview = z.infer<typeof ProjectOverviewSchema>
