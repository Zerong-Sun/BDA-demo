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

export const CopilotConfigSchema = z.object({
  llm_api_base: z.string(),
  llm_model: z.string(),
  api_key_configured: z.boolean(),
  api_key_preview: z.string().nullable(),
  system_scope: z.string(),
  system_prompt: z.string(),
})

export type CopilotConfig = z.infer<typeof CopilotConfigSchema>

export const CopilotKnowledgeEntrySchema = z.object({
  knowledge_entry_id: z.string(),
  title: z.string(),
  category: z.string(),
  subcategory: z.string().nullable().optional(),
  summary: z.string(),
  content: z.string(),
  tags_json: z.array(z.string()).optional(),
  related_model_plugins: z.array(z.string()).optional(),
  related_method_plugins: z.array(z.string()).optional(),
  source_type: z.string(),
  citation: z.string().nullable().optional(),
  confidence: z.string(),
  metadata_json: z.record(z.string(), z.unknown()).optional(),
  status: z.string(),
})

export type CopilotKnowledgeEntry = z.infer<typeof CopilotKnowledgeEntrySchema>

export interface CopilotConfigUpdate {
  llm_api_base?: string
  llm_api_key?: string
  llm_model?: string
}

export function getCopilotConfig() {
  return apiRequest<CopilotConfig>('/copilot/config', {}, CopilotConfigSchema)
}

export function updateCopilotConfig(payload: CopilotConfigUpdate) {
  return apiRequest<CopilotConfig>(
    '/copilot/config',
    { method: 'PUT', body: JSON.stringify(payload) },
    CopilotConfigSchema,
  )
}

export function searchCopilotKnowledge(query: string, category?: string) {
  const params = new URLSearchParams({ q: query })
  if (category) params.set('category', category)
  return apiRequest<{ items: CopilotKnowledgeEntry[]; total: number; query: string }>(
    `/copilot/knowledge?${params.toString()}`,
    {},
    z.object({
      items: z.array(CopilotKnowledgeEntrySchema),
      total: z.number(),
      query: z.string(),
    }),
  )
}

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
