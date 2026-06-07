import { apiRequest } from './client'
import {
  WorkflowNodeSchema,
  WorkflowRunSchema,
  type WorkflowLayout,
  type WorkflowNode,
  type WorkflowRun,
} from '../schemas/workflow'
import { z } from 'zod'

const PaginatedNodesSchema = z.object({
  items: z.array(WorkflowNodeSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
})

export function listWorkflowNodes(workflowRunId: string): Promise<WorkflowNode[]> {
  return apiRequest(`/workflow-runs/${workflowRunId}/nodes`, {}, PaginatedNodesSchema).then(
    (page) => page.items,
  )
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
  return apiRequest<WorkflowRun>(
    `/workflow-runs/${workflowRunId}/layout`,
    { method: 'PATCH', body: JSON.stringify(layout) },
    WorkflowRunSchema,
  )
}

export function deleteWorkflowNode(workflowRunId: string, nodeRunId: string) {
  return apiRequest<{ deleted: string }>(`/workflow-runs/${workflowRunId}/nodes/${nodeRunId}`, {
    method: 'DELETE',
  })
}
