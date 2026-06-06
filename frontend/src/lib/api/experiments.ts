import { apiRequest } from './client'
import type { ExperimentResult } from '../schemas/candidate'

export function listExperimentResults(projectId: string) {
  return apiRequest<ExperimentResult[]>(`/projects/${projectId}/experiment-results`)
}

export function uploadExperimentResults(file: File, projectId: string) {
  const form = new FormData()
  form.append('file', file)
  form.append('project_id', projectId)
  return apiRequest<{ imported: number; batch_id: string }>('/experiment-results/upload', {
    method: 'POST',
    body: form,
  })
}
