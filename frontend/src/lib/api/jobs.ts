import { apiRequest } from './client'
import { fetchPaginatedList } from './pagination'
import { JobSchema, type Job } from '../schemas/job'

export function listWorkflowJobs(workflowRunId: string): Promise<Job[]> {
  return fetchPaginatedList(`/workflow-runs/${workflowRunId}/jobs`, JobSchema)
}

export function getJobLogs(jobId: string, tail = 200): Promise<{ job_id: string; logs: string }> {
  return apiRequest(`/jobs/${jobId}/logs?tail=${tail}`)
}

export function cancelJob(jobId: string): Promise<{ job_id: string; status: string; cancelled?: boolean }> {
  return apiRequest(`/jobs/${jobId}/cancel`, { method: 'POST' })
}
