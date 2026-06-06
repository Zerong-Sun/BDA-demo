import { apiRequest } from './client'
import type { WorkflowNode } from '../schemas/candidate'

export function listWorkflowNodes(workflowRunId: string) {
  return apiRequest<WorkflowNode[]>(`/workflow-runs/${workflowRunId}/nodes`)
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
