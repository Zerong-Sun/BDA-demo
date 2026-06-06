import type { ZodType } from 'zod'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

export interface ApiEnvelope<T> {
  data: T
  trace_id: string
}

export class ApiError extends Error {
  status: number
  payload?: unknown

  constructor(message: string, status: number, payload?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

function authHeaders(): HeadersInit {
  const token = sessionStorage.getItem('bda_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  schema?: ZodType<T>,
): Promise<T> {
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData)) {
    headers.set('content-type', 'application/json')
  }
  const auth = authHeaders()
  if (auth.Authorization) {
    headers.set('Authorization', auth.Authorization as string)
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    onUnauthorized?.()
  }

  if (!response.ok) {
    let payload: unknown
    try {
      payload = await response.json()
    } catch {
      payload = null
    }
    const message =
      (payload as { message?: string })?.message ??
      (payload as { detail?: string })?.detail ??
      `Request failed (${response.status})`
    throw new ApiError(message, response.status, payload)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const payload = (await response.json()) as ApiEnvelope<T>
  const data = payload.data
  if (schema) {
    return schema.parse(data)
  }
  return data
}

export function structureFileUrl(candidateId: string): string {
  return `${API_BASE}/candidates/${candidateId}/structure-file`
}

export function artifactUrl(relativePath: string): string {
  const normalized = relativePath.replace(/^\/+/, '').replace(/^artifacts\//, '')
  return `${API_BASE}/artifacts/${normalized}`
}

export function deliveryPackageDownloadUrl(projectId: string): string {
  return `${API_BASE}/projects/${projectId}/delivery-package/download`
}

export { API_BASE }
