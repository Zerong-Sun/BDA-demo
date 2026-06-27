import { apiRequest } from './client'
import { JobSchema, type Job } from '../schemas/job'

export function listWorkflowJobs(workflowRunId: string): Promise<Job[]> {
  return apiRequest<{ items: unknown[] }>(`/workflow-runs/${workflowRunId}/jobs`).then((payload) =>
    payload.items.map((item) => JobSchema.parse(item)),
  )
}

export function getJob(jobId: string): Promise<Job> {
  return apiRequest<Job>(`/jobs/${jobId}`, {}, JobSchema)
}

export function syncJobResult(jobId: string): Promise<{
  job: Job
  live_status: string
  outputs?: Record<string, unknown> | null
  next_actions?: string[]
}> {
  return apiRequest<{
    job: unknown
    live_status: string
    outputs?: Record<string, unknown> | null
    next_actions?: string[]
  }>(`/jobs/${jobId}/sync`, { method: 'POST' }).then((payload) => ({
    ...payload,
    job: JobSchema.parse(payload.job),
  }))
}

export function getJobLogs(jobId: string, tail = 200): Promise<{ job_id: string; logs: string }> {
  return apiRequest(`/jobs/${jobId}/logs?tail=${tail}`)
}

export function cancelJob(jobId: string): Promise<{ job_id: string; status: string; cancelled?: boolean }> {
  return apiRequest(`/jobs/${jobId}/cancel`, { method: 'POST' })
}
