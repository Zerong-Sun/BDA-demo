import { apiRequest } from './client'
import { fetchPaginatedList } from './pagination'
import {
  WorkflowNodeSchema,
  WorkflowGraphSchema,
  WorkflowRunSchema,
  type WorkflowGraph,
  type WorkflowLayout,
  type WorkflowNode,
  type WorkflowRun,
} from '../schemas/workflow'

export function listWorkflowNodes(workflowRunId: string): Promise<WorkflowNode[]> {
  return fetchPaginatedList(`/workflow-runs/${workflowRunId}/nodes`, WorkflowNodeSchema)
}

export function getWorkflowGraph(workflowRunId: string): Promise<WorkflowGraph> {
  return apiRequest<WorkflowGraph>(`/workflow-runs/${workflowRunId}/graph`, {}, WorkflowGraphSchema)
}

export interface SubmitWorkflowResponse {
  workflow_run_id: string
  status: string
  reason?: string
  message?: string
}

export function submitWorkflowRun(workflowRunId: string) {
  return apiRequest<SubmitWorkflowResponse>(
    `/workflow-runs/${workflowRunId}/submit-to-compute`,
    { method: 'POST' },
  )
}

export function createWorkflowRun(projectId: string) {
  return apiRequest<WorkflowRun>(`/projects/${projectId}/workflow-runs`, { method: 'POST' }, WorkflowRunSchema)
}

export function addWorkflowNode(
  workflowRunId: string,
  payload: {
    node_type: string
    node_name: string
    model_name?: string
    model_version?: string
    model_plugin_id?: string
    parameters_json?: Record<string, unknown>
    position?: { x: number; y: number }
  },
) {
  return apiRequest<WorkflowNode>(
    `/workflow-runs/${workflowRunId}/nodes`,
    { method: 'POST', body: JSON.stringify(payload) },
    WorkflowNodeSchema,
  )
}

export function saveWorkflowLayout(workflowRunId: string, layout: WorkflowLayout) {
  return apiRequest<WorkflowGraph>(
    `/workflow-runs/${workflowRunId}/graph`,
    { method: 'PATCH', body: JSON.stringify(layout) },
    WorkflowGraphSchema,
  ).then((graph) => WorkflowRunSchema.parse(graph.workflow_run))
}

export function validateWorkflowRun(workflowRunId: string) {
  return apiRequest<{ valid: boolean; errors: Array<Record<string, unknown>>; warnings: Array<Record<string, unknown>> }>(
    `/workflow-runs/${workflowRunId}/validate`,
    { method: 'POST' },
  )
}

export function deleteWorkflowNode(workflowRunId: string, nodeRunId: string) {
  return apiRequest<{ deleted: string }>(`/workflow-runs/${workflowRunId}/nodes/${nodeRunId}`, {
    method: 'DELETE',
  })
}

export function updateWorkflowNode(
  workflowRunId: string,
  nodeRunId: string,
  payload: {
    parameters_json?: Record<string, unknown>
    input_files_json?: Record<string, unknown> | Array<unknown>
    status?: string
  },
) {
  return apiRequest<WorkflowNode>(
    `/workflow-runs/${workflowRunId}/nodes/${nodeRunId}`,
    { method: 'PATCH', body: JSON.stringify(payload) },
    WorkflowNodeSchema,
  )
}

export interface NodeSubmissionPreview {
  node_run_id: string
  ready: boolean
  blockers: Array<{
    code: string
    message: string
    source_node_run_id?: string
    source_node_name?: string
    source_status?: string
  }>
  parameter_checksum: string
  model_name?: string | null
  plugin_id?: string | null
  container_image?: string | null
  resources: Record<string, unknown>
  command: string
  inputs: Record<string, unknown>
  expected_outputs: Record<string, unknown>
  model_command_preview?: string
  requires_confirmation: boolean
  validation: {
    valid: boolean
    errors: Array<{ parameter: string; message: string }>
    warnings: Array<{ parameter: string; message: string }>
  }
}

export function previewWorkflowNodeSubmission(nodeRunId: string) {
  return apiRequest<NodeSubmissionPreview>(
    `/workflow-node-runs/${nodeRunId}/submission-preview`,
  )
}

export function submitWorkflowNode(nodeRunId: string, parameterChecksum: string) {
  return apiRequest<{ node_run_id: string; job_id: string; status: string }>(
    `/workflow-node-runs/${nodeRunId}/submit-to-compute`,
    {
      method: 'POST',
      body: JSON.stringify({ expected_parameter_checksum: parameterChecksum }),
    },
  )
}

export function completeWorkflowNodeReview(nodeRunId: string) {
  return apiRequest<WorkflowNode>(
    `/workflow-node-runs/${nodeRunId}/complete-review`,
    { method: 'POST' },
    WorkflowNodeSchema,
  )
}

export interface AutomationPolicy {
  workflow_run_id: string
  mode: 'confirm_each_node' | 'auto_after_gate' | 'advisory_only'
  auto_submit_ready: boolean
  notify_on_ready: boolean
  notify_on_terminal: boolean
  max_auto_retries: number
  retry_backoff_seconds: number
}

export function getWorkflowAutomationPolicy(workflowRunId: string) {
  return apiRequest<AutomationPolicy>(
    `/workflow-runs/${workflowRunId}/automation-policy`,
  )
}

export function updateWorkflowAutomationPolicy(
  workflowRunId: string,
  payload: Omit<AutomationPolicy, 'workflow_run_id'>,
) {
  return apiRequest<AutomationPolicy>(
    `/workflow-runs/${workflowRunId}/automation-policy`,
    { method: 'PATCH', body: JSON.stringify(payload) },
  )
}

export function evaluateReadyWorkflowNodes(workflowRunId: string) {
  return apiRequest<{
    ready_nodes: string[]
    waiting_external_nodes: string[]
    auto_submitted_job_ids: string[]
  }>(
    `/workflow-runs/${workflowRunId}/evaluate-ready-nodes`,
    { method: 'POST' },
  )
}
