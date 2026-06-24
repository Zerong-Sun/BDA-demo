import { z } from 'zod'

import { apiRequest } from './client'

const CampaignRoundSchema = z.object({
  campaign_round_id: z.string(),
  campaign_id: z.string(),
  round_number: z.number(),
  workflow_run_id: z.string(),
  parent_round_id: z.string().nullable().optional(),
  status: z.string(),
  parameter_patch_json: z.record(z.string(), z.unknown()).optional(),
  approval_status: z.string(),
  evaluations: z.array(z.record(z.string(), z.unknown())).optional(),
  decisions: z.array(z.record(z.string(), z.unknown())).optional(),
})

export const CampaignSchema = z.object({
  campaign_id: z.string(),
  project_id: z.string(),
  name: z.string(),
  objective: z.string(),
  status: z.string(),
  max_rounds: z.number(),
  current_round: z.number(),
  budget_json: z.record(z.string(), z.unknown()),
  stop_conditions_json: z.array(z.record(z.string(), z.unknown())),
  strategy_json: z.record(z.string(), z.unknown()),
  rounds: z.array(CampaignRoundSchema).optional(),
})

export type Campaign = z.infer<typeof CampaignSchema>

export interface CreateCampaignPayload {
  project_id: string
  name: string
  objective: string
  initial_workflow_run_id?: string
  max_rounds?: number
  budget?: Record<string, unknown>
  stop_conditions?: Array<Record<string, unknown>>
  strategy?: Record<string, unknown>
}

export function createCampaign(payload: CreateCampaignPayload) {
  return apiRequest<Campaign>(
    '/campaigns',
    { method: 'POST', body: JSON.stringify(payload) },
    CampaignSchema,
  )
}

export function listProjectCampaigns(projectId: string) {
  return apiRequest<{ items: Campaign[]; total: number }>(
    `/projects/${projectId}/campaigns`,
    {},
    z.object({ items: z.array(CampaignSchema), total: z.number() }),
  )
}

export function getCampaign(campaignId: string) {
  return apiRequest<Campaign>(`/campaigns/${campaignId}`, {}, CampaignSchema)
}

export function evaluateCampaignRound(campaignId: string, roundNumber: number) {
  return apiRequest<Record<string, unknown>>(
    `/campaigns/${campaignId}/rounds/${roundNumber}/evaluate`,
    { method: 'POST' },
  )
}

export function updateCampaignDecision(
  decisionId: string,
  parameterPatch: Record<string, unknown>,
  rationale?: string,
) {
  return apiRequest<Record<string, unknown>>(
    `/campaign-decisions/${decisionId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        parameter_patch: parameterPatch,
        rationale,
      }),
    },
  )
}

export function reviewCampaignDecision(decisionId: string, approve: boolean) {
  return apiRequest<Record<string, unknown>>(
    `/campaign-decisions/${decisionId}/review`,
    { method: 'POST', body: JSON.stringify({ approve }) },
  )
}
