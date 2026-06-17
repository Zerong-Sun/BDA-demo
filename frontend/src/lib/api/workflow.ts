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
