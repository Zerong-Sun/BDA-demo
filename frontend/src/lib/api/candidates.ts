import { apiRequest } from './client'
import type { Candidate } from '../schemas/candidate'

export interface CandidateQuery {
  sort?: 'interface_score' | 'plddt' | 'pred_kd'
  order?: 'asc' | 'desc'
  status?: string
  decision?: string
  search?: string
  limit?: number
  offset?: number
}

export interface CandidateListResponse {
  items: Candidate[]
  total: number
  limit: number
  offset: number
}

export function listCandidates(projectId: string, query: CandidateQuery = {}) {
  const params = new URLSearchParams()
  if (query.sort) params.set('sort', query.sort)
  if (query.order) params.set('order', query.order)
  if (query.status) params.set('status', query.status)
  if (query.decision) params.set('decision', query.decision)
  if (query.search) params.set('search', query.search)
  if (query.limit != null) params.set('limit', String(query.limit))
  if (query.offset != null) params.set('offset', String(query.offset))
  const qs = params.toString()
  return apiRequest<CandidateListResponse>(
    `/projects/${projectId}/candidates${qs ? `?${qs}` : ''}`,
  )
}

export function getCandidate(candidateId: string) {
  return apiRequest<Candidate>(`/candidates/${candidateId}`)
}
