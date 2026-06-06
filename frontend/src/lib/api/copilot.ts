import { apiRequest } from './client'

/** Phase 2: DeepSeek / local LLM integration point */
export interface CopilotMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface CopilotChatRequest {
  messages: CopilotMessage[]
  project_id?: string
  skill?: string
}

export interface CopilotChatResponse {
  mode: 'rule_based_demo' | 'llm'
  message: string
  skill_used?: string
  structured?: Record<string, unknown>
}

export function sendCopilotMessage(payload: CopilotChatRequest) {
  return apiRequest<CopilotChatResponse>('/copilot/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function planRoute(projectId: string, target = 'PD-1') {
  return apiRequest<Record<string, unknown>>('/copilot/route-plan', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId, target }),
  })
}
