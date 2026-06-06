import { apiRequest } from './client'
import { z } from 'zod'

export interface CopilotMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface CopilotChatRequest {
  messages: CopilotMessage[]
  project_id?: string
  skill?: string
}

export const CopilotChatResponseSchema = z.object({
  mode: z.enum(['rule_based_demo', 'llm']),
  message: z.string(),
  skill_used: z.string().optional(),
  structured: z.record(z.string(), z.unknown()).optional(),
})

export type CopilotChatResponse = z.infer<typeof CopilotChatResponseSchema>

export function sendCopilotMessage(payload: CopilotChatRequest) {
  return apiRequest<CopilotChatResponse>(
    '/copilot/chat',
    { method: 'POST', body: JSON.stringify(payload) },
    CopilotChatResponseSchema,
  )
}

export function planRoute(projectId: string, target = 'PD-1') {
  return apiRequest<Record<string, unknown>>('/copilot/route-plan', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId, target }),
  })
}

export function explainCandidate(candidateId: string) {
  return apiRequest<{ candidate_id: string; recommendation: string; reasons: string[] }>(
    '/copilot/candidate-explanation',
    { method: 'POST', body: JSON.stringify({ candidate_id: candidateId }) },
    z.object({
      candidate_id: z.string(),
      recommendation: z.string(),
      reasons: z.array(z.string()),
    }),
  )
}

export function interpretResults(projectId: string) {
  return apiRequest<Record<string, unknown>>('/copilot/result-interpretation', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId }),
  })
}
