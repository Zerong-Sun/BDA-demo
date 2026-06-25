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

export interface ResearchBrief {
  research_brief_id: string
  project_id: string
  title: string
  objective: string
  product_context: string
  constraints_json: Record<string, unknown>
  source_material_json: Array<Record<string, unknown>>
  assumptions_json: Array<Record<string, unknown>>
  status: string
}

export interface SweetProteinRoute {
  route_id: string
  name: string
  recommendation: string
  generation: string
  rationale: string
  key_risks: string[]
  required_evidence?: string[]
  expected_benefits?: string[]
}

export interface WorkflowPlan {
  workflow_plan_id: string
  research_brief_id: string
  project_id: string
  name: string
  version?: number
  supersedes_workflow_plan_id?: string | null
  selected_route?: string | null
  route_options_json: SweetProteinRoute[]
  dossier_json: Record<string, unknown>
  nodes_json: Array<Record<string, unknown>>
  edges_json: Array<Record<string, unknown>>
  status: string
  materialized_workflow_run_id?: string | null
  parameter_recommendations?: Array<Record<string, unknown>>
  decision_gates?: Array<Record<string, unknown>>
}

export interface ResearchEvidence {
  evidence_link_id: string
  research_question_id?: string | null
  source_type: string
  source_identifier?: string | null
  title: string
  uri?: string | null
  evidence_excerpt?: string | null
  evidence_level: string
  review_status: string
  metadata_json?: Record<string, unknown>
}

export interface ResearchRun {
  research_run_id: string
  research_brief_id: string
  status: string
  progress_json: Record<string, unknown>
  result_summary_json: Record<string, unknown>
  evidence: ResearchEvidence[]
  questions: Array<Record<string, unknown>>
}

export interface ExperimentPlanStep {
  experiment_plan_step_id: string
  stage_key: string
  stage_order: number
  title: string
  purpose: string
  samples_json: unknown[]
  controls_json: unknown[]
  readouts_json: unknown[]
  acceptance_criteria_json: unknown[]
  dependencies_json: unknown[]
  owner?: string | null
  safety_level: string
  status: string
  result_artifact_id?: string | null
  notes?: string | null
  updated_at: string
}

export interface ExperimentPlan {
  experiment_plan_id: string
  project_id: string
  workflow_run_id?: string | null
  node_run_id?: string | null
  title: string
  objective: string
  status: string
  ethics_requirements_json: Array<Record<string, unknown>>
  regulatory_questions_json: Array<Record<string, unknown>>
  result_template_json: Record<string, unknown>
  steps: ExperimentPlanStep[]
}

export interface ParameterRecommendation {
  parameter_recommendation_id: string
  parameter_key: string
  model_name: string
  recommended_value_json: unknown
  default_value_json: unknown
  recommended_range_json: Record<string, unknown>
  source_refs_json: string[]
  rationale?: string
  confidence?: string
  user_modified: boolean
  current_value: unknown
  differs_from_recommendation: boolean
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

export interface PlannedWorkflowStep {
  template_id: 'rf' | 'mpnn' | 'af2' | 'rosetta' | 'filter' | 'lab'
  name: string
  methods: string[]
  parameters: Record<string, unknown>
  estimate: {
    planned: number
    unit: string
    duration: string
  }
}

export interface PlannedWorkflowRoute {
  mode: 'llm_validated' | 'validated_fallback'
  summary?: string
  assumptions?: string[]
  risks?: string[]
  fallback_reason?: string
  steps: PlannedWorkflowStep[]
}

export function planRoute(
  projectId: string,
  goal: string,
  objective = 'protein_design',
  constraints: Record<string, unknown> = {},
) {
  return apiRequest<PlannedWorkflowRoute>('/copilot/route-plan', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      target: goal,
      objective,
      constraints,
    }),
  })
}

export function createResearchBrief(payload: {
  project_id: string
  title: string
  objective: string
  product_context?: string
  constraints?: Record<string, unknown>
  source_material?: Array<Record<string, unknown>>
}) {
  return apiRequest<ResearchBrief>('/copilot/research-briefs', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listResearchBriefs(projectId: string) {
  return apiRequest<{ items: ResearchBrief[]; total: number }>(
    `/copilot/research-briefs?project_id=${encodeURIComponent(projectId)}`,
  )
}

export function ingestResearchMarkdown(
  researchBriefId: string,
  payload: { title: string; content: string; source_uri?: string },
) {
  return apiRequest<{
    source_id: string
    document_id: string
    title: string
    chunk_count: number
    reference_count: number
    references: string[]
  }>(
    `/copilot/research-briefs/${researchBriefId}/sources/markdown`,
    { method: 'POST', body: JSON.stringify(payload) },
  )
}

export function generateResearchPlan(researchBriefId: string, selectedRoute?: string) {
  return apiRequest<WorkflowPlan>(
    `/copilot/research-briefs/${researchBriefId}/plan`,
    {
      method: 'POST',
      body: JSON.stringify({ selected_route: selectedRoute ?? null }),
    },
  )
}

export function createResearchRun(researchBriefId: string) {
  return apiRequest<ResearchRun>(
    `/copilot/research-briefs/${researchBriefId}/research-runs`,
    { method: 'POST' },
  )
}

export function startResearchRun(researchRunId: string) {
  return apiRequest<ResearchRun>(
    `/copilot/research-runs/${researchRunId}/start`,
    { method: 'POST' },
  )
}

export function reviewResearchEvidence(
  evidenceLinkId: string,
  reviewStatus: 'accepted' | 'rejected' | 'pending_review',
) {
  return apiRequest<ResearchEvidence>(
    `/copilot/research-evidence/${evidenceLinkId}`,
    { method: 'PATCH', body: JSON.stringify({ review_status: reviewStatus }) },
  )
}

export function researchDossierExportUrl(researchBriefId: string, format: 'markdown' | 'json') {
  return `${API_BASE}/copilot/research-briefs/${researchBriefId}/dossier-export?format=${format}`
}

export async function downloadResearchDossier(
  researchBriefId: string,
  format: 'markdown' | 'json',
) {
  const token = sessionStorage.getItem('bda_token')
  const response = await fetch(researchDossierExportUrl(researchBriefId, format), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error('Failed to export research dossier')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${researchBriefId}.${format === 'markdown' ? 'md' : 'json'}`
  link.click()
  URL.revokeObjectURL(url)
}

export function materializeWorkflowPlan(workflowPlanId: string, selectedRoute: string) {
  return apiRequest<{
    workflow_plan_id: string
    workflow_run_id: string
    selected_route: string
    nodes: Array<Record<string, unknown>>
    edges: Array<Record<string, unknown>>
  }>(
    `/copilot/workflow-plans/${workflowPlanId}/materialize`,
    {
      method: 'POST',
      body: JSON.stringify({ selected_route: selectedRoute }),
    },
  )
}

export function getWorkflowExperimentPlan(workflowRunId: string) {
  return apiRequest<ExperimentPlan>(
    `/copilot/workflow-runs/${workflowRunId}/experiment-plan`,
  )
}

export function getWorkflowParameterRecommendations(
  workflowRunId: string,
  nodeRunId: string,
) {
  return apiRequest<{ items: ParameterRecommendation[]; total: number }>(
    `/copilot/workflow-runs/${workflowRunId}/parameter-recommendations?node_run_id=${encodeURIComponent(nodeRunId)}`,
  )
}

export function experimentResultTemplateUrl(
  experimentPlanId: string,
  format: 'csv' | 'xlsx' | 'json' = 'csv',
) {
  return `${API_BASE}/copilot/experiment-plans/${experimentPlanId}/result-template?format=${format}`
}

export async function downloadExperimentResultTemplate(
  experimentPlanId: string,
  format: 'csv' | 'xlsx' | 'json',
) {
  const token = sessionStorage.getItem('bda_token')
  const response = await fetch(experimentResultTemplateUrl(experimentPlanId, format), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error('Failed to download experiment result template')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${experimentPlanId}-results.${format}`
  link.click()
  URL.revokeObjectURL(url)
}

export interface SequenceComparison {
  reference: { name: string; sequence: string }
  sequences: Array<{ name: string; length: number }>
  alignments: Array<{
    reference: string
    query: string
    aligned_reference: string
    aligned_query: string
    score: number
    identity: number
    coverage: number
  }>
  conserved_reference_positions: number[]
  note: string
}

export interface StructureComparison {
  reference_artifact_id: string
  comparisons: Array<{
    reference_artifact_id: string
    query_artifact_id: string
    reference_name: string
    query_name: string
    reference_ca_count: number
    query_ca_count: number
    paired_ca_count: number
    ca_rmsd: number
    coverage: number
  }>
  note: string
}

export function compareResearchSequences(
  researchBriefId: string,
  sequences: Array<{ name: string; sequence: string }>,
) {
  return apiRequest<SequenceComparison>(
    `/copilot/research-briefs/${researchBriefId}/sequence-comparison`,
    { method: 'POST', body: JSON.stringify({ sequences }) },
  )
}

export function compareResearchStructures(
  researchBriefId: string,
  artifactIds: string[],
) {
  return apiRequest<StructureComparison>(
    `/copilot/research-briefs/${researchBriefId}/structure-comparison`,
    { method: 'POST', body: JSON.stringify({ artifact_ids: artifactIds }) },
  )
}

export function updateExperimentPlanStep(
  stepId: string,
  payload: Partial<{
    title: string
    purpose: string
    samples: unknown[]
    controls: unknown[]
    readouts: unknown[]
    acceptance_criteria: unknown[]
    dependencies: unknown[]
    owner: string
    status: string
    result_artifact_id: string
    notes: string
  }>,
) {
  return apiRequest<{ step: ExperimentPlanStep; plan: ExperimentPlan }>(
    `/copilot/experiment-plan-steps/${stepId}`,
    { method: 'PATCH', body: JSON.stringify(payload) },
  )
}

export function listNotifications(projectId?: string) {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
  return apiRequest<{ items: Array<Record<string, unknown>>; total: number }>(
    `/copilot/notifications${query}`,
  )
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
