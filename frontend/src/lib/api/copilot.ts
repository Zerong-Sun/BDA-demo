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

export const ClusterDraftSchema = z.object({
  draft_id: z.string(),
  project_id: z.string().nullable().optional(),
  status: z.string(),
  job_name: z.string(),
  queue: z.string(),
  gpu_count: z.number(),
  cpu_count: z.number(),
  rationale: z.string().nullable().optional(),
  script: z.string(),
  script_sha256: z.string(),
  external_id: z.string().nullable().optional(),
  logs: z.string().optional(),
  output_files: z.array(z.object({
    path: z.string(),
    size_bytes: z.number(),
  })).optional(),
  created_at: z.string(),
})

export type ClusterDraft = z.infer<typeof ClusterDraftSchema>

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

export function testCopilotConfig() {
  return apiRequest<{
    connected: boolean
    model: string
    sample?: string
    reason?: string
  }>('/copilot/config/test', { method: 'POST' })
}

export function listClusterDrafts(projectId?: string) {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
  return apiRequest<{ items: ClusterDraft[] }>(
    `/copilot/cluster/drafts${query}`,
    {},
    z.object({ items: z.array(ClusterDraftSchema) }),
  )
}

export function getClusterDraft(draftId: string) {
  return apiRequest<ClusterDraft>(
    `/copilot/cluster/drafts/${draftId}`,
    {},
    ClusterDraftSchema,
  )
}

export function confirmClusterDraft(draftId: string) {
  return apiRequest<ClusterDraft>(
    `/copilot/cluster/drafts/${draftId}/confirm`,
    { method: 'POST' },
    ClusterDraftSchema,
  )
}

export function clusterOutputUrl(draftId: string, path: string) {
  return `${API_BASE}/copilot/cluster/drafts/${draftId}/download?path=${encodeURIComponent(path)}`
}

export async function downloadClusterOutput(draftId: string, path: string) {
  const token = sessionStorage.getItem('bda_token')
  const response = await fetch(clusterOutputUrl(draftId, path), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error('Failed to download cluster output')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = path.split('/').pop() || 'cluster-output'
  link.click()
  URL.revokeObjectURL(url)
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

export function ingestLiterature(query: string, limit = 5) {
  return apiRequest<Record<string, unknown>>('/copilot/literature/ingest', {
    method: 'POST',
    body: JSON.stringify({
      query,
      limit,
      fetch_full_text: true,
      extract_claims: true,
    }),
  })
}

export function searchLiteratureLibrary(query: string) {
  return apiRequest<{ items: Array<Record<string, unknown>>; total: number }>(
    `/copilot/literature?q=${encodeURIComponent(query)}`,
  )
}

export function listLiteratureClaims(reviewStatus = 'pending_review') {
  return apiRequest<{ items: Array<Record<string, unknown>>; total: number }>(
    `/copilot/literature/claims?review_status=${encodeURIComponent(reviewStatus)}`,
  )
}

export function reviewLiteratureClaim(claimId: string, reviewStatus: 'accepted' | 'rejected') {
  return apiRequest<Record<string, unknown>>(
    `/copilot/literature/claims/${claimId}`,
    { method: 'PATCH', body: JSON.stringify({ review_status: reviewStatus }) },
  )
}

export function listLiteratureRelations(reviewStatus = 'pending_review') {
  return apiRequest<{ items: Array<Record<string, unknown>>; total: number }>(
    `/copilot/literature/relations?review_status=${encodeURIComponent(reviewStatus)}`,
  )
}

export function reviewLiteratureRelation(relationId: string, reviewStatus: 'accepted' | 'rejected') {
  return apiRequest<Record<string, unknown>>(
    `/copilot/literature/relations/${relationId}`,
    { method: 'PATCH', body: JSON.stringify({ review_status: reviewStatus }) },
  )
}

export function detectLiteratureRelations(acceptedOnly = false) {
  return apiRequest<Record<string, unknown>>(
    '/copilot/literature/relations/detect',
    {
      method: 'POST',
      body: JSON.stringify({ limit: 30, accepted_only: acceptedOnly }),
    },
  )
}

export interface LiteratureSubscription {
  subscription_id: string
  name: string
  query: string
  enabled: boolean
  interval_hours: number
  result_limit: number
  fetch_full_text: boolean
  extract_claims: boolean
  last_status?: string | null
  last_run_at?: string | null
  next_run_at: string
}

export function listLiteratureSubscriptions() {
  return apiRequest<{ items: LiteratureSubscription[]; total: number }>(
    '/copilot/literature/subscriptions',
  )
}

export function createLiteratureSubscription(payload: Omit<LiteratureSubscription, 'subscription_id' | 'last_status' | 'last_run_at' | 'next_run_at'>) {
  return apiRequest<LiteratureSubscription>(
    '/copilot/literature/subscriptions',
    { method: 'POST', body: JSON.stringify(payload) },
  )
}

export function updateLiteratureSubscription(
  subscriptionId: string,
  payload: Omit<LiteratureSubscription, 'subscription_id' | 'last_status' | 'last_run_at' | 'next_run_at'>,
) {
  return apiRequest<LiteratureSubscription>(
    `/copilot/literature/subscriptions/${subscriptionId}`,
    { method: 'PATCH', body: JSON.stringify(payload) },
  )
}

export function runLiteratureSubscription(subscriptionId: string) {
  return apiRequest<Record<string, unknown>>(
    `/copilot/literature/subscriptions/${subscriptionId}/run`,
    { method: 'POST' },
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
