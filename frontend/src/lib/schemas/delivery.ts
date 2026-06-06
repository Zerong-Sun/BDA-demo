import { z } from 'zod'

export const DeliveryPackageSchema = z.object({
  package_id: z.string(),
  project_id: z.string(),
  candidate_ids: z.union([z.array(z.string()), z.string()]),
  report_file: z.string().nullable().optional(),
  fasta_file: z.string().nullable().optional(),
  structure_bundle: z.string().nullable().optional(),
  score_table: z.string().nullable().optional(),
  experiment_summary: z.string().nullable().optional(),
  redesign_constraints: z.union([z.record(z.string(), z.unknown()), z.string()]).optional(),
})

export type DeliveryPackageData = z.infer<typeof DeliveryPackageSchema>

export const ResultsSummarySchema = z.object({
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

export type ResultsSummary = z.infer<typeof ResultsSummarySchema>

export const CandidateFunnelSchema = z.object({
  generated: z.number(),
  designed: z.number(),
  folded: z.number(),
  scored: z.number(),
  ordered: z.number(),
})

export type CandidateFunnel = z.infer<typeof CandidateFunnelSchema>
