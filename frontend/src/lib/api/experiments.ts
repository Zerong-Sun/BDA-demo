import { apiRequest } from './client'
import { ExperimentResultSchema, type ExperimentResult } from '../schemas/candidate'
import { z } from 'zod'

export function listExperimentResults(projectId: string) {
  return apiRequest<ExperimentResult[]>(
    `/projects/${projectId}/experiment-results`,
    {},
    z.array(ExperimentResultSchema),
  )
}

export function uploadExperimentResults(file: File, projectId: string) {
  const form = new FormData()
  form.append('file', file)
  form.append('project_id', projectId)
  return apiRequest<{ imported: number; batch_id: string }>(
    '/experiment-results/upload',
    { method: 'POST', body: form },
    z.object({ imported: z.number(), batch_id: z.string() }),
  )
}
