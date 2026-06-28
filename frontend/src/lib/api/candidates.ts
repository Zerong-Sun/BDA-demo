import { API_BASE, apiRequest } from './client'
import {
  CandidateListSchema,
  CandidateSchema,
  type Candidate,
  type CandidateListResponse,
} from '../schemas/candidate'

export interface CandidateQuery {
  sort?: 'interface_score' | 'plddt' | 'pred_kd'
  order?: 'asc' | 'desc'
  status?: string
  decision?: string
  search?: string
  limit?: number
  offset?: number
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
    {},
    CandidateListSchema,
  )
}

export function getCandidate(candidateId: string) {
  return apiRequest<Candidate>(`/candidates/${candidateId}`, {}, CandidateSchema)
}

export async function downloadCandidateStructures(
  candidateIds: string[],
  filename = 'candidate_structures.zip',
) {
  const token = sessionStorage.getItem('bda_token')
  const response = await fetch(`${API_BASE}/candidates/batch-download`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ candidate_ids: candidateIds, filename }),
  })
  if (!response.ok) {
    let message = `Candidate download failed (${response.status})`
    try {
      const payload = await response.json()
      message = payload?.detail ?? payload?.message ?? message
    } catch {
      // Keep the status-based message for non-JSON failures.
    }
    throw new Error(message)
  }

  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename.toLowerCase().endsWith('.zip') ? filename : `${filename}.zip`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

export type { CandidateListResponse }
