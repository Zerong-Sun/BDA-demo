import { apiRequest, API_BASE } from './client'
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
  mode: z.string(),
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

export async function streamCopilotMessage(
  payload: CopilotChatRequest,
  onChunk: (text: string) => void,
): Promise<void> {
  const token = sessionStorage.getItem('bda_token')
  const response = await fetch(`${API_BASE}/copilot/chat/stream`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })
  if (!response.ok || !response.body) {
    const fallback = await sendCopilotMessage(payload)
    onChunk(fallback.message)
    return
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''
    for (const evt of events) {
      const dataLine = evt.split('\n').find((l) => l.startsWith('data:'))
      const eventLine = evt.split('\n').find((l) => l.startsWith('event:'))
      if (dataLine && eventLine?.includes('message')) {
        onChunk(dataLine.slice(5).trimStart())
      }
    }
  }
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
